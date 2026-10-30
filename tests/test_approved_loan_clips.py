"""Synthetic approvals verify fixed examples, exact files, and source invalidation."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from ilma_api import loan_readout
from ilma_api.loan_catalog import DEFAULTS

spec = importlib.util.spec_from_file_location('approved_loans', Path(__file__).resolve().parents[1] / 'scripts/build_approved_loan_clips.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def inputs(tmp_path):
    clips, bindings = [], {}
    for kind, key in loan_readout.CLIP_KEYS.items():
        text = 'অনুমোদিত পরীক্ষার পাঠ।'
        clips.append(dict(key=key, text=text, chars=len(text), text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                          file='static/audio/services/bn/loan_' + key.split(':')[-1] + '.mp3'))
        amount, years = DEFAULTS[kind]
        bindings[kind] = dict(rows=[dict(stale=False)], readout=dict(source_sha256='a' * 64, example_amount=amount, example_years=years))
    data = dict(clips=clips, total_chars=sum(c['chars'] for c in clips))
    a, b = tmp_path/'input.json', tmp_path/'bindings.json'
    a.write_text(json.dumps(data)); b.write_text(json.dumps(bindings))
    return a, b, data, bindings


def test_all_four_approved_keys_texts_and_paths_are_preserved(tmp_path):
    a, b, data, _ = inputs(tmp_path)
    items = builder.plan(a, b)
    assert [(i['key'], i['text'], i['file']) for i in items] == [(c['key'], c['text'], c['file']) for c in data['clips']]


@pytest.mark.parametrize('field,value', [('key', 'loan:bn:other'), ('text', 'changed'), ('file', 'static/audio/services/bn/../../private.mp3'), ('text_sha256', 'b'*64)])
def test_changed_approved_input_is_rejected(tmp_path, field, value):
    a, b, data, _ = inputs(tmp_path)
    data['clips'][0][field] = value
    a.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        builder.plan(a, b)


def test_duplicate_clips_and_changed_defaults_are_rejected(tmp_path):
    a, b, data, bindings = inputs(tmp_path)
    data['clips'][1] = data['clips'][0].copy()
    a.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        builder.plan(a, b)
    a, b, data, bindings = inputs(tmp_path)
    bindings['home_loan']['readout']['example_years'] = 10
    b.write_text(json.dumps(bindings))
    with pytest.raises(ValueError, match='default'):
        builder.plan(a, b)


def test_shared_saved_loan_blocks_changed_rate_bank_set_or_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(loan_readout, 'ROOT', tmp_path)
    monkeypatch.setattr(loan_readout, 'facts', lambda result: dict(product_type='home_loan', amount=2000000, years=20))
    monkeypatch.setattr(loan_readout, 'narration', lambda pack: 'Current source fallback')
    result = dict(rows=[dict(bank='synthetic', rate=10)], defaults=dict(amount=2000000, years=20))
    baseline = loan_readout.readout(result)
    audio = b'synthetic-audio'
    directory = tmp_path/'static/audio/services/bn'; directory.mkdir(parents=True)
    path = directory/'loan_home.mp3'; path.write_bytes(audio)
    text = 'পরীক্ষার অনুমোদিত পাঠ।'
    item = dict(key='loan:bn:home', text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                file='static/audio/services/bn/loan_home.mp3', audio_sha256=hashlib.sha256(audio).hexdigest(),
                source_sha256=baseline['source_sha256'], approved_exact_text=True, reviewed=True,
                example_amount=2000000, example_years=20)
    (directory.parent/'manifest.json').write_text(json.dumps(dict(clips={item['key']:item})))
    ready = loan_readout.readout(result)
    assert ready['text'] == text and ready['audio_url'].startswith('/static/audio/services/bn/loan_home.mp3?v=')
    assert loan_readout.readout({**result, 'rows':[dict(bank='synthetic', rate=11)]})['audio_url'] is None
    assert loan_readout.readout({**result, 'rows':[]})['audio_url'] is None
    path.write_bytes(b'corrupt')
    assert loan_readout.readout(result)['audio_url'] is None
