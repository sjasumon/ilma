"""Handwritten loan examples only; no supplied source export fixtures."""
from datetime import date,timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import math,asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from ilma_api.db import Base,Institution,ServiceOffer
from ilma_api.loan_catalog import emi,fee_meta,fee_amount,margin,group,recoverable,scopes

@pytest.fixture
def db():
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False});Base.metadata.create_all(engine)
    with Session(engine) as s:
        for id,slug in [(1,'nccbank'),(2,'mtb'),(3,'bankasia')]:s.add(Institution(id=id,slug=slug,name_bn='পরীক্ষা ঋণ ব্যাংক '+str(id),name_en='Synthetic Lender '+str(id),type='bank',coverage='full',licensed=True,listed=True,islamic=False))
        s.commit();yield s
    engine.dispose()
def offer(db,id,bank=1,kind='home_loan',product='Synthetic Home',attr='interest_rate',value='10%',quote='Example published annual rate 10%.',condition='',hidden=False,stale=False):
    row=ServiceOffer(offer_id=id,institution_id=bank,category='loan',product=product,product_type=kind,attribute=attr,value_text=value,value_num=None,unit='pct_year',condition=condition,basis='conventional',doc_date=date.today(),stale=stale,source_url='https://example.example/loan',page=1,quote=quote,column_header='',variant='main',hidden=hidden,hidden_reason='numeric value is not printed in quote; requires verification' if hidden else '',checked_by='synthetic',checked_on=date.today())
    db.add(row);db.flush();return row
@pytest.mark.parametrize('rate,expected',[(0,2000000/240),(9.99,19287),(10,19300),(14,24870)])
def test_installment_math_rounds_only_for_display(rate,expected):
    value=emi(2000000,rate,240)
    assert value==expected if rate==0 else math.floor(value+.5)==expected
    if rate==10:assert value*240-2000000==pytest.approx(2632103.896,abs=.01)
def test_capped_fee_slabs_and_one_time_units():
    first={**fee_meta({'condition':'up to Tk. 50.00 lac; max Tk. 15,000; plus 15% VAT'}),'value_num':.5}
    second={**fee_meta({'condition':'above Tk. 50 lac; max Tk. 20,000; plus 15% VAT'}),'value_num':.3}
    assert first['unit']=='pct_once' and first['vat_percent']==15
    assert fee_amount(first,2000000)==10000 and fee_amount(first,4000000)==15000
    assert fee_amount(first,6000000) is None and fee_amount(second,6000000)==18000
    assert fee_amount(first,5000000)==15000 and fee_amount(second,5000000) is None
    cap=fee_meta({'condition':'below Tk.5,000,000: max 0.50% but not exceed Tk.15,000; plus 15% VAT'})
    assert cap['cap_bdt']==15000 and not cap['slab_max_inclusive']
def test_retail_scope_does_not_attach_professional_fees(db):
    rate=offer(db,'rate');fee=offer(db,'fee',kind='personal_loan',product='Retail Loan',attr='processing_fee',value='0.50%',quote='Synthetic fee 0.50%.',condition='up to Tk. 50 lac; max Tk.15,000')
    result=group(db,db.get(Institution,1),[rate,fee],'home_loan');assert result['fees'][0]['cap_bdt']==15000
    special=offer(db,'special',bank=3,kind='personal_loan',product='Bank Asia Loan for Professional',attr='processing_fee',value='0.50%',quote='Synthetic professional fee0.50%.')
    assert scopes(special,'bankasia')==['none']
def test_unreadable_and_stale_rows_never_enter_comparison(db):
    rate=offer(db,'rate');bad=offer(db,'unreadable',kind='home_loan',product='Synthetic Home',attr='processing_fee',value='0.50%',quote='Example fee 0.50%.',condition='quote_unreadable',hidden=True)
    old=offer(db,'oldfee',kind='personal_loan',product='Retail Loan',attr='processing_fee',value='0.50%',quote='Example fee 0.50%.',stale=True)
    assert group(db,db.get(Institution,1),[rate,bad,old],'home_loan')['fees']==[]
    rate.doc_date=date.today()-timedelta(days=366);assert group(db,db.get(Institution,1),[rate,bad,old],'home_loan') is None
