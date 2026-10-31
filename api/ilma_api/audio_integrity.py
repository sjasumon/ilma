"""Bounded verification of immutable saved clips; source checks stay per request."""
from functools import lru_cache
import hashlib
from pathlib import Path
import re
import time


def _identity(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


@lru_cache(maxsize=256)
def _verified(path, expected, identity):
    file = Path(path)
    # Recheck identity around the read so a replacement cannot inherit a hit.
    if _identity(file) != identity:
        return False
    actual = hashlib.sha256(file.read_bytes()).hexdigest()
    return _identity(file) == identity and actual == expected


def verified_audio(path, expected):
    """Reuse a hash only while file identity and the expected digest are unchanged."""
    if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
        return False
    try:
        path = Path(path).resolve(strict=True)
        identity = _identity(path)
        # Timestamp granularity can hide same-size writes in the current tick.
        # Only immutable files whose metadata has settled may reuse a digest.
        verify = _verified if time.time_ns() - max(identity[-2:]) > 1_000_000_000 else _verified.__wrapped__
        return verify(str(path), expected, identity)
    except (OSError, ValueError):
        return False
