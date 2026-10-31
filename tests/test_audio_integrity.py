"""Saved audio may reuse a hash only while the actual file is unchanged."""
import hashlib
import os
import time
from pathlib import Path
from unittest.mock import patch
from ilma_api.audio_integrity import verified_audio, _verified


def test_unchanged_clip_hashes_once_and_expected_hash_is_part_of_identity(tmp_path, monkeypatch):
    path = tmp_path/'sample.mp3'
    audio = b'synthetic audio'
    path.write_bytes(audio)
    digest = hashlib.sha256(audio).hexdigest()
    settled = time.time_ns() + 2_000_000_000
    monkeypatch.setattr('ilma_api.audio_integrity.time.time_ns', lambda: settled)
    _verified.cache_clear()
    original = Path.read_bytes
    reads = []
    def read(p):
        reads.append(p)
        return original(p)
    with patch.object(Path, 'read_bytes', read):
        assert verified_audio(path, digest)
        assert verified_audio(path, digest)
        assert len(reads)==1
        assert not verified_audio(path, '0'*64)
        assert len(reads)==2


def test_same_size_replacement_with_restored_mtime_cannot_reuse_success(tmp_path):
    path = tmp_path/'sample.mp3'
    path.write_bytes(b'original')
    digest = hashlib.sha256(b'original').hexdigest()
    before = path.stat()
    assert verified_audio(path, digest)
    replacement = tmp_path/'replacement.mp3'
    replacement.write_bytes(b'changed!')
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    replacement.replace(path)
    assert path.stat().st_size == before.st_size
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert not verified_audio(path, digest)
    path.unlink()
    assert not verified_audio(path, digest)


def test_change_during_verification_fails_closed(tmp_path):
    path = tmp_path/'sample.mp3'
    path.write_bytes(b'original')
    digest = hashlib.sha256(b'original').hexdigest()
    def changed(p):
        path.write_bytes(b'changed!')
        os.utime(path, ns=(1, 1))
        return b'original'
    with patch.object(Path, 'read_bytes', changed):
        assert not verified_audio(path, digest)
    assert not verified_audio(path, None)
    assert not verified_audio(tmp_path, digest)


def test_recently_written_clip_is_not_cached_before_metadata_settles(tmp_path):
    path = tmp_path/'sample.mp3'
    path.write_bytes(b'original')
    digest = hashlib.sha256(b'original').hexdigest()
    assert verified_audio(path, digest)
    path.write_bytes(b'changed!')
    assert not verified_audio(path, digest)
