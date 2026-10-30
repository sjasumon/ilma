"""Synthetic account ladders, annualization and complete-net rules."""
import pytest
from types import SimpleNamespace
from ilma_api.account_catalog import balance_slab,contains,yearly,calculate,debit_variant,fee_view

@pytest.mark.parametrize('text,low,high,inclusive',[('average balance up to BDT 10,000',None,10000,True),('average balance BDT 25,001 to 200,000',25001,200000,True),('average balance above 10 Lac',1000000,None,False),('AverageBalanceAboveTk.10,00,000.00',1000000,None,False),('average balance above TK. 10,000 to TK. 25,000',10000,25000,True)])
def test_balance_boundaries(text,low,high,inclusive):
    result=balance_slab(text);assert (result['balance_min'],result['balance_max'])==(low,high)
    if high:assert contains(result,high)==inclusive and not contains(result,high+1)
    if low:assert not contains(result,low-1)

def fee(value,condition='',periods=2,vat=15):return dict(value_num=value,periods_per_year=periods,vat_percent=vat,vat_included=False,account_audience='all',**balance_slab(condition))
def bank():
    rate=dict(audience='all',display_priority=0,slab_known=True,amount_min=100000,amount_max=2500000,amount_max_inclusive=False,value_num=.5,product='Synthetic',offer_id='synthetic',rate_is_maximum=False)
    return dict(interest_slabs=[rate],maintenance_slabs=[fee(0,'average balance up to BDT 10,000',vat=None),fee(200,'average balance BDT 25,001 to 200,000'),fee(300,'average balance above 10 Lac')],debit_main=fee(600,periods=1),sms=None)
def test_brac_style_worked_net_and_unknown_sms():
    b=bank();c=calculate(b,100000,True,False)
    assert c['interest']==500 and yearly(c['maintenance'])==460 and yearly(c['debit'])==690 and c['net']==-650
    assert calculate(b,100000,False,False)['net']==40
    assert calculate(b,100000,True,True)['net'] is None
    assert calculate(b,5000,False,False)['maintenance']['value_num']==0
    assert calculate(b,1500000,False,False)['maintenance']['value_num']==300
    b['maintenance_slabs']=[fee(300,'average balance above 10 Lac')]
    assert calculate(b,100000,False,False)['net'] is None

def test_maximum_interest_and_special_audience_cannot_supply_general_net():
    b=bank();b['interest_slabs'][0]['rate_is_maximum']=True
    assert calculate(b,100000,False,False)['net'] is None
    b=bank();b['interest_slabs'][0]['audience']='check'
    assert calculate(b,100000,False,False)['interest'] is None
    b=bank();assert calculate(b,100000,False,False,'women')['net'] is None

def test_sms_half_year_and_included_vat_not_added_twice():
    f=fee(150,periods=2);assert yearly(f)==345
    f=fee(15,periods=1);f['vat_included']=True;assert yearly(f)==15
@pytest.mark.parametrize('name,expected',[('EBL Classic Debit Card','main'),('VISA Debit Card','main'),('Nexus-EMV Debit Card (Local)','main'),('EBL Platinum Debit Card','variant'),('EBL UnionPay Classic Debit Card','variant'),('EBL Prepaid Card','excluded'),('EBL Mastercard Women Prepaid Card','excluded')])
def test_debit_classification(name,expected):assert debit_variant(name)==expected

def test_account_endpoint_rejects_balance_and_makes_no_provider_call():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from ilma_api.db import Base
    from ilma_api.main import app,get_db
    from fastapi.testclient import TestClient
    from unittest.mock import patch,AsyncMock
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False});Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db]=lambda:db
        try:
            with TestClient(app) as c,patch('httpx.AsyncClient.post',new=AsyncMock()) as provider:
                for query in ['balance=100000','amount=100000','card=false']:assert c.get('/v1/services/accounts?'+query).status_code==422
                assert c.get('/v1/services/accounts?item=other&audience=all').status_code==200
                assert c.get('/v1/services/compare?product_type=account_fee&item=savings&audience=all').status_code==200
                assert c.get('/v1/services/accounts?audience=check').status_code==422
                provider.assert_not_awaited()
        finally:app.dependency_overrides.clear()
    engine.dispose()


def test_paragraph_checker_rejects_top_slab_fee_at_one_lakh():
    from ilma_api.account_readout import check_draft
    pack=dict(balance=100000,item='savings',banks=[dict(name_bn='ব্র্যাক ব্যাংক',maintenance_half_year=200,maintenance_year=460),dict(name_bn='ব্যাংক এশিয়া',maintenance_half_year=None)])
    assert not check_draft('১ লাখ টাকায় ৩০০ টাকা রক্ষণাবেক্ষণ ফি।',pack)
    assert check_draft('ব্র্যাক ব্যাংকে ছয় মাসে ২০০ টাকা রক্ষণাবেক্ষণ ফি।',pack)
    assert not check_draft('ব্যাংক এশিয়ায় ২০০ টাকা রক্ষণাবেক্ষণ ফি।',pack)
    assert not check_draft('নেট নাল থাকায় বলা যায় না।',pack)
