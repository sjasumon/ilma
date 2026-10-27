from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ilma_api.main import app
from ilma_api.csv_loader import load
from ilma_api.report_card import get_institution_report_card
from ilma_api.bank_services import voice_service_result
from ilma_api.voice_text import VoiceIntent, VoiceContext


def test_security_headers_cover_shell_errors_and_rejected_uploads():
    with TestClient(app) as client:
        responses = [client.get('/'), client.get('/missing-page'),
            client.post('/v1/speech', content=b'x'*17000)]
    assert [r.status_code for r in responses] == [200, 404, 413]
    assert 'no-transform' in responses[0].headers['cache-control']
    for response in responses:
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['strict-transport-security'] == 'max-age=31536000'
        assert response.headers['referrer-policy'] == 'strict-origin-when-cross-origin'
        assert "script-src 'self'" in response.headers['content-security-policy']
    with TestClient(app) as client:
        docs=client.get('/docs')
    policy=docs.headers['content-security-policy']
    assert 'https://cdn.jsdelivr.net' in policy and "'sha256-" in policy
    assert "script-src 'self' 'unsafe-inline'" not in policy


def test_real_seed_insurance_has_official_source_and_qualified_payment_steps():
    engine=create_engine('sqlite://')
    load(Path(__file__).resolve().parents[1]/'seed',engine)
    with Session(engine) as db:
        insurance=get_institution_report_card(db,19)['insurance']
        assert insurance['limit_bdt']==200000
        assert insurance['payout_working_days']==17
        assert insurance['source_url']=='https://bdlaws.minlaw.gov.bd/act-print-1703.html'
        assert '১০ কার্যদিবস' in insurance['text_bn'] and '৭ কার্যদিবস' in insurance['text_bn']
        assert 'required information' in insurance['text_en']
        answer=voice_service_result('এফডিআরের হার',VoiceIntent(intent='rates',product='fdr'),VoiceContext(tab='services'),db,'bn')
        assert '৯.২৫%' in answer['text']
        assert 'সেপ্টেম্বর' in answer['text']
        assert '2026-' not in answer['text']
        assert 'ব্যাংকের অবস্থা যাচাই হয়নি' in answer['text']
        assert 'ব্যাংকের অবস্থা যাচাই হয়নি' in answer['speech_text']
        assert all(source['source_title_bn'] for source in answer['sources'])
    engine.dispose()