def test_mid_rate_requires_quote_evidence_and_preserves_hidden_raw_row(db):
    row=offer(db,'mid',bank=2,attr='rate_min',value='9.50',quote='Synthetic Home Mid-Rate 10.50 ± 1%',hidden=True)
    assert recoverable(row)
    result=group(db,db.get(Institution,2),[row],'home_loan')
    assert result['rate']['value_num']==10.5 and result['rate_min']['value_num']==9.5 and result['rate_max']['value_num']==11.5
    assert result['rate']['offer_id']=='loan-mid-mid' and row.hidden
    row.quote='Published range 9.50% to11.50%';row.condition='Mid-Rate10.50 ±1%'
    assert not recoverable(row) and group(db,db.get(Institution,2),[row],'home_loan') is None
@pytest.mark.parametrize('text,expected',[('IR of Security + up to 3%',(None,3)),('Instrument Rate + 3%',(3,3)),('Scheme Rate+minimum 2.00%',(2,None)),('1.50%-3.00% above relevant FOs rate',(1.5,3))])
def test_margin_formula_does_not_become_a_fixed_rate(text,expected):
    data=margin({'value_text':text,'condition':'','quote':text});assert (data['margin_min'],data['margin_max'])==expected

def test_api_rejects_amount_terms_and_readout_never_calls_provider(db):
    from ilma_api.main import app,get_db
    rate=offer(db,'rate');db.commit();app.dependency_overrides[get_db]=lambda:db
    try:
        with TestClient(app) as client,patch('httpx.AsyncClient.post',new=AsyncMock()) as provider,patch('ilma_api.audio_cache.register_speech',new=AsyncMock()) as tts:
            assert client.get('/v1/services/compare?product_type=home_loan&amount=2000000').status_code==422
            assert client.get('/v1/services/compare?product_type=home_loan&tenor_months=240').status_code==422
            assert client.post('/v1/services/readout',json={'product_type':'home_loan','amount':2000000}).status_code==422
            result=client.post('/v1/services/readout',json={'product_type':'home_loan'});assert result.status_code==200 and result.json()['audio_url'] is None
            provider.assert_not_awaited();tts.assert_not_awaited()
    finally:app.dependency_overrides.clear()


def test_range_only_has_no_invented_declared_rate(db):
    low=offer(db,'range-low',attr='rate_min',value='9%',quote='Synthetic range9% to11%.')
    high=offer(db,'range-high',attr='rate_max',value='11%',quote='Synthetic range9% to11%.')
    result=group(db,db.get(Institution,1),[low,high],'home_loan')
    assert result['rate'] is None and result['rate_min']['value_num']==9 and result['rate_max']['value_num']==11

def test_frozen_loan_plan_preserves_exact_text_and_source(tmp_path):
    import importlib.util,json
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('loan_builder',Path(__file__).resolve().parents[1]/'scripts/build_loan_clips.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    kinds=['home_loan','auto_loan','personal_loan','loan_against_fdr']
    path=tmp_path/'review.json';path.write_text(json.dumps([{'product_type':k,'text':'পরীক্ষা ১০ টাকা।','source_sha256':'a'*64} for k in kinds]))
    items=module.plan(path)
    assert len(items)==4 and items[0]['text']=='পরীক্ষা ১০ টাকা।' and items[0]['source_sha256']=='a'*64
    assert items[0]['file']=='bn/home-loan.mp3'
    path.write_text(json.dumps([{'product_type':'home_loan','text':'x','source_sha256':'a'*64}]*4))
    with pytest.raises(ValueError,match='Duplicate'):module.plan(path)
