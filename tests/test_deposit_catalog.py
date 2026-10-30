"""Synthetic deposit boundaries and privacy cases; no source-export fixtures."""
from types import SimpleNamespace
from datetime import date
import math,pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import patch,AsyncMock
from ilma_api.db import Base,Institution,ServiceOffer
from ilma_api.deposit_catalog import slabs,in_slab,term_list,fv,view,kind,scheme,select

@pytest.mark.parametrize('text,minimum,maximum',[('amount less than BDT 0.1 crore',None,1000000),('Below 50 Lac',None,5000000),('1 Lac - < 1 Cr',100000,10000000),('Below Tk. 100.00 Crore',None,1000000000),('Tk. 50,00,001 - Tk. 1,00,00,000',5000001,10000000),('Daily Average Balance Below 50k',None,50000),('25 Lac and above',2500000,None)])
def test_printed_balance_slabs(text,minimum,maximum):
    r=slabs(text);assert (r['amount_min'],r['amount_max'])==(minimum,maximum)
    if minimum:assert not in_slab(r,minimum-1)
    if maximum:assert not in_slab(r,maximum+1)

def test_strict_and_inclusive_boundaries():
    assert not in_slab(slabs('Below 50 Lac'),5000000)
    assert in_slab(slabs('Tk. 50,00,001 - Tk. 1,00,00,000'),10000000)
    assert not slabs('Regular Up to 2.00%')['slab_known']

@pytest.mark.parametrize('text,expected',[('1 to 6 Years',[12,24,36,48,60,72]),('2 to 5 Years tenor',[24,36,48,60]),('5-9 Years',[60,72,84,96,108]),('3, 5, 7, 10 Years',[36,60,84,120]),('tenure 60M to 180M',list(range(60,181,12))),('36M or 60M',[36,60]),('Year 4; Monthly Payment 17,676',[48]),('not a readable term',[])])
def test_discrete_dps_terms(text,expected):
    assert term_list(SimpleNamespace(product='Synthetic plan',condition=text,tenor_months=None))==expected

def test_dps_beginning_of_month_compounding_and_zero_rate():
    assert fv(17676,8,48)==pytest.approx(1000000,rel=.005)
    assert fv(5000,0,36)==180000
    assert fv(5000,7.5,36)>180000

def test_double_benefit_is_lump_sum_scheme():
    r=SimpleNamespace(product='NCC Double Benefit Scheme',product_type='dps')
    assert kind(r)=='fdr' and scheme(r)

def test_audience_and_scheme_isolation():
    base=dict(product_type='dps',tenor_list_months=[36],amount_min=None,amount_max=None,amount_max_inclusive=False,slab_known=True,variant='main',product='Synthetic',offer_id='x')
    allrow={**base,'audience':'all'};women={**base,'audience':'women'};target={**allrow,'variant':'scheme','offer_id':'scheme'}
    assert select([allrow,women,target],'dps',36,'all',5000)==[allrow,target]
    assert select([allrow,women],'dps',36,'women',5000)==[women]
    assert not select([allrow],'dps',48,'all',5000)

@pytest.fixture
def db():
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False});Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Institution(id=1,slug='nccbank',name_bn='পরীক্ষা ব্যাংক',name_en='Synthetic Bank',type='bank',coverage='full',licensed=True,listed=True,islamic=False))
        s.add(ServiceOffer(offer_id='synthetic-fdr',institution_id=1,category='deposit',product='Fixed Deposit 12 Months',product_type='fdr',attribute='rate',value_text='8.25',value_num=8.25,unit='pct_year',condition='Below 50 Lac',basis='conventional',doc_date=date.today(),stale=False,source_url='https://example.example/rates',page=1,quote='Synthetic fixed deposit rate8.25%.',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='synthetic',checked_on=date.today()))
        s.commit();yield s
    engine.dispose()
def test_endpoint_no_inputs_no_runtime_speech_and_source_bound_text(db):
    from ilma_api.main import app,get_db
    app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as c,patch('httpx.AsyncClient.post',new=AsyncMock()) as provider:
            for query in ['amount=100000','tenor_months=12','balance=30000','term=36']:assert c.get('/v1/services/deposits?'+query).status_code==422
            assert c.get('/v1/services/deposits?audience=unknown').status_code==422
            r=c.get('/v1/services/deposits');assert r.status_code==200
            d=r.json();assert d['catalog_banks'][0]['rates'][0]['amount_max']==5000000
            assert d['readouts']['fdr-12-all']['audio_url'] is None
            assert c.get('/v1/services/compare?product_type=fdr&tenor_months=12&audience=all').status_code==200
            provider.assert_not_awaited()
    finally:app.dependency_overrides.clear()


