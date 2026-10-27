"""Private local MySQL backups and an isolated restore drill (ilma only)."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from ilma_api.db import engine


def require_ilma(url):
    if url.get_backend_name() != 'mysql' or url.database != 'ilma':
        raise ValueError('Recovery commands require the ilma MySQL database.')


def option_value(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


@contextmanager
def credentials(url):
    # Credentials never appear in process arguments, logs or backup metadata.
    with tempfile.TemporaryDirectory(prefix='ilma-mysql-') as directory:
        path = Path(directory) / 'client.cnf'
        path.touch(mode=0o600)
        options = {
            'user': url.username, 'password': url.password or '', 'host': url.host or '127.0.0.1',
            'port': url.port or 3306, 'protocol': 'TCP', 'default-character-set': 'utf8mb4'}
        if url.query.get('unix_socket'):
            options.update(protocol='SOCKET', socket=url.query['unix_socket'])
        path.write_text('[client]\n' + '\n'.join(f'{key}={option_value(value)}' for key, value in options.items()) + '\n')
        yield str(path)


def run_mysql(arguments, **kwargs):
    try:
        subprocess.run(arguments, check=True, timeout=180, stderr=subprocess.DEVNULL, **kwargs)
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError('MySQL recovery command failed; check service permissions and journal.') from None


def backup(directory):
    require_ilma(engine.url)
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise ValueError('Backup directory must be private (0700), without a symlink.')
    destination = directory / ('ilma-' + datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8] + '.sql.gz')
    manifest = destination.with_suffix(destination.suffix + '.json')
    pending_manifest = destination.with_suffix(destination.suffix + '.json.part')
    completed = False
    try:
        with credentials(engine.url) as config, tempfile.TemporaryFile() as raw:
            # Ignore unrelated ~/.my.cnf/global defaults (including database=...).
            run_mysql(['mysqldump', '--defaults-file=' + config, '--single-transaction', '--quick',
                '--hex-blob', '--no-tablespaces', '--set-gtid-purged=OFF', '--column-statistics=0', 'ilma'], stdout=raw)
            raw.seek(0)
            with destination.open('xb') as compressed:
                os.chmod(destination, 0o600)
                with gzip.GzipFile(fileobj=compressed, mode='wb') as archive:
                    shutil.copyfileobj(raw, archive)
                compressed.flush()
                os.fsync(compressed.fileno())
        metadata = {'database': 'ilma', 'file': destination.name,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'created_at': datetime.utcnow().isoformat()}
        with pending_manifest.open('x') as handle:
            os.chmod(pending_manifest, 0o600)
            json.dump(metadata, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending_manifest, manifest)
        completed = True
        # Seven completed snapshots. Off-host/encrypted backups are a separate gate.
        # UUID suffixes do not order creation time when backups share a second.
        # Always keep this completed snapshot; retain six other recent completed
        # snapshots and leave any concurrent, unfinished dump alone.
        previous = [p for p in directory.glob('ilma-*.sql.gz') if p != destination
            and p.with_suffix(p.suffix + '.json').is_file()]
        for old in sorted(previous, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)[6:]:
            old.unlink()
            old.with_suffix(old.suffix + '.json').unlink(missing_ok=True)
        return destination
    except BaseException:
        if not completed:
            destination.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
        pending_manifest.unlink(missing_ok=True)
        raise


def restore_check(path, admin_url=None):
    require_ilma(engine.url)
    path = Path(path)
    metadata = json.loads(path.with_suffix(path.suffix + '.json').read_text())
    if metadata.get('database') != 'ilma' or hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get('sha256'):
        raise ValueError('Backup checksum/database verification failed.')
    target = 'ilma_restore_check_' + uuid.uuid4().hex
    created = False
    restored = None
    administrator = create_engine(admin_url) if admin_url else engine
    try:
        with administrator.connect() as connection:
            connection.execute(text(f'CREATE DATABASE `{target}` CHARACTER SET utf8mb4'))
            created = True
        with credentials(administrator.url) as config, tempfile.TemporaryFile() as raw:
            with gzip.open(path, 'rb') as archive:
                shutil.copyfileobj(archive, raw)
            raw.seek(0)
            run_mysql(['mysql', '--defaults-file=' + config, target], stdin=raw, stdout=subprocess.DEVNULL)
        restored = create_engine(administrator.url.set(database=target))
        tables = inspect(restored).get_table_names()
        source_tables = inspect(engine).get_table_names()
        if set(tables) != set(source_tables):
            raise ValueError('Restored schema differs from the live schema.')
        # Validate the restored catalog against the release's stable key counts;
        # mutable voice logs can legitimately change after the backup snapshot.
        counts = {}
        with restored.connect() as connection, engine.connect() as source:
            for table in ['institution', 'fact', 'service_offer', 'release']:
                restored_count = connection.execute(text(f'SELECT COUNT(*) FROM `{table}`')).scalar_one()
                if restored_count != source.execute(text(f'SELECT COUNT(*) FROM `{table}`')).scalar_one():
                    raise ValueError('Restored catalog count differs; repeat against a stable release.')
                counts[table] = restored_count
        return {'restored': True, 'tables': len(tables), 'catalog_counts': counts}
    finally:
        if restored is not None:
            restored.dispose()
        if created:
            # Never drop a user-supplied name, the live DB or an existing DB.
            with administrator.connect() as connection:
                connection.execute(text(f'DROP DATABASE `{target}`'))
        if admin_url:
            administrator.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore-check'])
    parser.add_argument('--directory', default='/var/lib/ilma-backups')
    parser.add_argument('--file')
    parser.add_argument('--admin-socket', help='Local root-only restore drill; never broaden runtime grants.')
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            path = backup(args.directory)
            print(json.dumps({'backup': path.name, 'ok': True}))
        elif args.file:
            administrator = None
            if args.admin_socket:
                if os.geteuid() != 0 or not Path(args.admin_socket).is_socket():
                    raise ValueError('Admin socket restore requires local root and a Unix socket.')
                administrator = URL.create('mysql+pymysql', username='root', host='localhost',
                    query={'unix_socket': args.admin_socket, 'charset': 'utf8mb4'})
            print(json.dumps(restore_check(args.file, administrator)))
        else:
            parser.error('--file is required for restore-check')
    except Exception:
        raise SystemExit('Recovery operation failed. Check credentials/permissions, checksum and disk capacity; no secrets printed.') from None


if __name__ == '__main__':
    main()
