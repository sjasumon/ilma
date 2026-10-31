"""The optional fixed-prompt capability never publishes unreviewed assets."""
import json
from ilma_api import main
from ilma_api.voice_assets import CATALOG, digest


def payload(response):
    assert response.headers['cache-control'] == 'no-store'
    return json.loads(response.body)


def reviewed_bundle(root):
    directory = root / 'audio/fixed'
    directory.mkdir(parents=True)
    clips = {}
    for language in ('bn', 'en'):
        for key in CATALOG:
            if key.startswith('ivr_'):
                continue
            name = language + '-' + key
            (directory / (name + '.opus')).write_bytes(b'synthetic opus')
            (directory / (name + '.mp3')).write_bytes(b'synthetic mp3')
            clips[language + ':' + key] = {
                'file': name + '.opus', 'fallback_file': name + '.mp3',
                'text': 'Synthetic approved prompt',
                'text_sha256': digest(b'Synthetic approved prompt'),
                'audio_sha256': digest(b'synthetic opus'),
                'fallback_sha256': digest(b'synthetic mp3'),
                'reviewed': True, 'reviewer': 'Synthetic reviewer',
                'reviewed_at': '2026-10-31'}
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps({'clips': clips}))
    return directory, manifest, clips


def test_absent_optional_bundle_is_an_explicit_capability(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'STATIC_DIR', tmp_path)
    response = main.fixed_voice_content()
    assert response.status_code == 200
    body = payload(response)
    assert body['available'] is False
    assert body['reason'] == 'not_published'
    assert body['clips'] == {}
    assert body['message_bn'] and body['message_en']


def test_reviewed_bundle_retains_clip_text_and_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'STATIC_DIR', tmp_path)
    _, _, clips = reviewed_bundle(tmp_path)
    response = main.fixed_voice_content()
    assert response.status_code == 200
    body = payload(response)
    assert body['available'] is True
    assert set(body['clips']) == set(clips)
    assert body['clips']['bn:hint'] == {
        'url': '/static/audio/fixed/bn-hint.opus',
        'fallback_url': '/static/audio/fixed/bn-hint.mp3',
        'text': 'Synthetic approved prompt'}


def test_existing_invalid_bundle_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'STATIC_DIR', tmp_path)
    directory, manifest, clips = reviewed_bundle(tmp_path)
    for invalid in ('unreviewed', 'tampered', 'malformed', 'missing'):
        clips['bn:hint']['reviewed'] = invalid != 'unreviewed'
        manifest.write_text(json.dumps({'clips': clips}))
        (directory / 'bn-hint.mp3').write_bytes(b'changed' if invalid == 'tampered' else b'synthetic mp3')
        if invalid == 'malformed':
            manifest.write_text('{')
        elif invalid == 'missing':
            manifest.unlink()
        response = main.fixed_voice_content()
        assert response.status_code == 503
        body = payload(response)
        assert body['available'] is False and body['clips'] == {}
        assert body['error']['code'] == 'fixed_audio_unavailable'