def test_fixed_fdr_half_taka_is_rounded_up_without_total_subtraction():
    from ilma_api.deposit_readout import facts
    row=dict(product_type='fdr',audience='all',tenor_list_months=[3],amount_min=None,amount_max=None,amount_max_inclusive=False,slab_known=True,variant='main',product='Synthetic',offer_id='x',value_num=8.25,display_priority=0)
    pack=facts({'catalog_banks':[dict(slug='nccbank',name_bn='পরীক্ষা',status={'code':'strong'},rates=[row])],'insurance':None},'fdr',3,'all')
    assert pack['banks'][0]['interest']==2063 and pack['banks'][0]['maturity']==102063


def test_service_answer_separates_general_and_women_dps(db):
    from ilma_api.bank_services import voice_service_result
    from ilma_api.voice_text import VoiceIntent,VoiceContext
    db.get(Institution,1).slug='bankasia'
    for id,product,rate in [('general','DPS+','8.25'),('women','DPS for Women – আঁচল','8.50')]:
        db.add(ServiceOffer(offer_id=id,institution_id=1,category='deposit',product=product,product_type='dps',attribute='rate',value_text=rate,value_num=float(rate),unit='pct_year',condition='3 Years tenor',basis='conventional',doc_date=date.today(),stale=False,source_url='https://example.example/dps',page=1,quote='Synthetic published annual rate '+rate+'%.',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='synthetic',checked_on=date.today()))
    db.commit()
    def answer(text):return voice_service_result(text,VoiceIntent(intent='rates',product='dps',period_months=36),VoiceContext(tab='services'),db,'bn')
    assert [r['fact_id'] for r in answer('ডিপিএসের হার')['sources']]==['general']
    assert [r['fact_id'] for r in answer('নারীদের ডিপিএসের হার')['sources']]==['women']
    assert answer('নারীদের ডিপিএসের হার')['comparison']['audience']=='women'

def test_nxt_is_reference_only_and_never_joins_general_calculation():
    from ilma_api.deposit_references import references
    row=dict(product_type='savings',audience='check',tenor_list_months=[],product='NCC NXT Savings Account',offer_id='synthetic-nxt',value_num=4)
    result=dict(catalog_banks=[dict(slug='nccbank',name_bn='পরীক্ষা',name_en='Synthetic',status={'code':'strong'},rates=[row])])
    refs=references(result,'savings',12,'all');assert refs[0]['reference_only'] and refs[0]['offer']['audience']=='check'
    assert select([row],'savings',12,'all',100000)==[]

def test_saved_deposit_uses_services_manifest_and_source_change_suppresses_audio(db,tmp_path,monkeypatch):
    import json,hashlib
    from ilma_api import deposit_readout
    from ilma_api.deposit_catalog import catalog
    initial=catalog(db);read=initial['readouts']['fdr-12-all'];monkeypatch.setattr(deposit_readout,'ROOT',tmp_path)
    directory=tmp_path/'static/audio/services/bn';directory.mkdir(parents=True);audio=b'synthetic-audio';(directory/'deposit_fdr-12-all.mp3').write_bytes(audio)
    text='অনুমোদিত পরীক্ষার পাঠ।';item=dict(text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_sha256=read['source_sha256'],audio_sha256=hashlib.sha256(audio).hexdigest(),file='bn/deposit_fdr-12-all.mp3',approved_exact_text=True,reviewed=True)
    (directory.parent/'manifest.json').write_text(json.dumps({'clips':{'deposit:bn:fdr-12-all':item}}))
    ready=catalog(db)['readouts']['fdr-12-all'];assert ready['text']==text and '/services/bn/deposit_fdr-12-all.mp3?v=' in ready['audio_url']
    row=db.get(ServiceOffer,'synthetic-fdr');row.value_num=9;row.value_text='9';row.quote='Synthetic fixed deposit rate9%.';db.flush()
    stale=catalog(db)['readouts']['fdr-12-all'];assert stale['audio_url'] is None and stale['text']!=text
