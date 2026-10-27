import gzip
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.engine import make_url

from ilma_api import monitor, recovery


def test_monitor_rejects_false_health_and_errors():
    for response, expected in [(httpx.Response(200, json={'ok': True, 'db': 'connected'}), True),
        (httpx.Response(200, json={'ok': False, 'db': 'unavailable'}), False),
        (httpx.Response(503, json={'ok': True, 'db': 'connected'}), False),
        (httpx.Response(200, text='not json'), False)]:
        with patch('ilma_api.monitor.httpx.get', return_value=response):
            assert monitor.check()['healthy'] is expected
    with patch('ilma_api.monitor.httpx.get', side_effect=httpx.ConnectError('unavailable')):
        assert monitor.check()['healthy'] is False


def test_backup_private_atomic_checksum_and_retention():
    from types import SimpleNamespace
    url = make_url('mysql+pymysql://user:private@localhost/ilma')
    def dump(arguments, stdout):
        assert 'private' not in ' '.join(arguments)
        config = Path(arguments[1].split('=', 1)[1])
        assert config.stat().st_mode & 0o777 == 0o600
        assert 'password="private"' in config.read_text()
        assert arguments[-1] == 'ilma'
        assert arguments[1].startswith('--defaults-file=')
        stdout.write(b'CREATE TABLE sample (id int);\n')
    with tempfile.TemporaryDirectory() as directory, patch.object(recovery, 'engine', SimpleNamespace(url=url)), patch.object(recovery, 'run_mysql', side_effect=dump):
        for _ in range(8):
            path = recovery.backup(directory)
        assert len(list(Path(directory).glob('*.sql.gz'))) == 7
        assert gzip.open(path, 'rb').read() == b'CREATE TABLE sample (id int);\n'
        assert path.stat().st_mode & 0o777 == 0o600
        assert json.loads(path.with_suffix('.gz.json').read_text())['database'] == 'ilma'
        # A partial dump must not become a completed snapshot.
        with patch.object(recovery, 'run_mysql', side_effect=RuntimeError('failure')), pytest.raises(RuntimeError):
            recovery.backup(directory)
        assert len(list(Path(directory).glob('*.sql.gz'))) == 7
        metadata = path.with_suffix('.gz.json')
        metadata.write_text(json.dumps({'database': 'ilma', 'sha256': 'bad'}))
        with pytest.raises(ValueError, match='checksum'):
            recovery.restore_check(path)


def test_recovery_rejects_unrelated_database_and_escapes_credentials():
    with pytest.raises(ValueError):
        recovery.require_ilma(make_url('mysql+pymysql://localhost/project_db'))
    assert recovery.option_value('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'
