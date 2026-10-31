"""Extra-data scope, provenance, matching and private-watch regressions."""
from pathlib import Path
from datetime import date
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from ilma_api.csv_loader import load as base
from ilma_api.export_seed import read
from ilma_api.incident_loader import load as incidents
from ilma_api.extra_data import load,ExtraItem,RelatedEntity,classify_announcement,circular_bank
from ilma_api.db import Fact,ServiceOffer
from ilma_api.report_card import get_institution_report_card
from ilma_api.main import app,get_db,get_institution_index
from ilma_api.voice_text import match_candidates
SEED=Path(__file__).resolve().parents[1]/'seed'

@pytest.fixture
def context():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    base(SEED,engine);incidents(SEED/'incidents',engine);load(SEED/'extra',engine)
    def fixture():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_db]=fixture
    with TestClient(app) as client:yield engine,client
    app.dependency_overrides.clear();engine.dispose()


def test_scope_sources_and_no_status_changes(context):
    engine,client=context
    manifest=json.loads((SEED/'extra/release.json').read_text())
    with Session(engine) as db:
        assert db.query(RelatedEntity).count()==33
        for row in db.query(ExtraItem):
            assert row.source_url.startswith(('https://','http://'))
            if row.kind=='announcement':
                assert row.topic!='other'
                assert 'dse' in row.source_url
            if row.kind=='press':assert not any(s in row.title.lower() for s in ('auction','statement of affairs','treasury bond','more....'))
            if row.kind=='bank_notice' and row.institution_id==26:assert not any(s in row.title.lower() for s in ('janata','sonali','agrani','rupali'))
            if row.kind=='bank_notice' and row.institution_id==36:assert 'pakistan' not in row.title.lower()
        assert db.query(ExtraItem).filter_by(kind='compliance').count()==2
        expected=sum(len(read(SEED/f)) for f in ('fact.csv','incidents/fact.csv'))
        assert db.query(Fact).count()==expected and db.query(ServiceOffer).count()==610
        assert get_institution_report_card(db,'nbl')['status']['code']=='high'
        assert get_institution_report_card(db,'islamibank')['status']['code']=='high'
        assert get_institution_report_card(db,'bracbank')['status']['code']=='strong'
    history=client.get('/v1/institutions/11/history').json()
    assert history['available'] and not history['complete_search']
    exemption=next(r for r in history['items'] if r['kind']=='other_compliance')
    assert exemption['official'] and not exemption['affects_status']
    for kind in ('announcements','reports','bb-notices'):
        response=client.get('/v1/institutions/19/publications/'+kind)
        assert response.status_code==200 and response.json()['items']
        assert len(response.json()['items'])<=20
    assert client.get('/v1/institutions/19/publications/invalid').status_code==404
    assert manifest['counts']['announcement']>400


def test_watch_filter_and_private_cache(context):
    _,client=context
    one={'X-ILMA-Device':'extra-test-device-one-123456'}
    two={'X-ILMA-Device':'extra-test-device-two-123456'}
    assert client.get('/v1/extra-news',headers=one).json()['announcements']==[]
    client.post('/v1/institutions/19/watch',headers=one)
    result=client.get('/v1/extra-news',headers=one)
    assert result.headers['cache-control']=='no-store'
    assert result.json()['announcements'] and all(r['institution_id']==19 for r in result.json()['announcements'])
    assert result.json()['warnings'] and result.json()['rules']
    assert client.get('/v1/extra-news',headers=two).json()['announcements']==[]
    client.delete('/v1/institutions/19/watch',headers=one)
    assert not client.get('/v1/extra-news',headers=one).json()['announcements']


def test_subsidiaries_not_parent_banks_and_review_survives(context):
    engine,client=context
    with Session(engine) as db:
        banks=get_institution_index(db)
        assert not any(r['id']==42 for r in match_candidates('Prime Bank Investment Limited',banks))
        assert match_candidates('Prime Bank',banks)[0]['id']==42
        assert not any(r['id']==42 for r in client.get('/v1/institutions',params={'q':'Prime Bank Investment'}).json())
        row=db.query(ExtraItem).first();key=row.item_id;row.checked_by='Sumon';db.commit()
    load(SEED/'extra',engine)
    with Session(engine) as db:assert db.get(ExtraItem,key).checked_by=='Sumon'


def test_handwritten_matching_and_audit_classification():
    banks=[dict(id='1',bank_name='National Bank PLC'),dict(id='2',bank_name='Islami Bank Bangladesh PLC'),dict(id='3',bank_name='Janata Bank PLC')]
    assert circular_bank('National Bank of Pakistan intermission',banks,{}) is None
    assert circular_bank('Name change of Janata Bank Limited',banks,{})=='3'
    assert circular_bank('National Bank Limited exemption',banks,{})=='1'
    assert circular_bank('Janata Bank and Islami Bank Bangladesh notice',banks,{}) is None
    assert classify_announcement(dict(topic='audit_emphasis',title='Emphasis of matters',body='Unqualified opinion',quote=''))=='financials'
    assert classify_announcement(dict(topic='audit_emphasis',title='Qualified Opinion',body='',quote=''))=='audit_emphasis'
    nested=[dict(id='1',bank_name='Mutual Trust Bank PLC'),dict(id='2',bank_name='Trust Bank PLC')]
    assert circular_bank('Mutual Trust Bank Ltd intermission',nested,{})=='1'
    assert classify_announcement(dict(topic='other',title='Dividend declaration',body='',quote=''))=='dividend'


def test_handwritten_converter_rejects_wrong_company_source(tmp_path):
    import csv
    from ilma_api.extra_data import convert
    def write(name,fields,rows=()):
        with (tmp_path/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    write('banks',['id','bank_name','dse_code','short_code'],[dict(id='19',bank_name='Eastern Bank PLC',dse_code='EBL',short_code='EBL')])
    write('bank_aliases',['bank_id','alias'])
    write('dse_bank_announcements',['id','bank_id','trading_code','announcement_date','topic','title','body','quote','document_id'],[
        dict(id='synthetic',bank_id='19',trading_code='EBL',announcement_date='2026-10-01',topic='other',title='SYNTHETIC board meeting',body='',quote='',document_id='1')])
    write('documents',['id','url','final_url'],[dict(id='1',url='https://www.dse.com.bd/company/NBL',final_url='')])
    # Minimal headers suffice because this invalid binding must fail first.
    for name in ('bank_reports','bb_press_releases','bb_circulars','bb_circular_banks','bb_bank_actions','related_entities'):
        write(name,['id'])
    with pytest.raises(ValueError,match='DSE bank/code/source mismatch'):
        convert(tmp_path,tmp_path/'output',tmp_path/'documents.csv','2026-10-28')


def test_subsidiary_cannot_fall_back_to_contextual_parent(context):
    import asyncio
    from unittest.mock import patch,AsyncMock
    from ilma_api.voice_pipeline import run_pipeline
    from ilma_api.voice_text import VoiceContext
    engine,_=context
    async def check():
        with Session(engine) as db:
            with patch('ilma_api.voice_pipeline.understand',new=AsyncMock()) as understand:
                response=''.join([chunk async for chunk in run_pipeline(None,'Prime Bank Investment Limited','',VoiceContext(tab='bank',bank_id=42,speak=False),get_institution_index(db),db,mode='text')])
                understand.assert_not_awaited()
                return response
    assert 'related_entity' in asyncio.run(check())
