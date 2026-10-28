"""Regressions for the 27 October full website test (typed questions and pages)."""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ilma_api import settings
from ilma_api.csv_loader import load as base
from ilma_api.incident_loader import load as load_incidents
from ilma_api.main import app, get_db, get_institution_index
from ilma_api.other_banks import find_other_bank
from ilma_api.rules.reasons import format_number
from ilma_api.voice_glossary import add_glossary
from ilma_api.voice_pipeline import run_pipeline, understand
from ilma_api.voice_text import VoiceContext, VoiceIntent

SEED = Path(__file__).resolve().parents[1] / 'seed'


@pytest.fixture(scope='module')
def sessions():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    base(SEED, engine)
    load_incidents(SEED / 'incidents', engine)
    with Session(engine) as db:
        add_glossary(db)
        db.commit()
    yield sessionmaker(bind=engine)
    engine.dispose()


def ask(sessions, text, language='bn', spark=None):
    """Run a typed question; any model call fails the test unless a reply is supplied."""
    async def collect():
        with sessions() as db, patch.object(settings, 'META_MODEL_API_KEY', 'test-only'):
            handler = spark or (lambda request: pytest.fail('unexpected model call'))
            transport = httpx.MockTransport(handler)
            real = httpx.AsyncClient
            with patch('ilma_api.voice_pipeline.httpx.AsyncClient', lambda **kw: real(transport=transport)), \
                 patch('ilma_api.voice_answers.httpx.AsyncClient', lambda **kw: real(transport=transport)):
                chunks = [chunk async for chunk in run_pipeline(None, text, '', VoiceContext(ui_lang=language, speak=False),
                                                                lambda: get_institution_index(db), db, mode='text')]
        events = [(c.split('\n')[0][7:], json.loads(c.split('\n')[1][6:])) for c in chunks]
        return {name: data for name, data in events}
    return asyncio.run(collect())


def wording_unavailable(request):
    return httpx.Response(503)


def test_best_bank_question_is_refused_without_a_model_call(sessions):
    result = ask(sessions, 'কোন ব্যাংকে টাকা রাখব? সবচেয়ে ভালো ব্যাংক কোনটা?')['result']
    assert result['type'] == 'refused' and result['offer_bank_list']
    assert 'সুপারিশ করি না' in result['text']
    assert ask(sessions, 'Which is the best bank?', 'en')['result']['type'] == 'refused'


def test_named_bank_figure_is_answered_from_the_database(sessions):
    result = ask(sessions, 'ডাচ বাংলার মুনাফা কত?', spark=wording_unavailable)['result']
    assert result['type'] == 'ask_answer'
    assert 'কোটি টাকা' in result['text'] and not any(c.isascii() and c.isdigit() for c in result['text'])


def test_islami_bad_loans_are_labelled_as_calculated(sessions):
    result = ask(sessions, 'ইসলামী ব্যাংকের খেলাপি ঋণ কত?', spark=wording_unavailable)['result']
    assert '৪৯.৬৬%' in result['text'] and 'হিসাব করা' in result['text']


def test_known_bank_outside_the_demo_says_so(sessions):
    result = ask(sessions, 'পূবালী ব্যাংক কেমন আছে?')['result']
    assert result['type'] == 'not_in_demo' and result['offer_bank_list']
    assert result['text'] == 'পূবালী ব্যাংক এখনো ডেমোতে নেই; ডেমোতে ১১টি ব্যাংক আছে।'
    assert find_other_bank('Dhaka Bank') and not find_other_bank('ঢাকায় থাকি') and not find_other_bank('one more question')
    # Names overlapping demo aliases are not listed, so a demo bank is never hidden.
    assert ask(sessions, 'Eastern Bank', 'en')['result']['type'] == 'report_card'


def test_english_report_uses_full_stops(sessions):
    result = ask(sessions, 'Is BRAC Bank safe?', 'en', spark=lambda request: httpx.Response(200, json={'choices': [
        {'message': {'content': json.dumps({'intent': 'bank_status', 'institution_ids': [11], 'product': None, 'card_tier': None,
                                             'service_attribute': None, 'amount_bdt': None, 'period_months': None})}}]}))['result']
    assert result['type'] == 'report_card' and '।' not in result['text'] + result['speech_text']


def test_crar_glossary_definition_is_corrected(sessions):
    with sessions() as db:
        from ilma_api.voice_facts import glossary_facts
        assert glossary_facts('CRAR মানে কি?', 'bn', db)[0]['text'].startswith('ঝুঁকিভিত্তিক সম্পদের তুলনায়')


def test_intent_retries_one_quick_failure():
    calls = []
    def provider(request):
        calls.append(1)
        if len(calls) == 1: return httpx.Response(503)
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'intent': 'out_of_scope', 'institution_ids': [],
            'product': None, 'card_tier': None, 'service_attribute': None, 'amount_bdt': None, 'period_months': None})}}]})
    async def check():
        with patch.object(settings, 'META_MODEL_API_KEY', 'test-only'):
            async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
                return await understand('What is the weather?', [], VoiceContext(), client)
    assert asyncio.run(check()).intent == 'out_of_scope' and len(calls) == 2


def test_number_grouping():
    assert format_number(7000, bn=True) == '৭,০০০' and format_number(10000) == '10,000'
    assert format_number(1000000) == '10,00,000' and format_number(-2429.87) == '-2,429.87'
    assert format_number(12.5) == '12.5' and format_number(1000000, group=False) == '1000000'


@pytest.fixture
def client(sessions):
    def fixture_db():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = fixture_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_search_treats_like_wildcards_literally(client):
    assert client.get('/v1/institutions', params={'q': '%'}).json() == []
    assert client.get('/v1/institutions', params={'q': '_'}).json() == []
    assert client.get('/v1/institutions', params={'q': 'brac'}).json()


def test_install_and_share_metadata(client):
    assert client.get('/favicon.ico').headers['content-type'] == 'image/x-icon'
    manifest = client.get('/manifest.webmanifest')
    assert manifest.headers['content-type'].startswith('application/manifest+json')
    assert manifest.json()['display'] == 'standalone'
    for icon in manifest.json()['icons']:
        assert client.get(icon['src']).status_code == 200
    html = client.get('/').text
    for tag in ('name="description"', 'name="theme-color"', 'rel="manifest"', 'property="og:image"', 'property="og:title"'):
        assert tag in html


def test_versioned_assets_are_immutable_and_compressed(client):
    response = client.get('/static/js/app.js?v=voice-complete-20261028-36', headers={'Accept-Encoding': 'gzip'})
    assert response.headers['cache-control'] == 'public, max-age=31536000, immutable'
    assert response.headers['content-encoding'] == 'gzip'
    assert 'content-security-policy' in response.headers


def test_voice_test_page_is_hidden_unless_enabled(client):
    with patch.object(settings, 'VOICE_TEST_PAGE_ENABLED', False):
        assert client.get('/voice-test').status_code == 404
        assert client.get('/static/voice-test.html').status_code == 404
    with patch.object(settings, 'VOICE_TEST_PAGE_ENABLED', True):
        assert client.get('/voice-test').status_code == 200
        assert client.get('/static/voice-test.html').status_code == 200
