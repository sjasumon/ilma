"""Small handwritten examples for card identity and source-bound comparisons."""
from datetime import date,timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from ilma_api.db import Base,Institution,ServiceOffer
from ilma_api.card_catalog import card_key,clean_name,condition
from ilma_api.export_seed import card_variants
from ilma_api.bank_services import compare

@pytest.mark.parametrize('header',['ভিসা গোল্ড Gold','Visa Gold','Gold','For Gold Card'])
def test_header_normalization(header):
    row=dict(bank_id='1',network='Visa',tier='Gold',column_header=header)
    assert card_key(row)=='1:visa:gold:gold'
    assert clean_name({**row,'column_header':'Gold Flexi'})=='Gold Flexi'

def test_converter_classifies_all_facts_of_one_clean_card_together():
    rows=[dict(id=str(i),bank_id='1',network='Visa',tier='Gold',basis='conventional',category='card',product='Synthetic card',column_header=header,value='2100',col_num='1') for i,header in enumerate(['ভিসা গোল্ড Gold','Visa Gold','For Gold Card'])]
    assert set(card_variants(rows).values())=={'main'}

@pytest.mark.parametrize('text,expected',[('BDT 200 or 3% whichever is higher','৩% অথবা ২০০ টাকা, যেটি বেশি'),('whichever is higher; 2.17% or Tk. 300 at own ATM','২.১৭% অথবা ৩০০ টাকা, যেটি বেশি'),('unknown wording',''),('stale',''),('plus 15% VAT','+১৫% ভ্যাট')])
def test_plain_conditions(text,expected):
    assert condition(dict(condition=text,value_text='',attribute='cash_advance_fee'))==expected

@pytest.fixture
def cards(monkeypatch):
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    monkeypatch.setattr('ilma_api.bank_services.bank_view',lambda db,bank:dict(id=bank.id,slug=bank.slug,name_bn=bank.name_bn,name_en=bank.name_en,status={'code':'strong'}))
    with Session(engine) as db:
        for id,slug,fee,late,old in [(1,'bracbank',2100,350,False),(2,'nccbank',1900,450,False),(3,'dutchbangl',100,50,True)]:
            db.add(Institution(id=id,slug=slug,name_bn='পরীক্ষা '+str(id),name_en='Synthetic '+str(id),type='bank',islamic=False,licensed=True,listed=True,coverage='full'))
            for attribute,value,header in [('annual_fee',fee,'ভিসা গোল্ড Gold'),('late_fee',late,'Visa Gold'),('fee_waiver_rule',7,'Visa Gold')]:
                db.add(ServiceOffer(offer_id=f'synthetic-{id}-{attribute}',institution_id=id,category='card',product='Synthetic card',product_type='card',network='Visa',tier='Gold',attribute=attribute,value_num=value,value_text=str(value),unit='count' if attribute=='fee_waiver_rule' else 'bdt',condition='waived if 7 transactions' if attribute=='fee_waiver_rule' else '',basis='conventional',doc_date=date.today()-timedelta(days=500 if old else 10),stale=old,source_url='https://example.test/synthetic',page=1,quote=f'Synthetic {value}',column_header=header,variant='variant' if header=='Visa Gold' else 'main',hidden=False,hidden_reason='',checked_by='synthetic',checked_on=date.today()))
        db.commit();yield db
    engine.dispose()

def test_fresh_first_joined_facts_and_selected_fact_order(cards):
    rows=compare(cards,'card',network='Visa',tier='Gold')['rows']
    assert [r['id'] for r in rows]==[2,1,3]
    assert rows[0]['facts']['fee_waiver_rule']['condition_bn']=='বছরে ৭টি লেনদেন করলে বার্ষিক ফি মওকুফ'
    assert len(rows[0]['facts'])==10
    assert rows[0]['alternatives']==[]
    assert [r['id'] for r in compare(cards,'card',network='Visa',tier='Gold',compare_by='late_fee')['rows']]==[1,2,3]
    assert rows[0]['facts']['late_fee']['source_url']=='https://example.test/synthetic'

def test_percentage_cash_fee_is_not_compared_as_a_taka_amount(cards):
    row=cards.query(ServiceOffer).filter_by(institution_id=1,attribute='late_fee').one()
    row.attribute='cash_advance_fee';row.unit='text';row.value_text='3%';row.value_num=3
    other=cards.query(ServiceOffer).filter_by(institution_id=2,attribute='late_fee').one()
    other.attribute='cash_advance_fee';other.value_num=100;other.value_text='100'
    cards.commit()
    result=compare(cards,'card',network='Visa',tier='Gold',compare_by='cash_advance_fee')
    assert [r['id'] for r in result['rows']][:2]==[2,1]
    assert 'সরাসরি তুলনীয় নয়' in result['unit_note_bn']
