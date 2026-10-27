"""Install a pinned official Gitleaks binary after verifying its SHA-256."""
import argparse
import hashlib
import io
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen

VERSION = '8.30.1'
BASE = f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}'


def install(directory):
    system = platform.system().lower()
    architecture = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine().lower())
    if system not in {'linux', 'darwin'} or not architecture:
        raise ValueError('Install the pinned official Gitleaks release for this platform manually.')
    name = f'gitleaks_{VERSION}_{system}_{architecture}.tar.gz'
    with urlopen(BASE + f'/gitleaks_{VERSION}_checksums.txt', timeout=30) as response:
        checksums = dict((parts[1].lstrip('*'), parts[0]) for line in response.read().decode().splitlines() if len(parts := line.split()) == 2)
    with urlopen(BASE + '/' + name, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != checksums.get(name):
        raise ValueError('Gitleaks checksum verification failed.')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'gitleaks'
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as bundle:
        member = bundle.getmember('gitleaks')
        if not member.isfile():
            raise ValueError('Unexpected binary archive member.')
        target.write_bytes(bundle.extractfile(member).read())
    target.chmod(0o755)
    print(f'Installed verified Gitleaks {VERSION}.')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default='.tools')
    install(parser.parse_args().directory)
