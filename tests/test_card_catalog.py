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
    monkeypatch.setattr('ilma_api.bank_services.bank_view',lambda db,bank,**kwargs:dict(id=bank.id,slug=bank.slug,name_bn=bank.name_bn,name_en=bank.name_en,status={'code':'strong'}))
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

@pytest.mark.parametrize('wording',['1st & 2nd card free','first 2 cards free','first two supplementary cards free'])
def test_two_free_cards_is_not_overridden_by_generic_free_value(wording):
    assert condition({'attribute':'supplementary_card_fee','value_text':'Free','condition':wording})=='প্রথম দুটি অতিরিক্ত কার্ড বিনামূল্যে'

def test_selected_article_changes_with_cost_and_retains_sources(cards):
    annual=compare(cards,'card',network='Visa',tier='Gold')
    late=compare(cards,'card',network='Visa',tier='Gold',compare_by='late_fee')
    assert annual['explanation']['attribute']=='annual_fee'
    assert late['explanation']['attribute']=='late_fee'
    assert annual['explanation']['title_bn']!=late['explanation']['title_bn']
    annual_rows=next(s for s in annual['explanation']['sections'] if s['id']=='published')['paragraphs']
    late_rows=next(s for s in late['explanation']['sections'] if s['id']=='published')['paragraphs']
    assert len(annual_rows)==len(late_rows)==2
    assert '১,৯০০ টাকা' in annual_rows[0]['text_bn']
    assert '৩৫০ টাকা' in late_rows[0]['text_bn']
    assert 'বার্ষিক ফি' not in late_rows[0]['text_bn']
    assert late_rows[0]['fact_ids']==['synthetic-1-late_fee']
    assert 'Fee' in late['explanation']['title_en'] or 'fee' in late['explanation']['title_en']
    stale=next(s for s in late['explanation']['sections'] if s['id']=='stale')
    assert '৫০ টাকা' in stale['paragraphs'][0]['text_bn']

def test_selecting_cost_changes_spoken_text_and_article(cards):
    from ilma_api.service_clips import selected_narration
    annual=compare(cards,'card',network='Visa',tier='Gold')
    late=compare(cards,'card',network='Visa',tier='Gold',compare_by='late_fee')
    assert selected_narration(annual)!=selected_narration(late)
    assert annual['readout']['text']!=late['readout']['text']
    assert annual['explanation']!=late['explanation']

@pytest.mark.parametrize('attribute',['annual_fee','interest_rate','late_fee','cash_advance_fee','foreign_currency_markup'])
def test_every_compare_option_has_its_own_explanation(cards,attribute):
    result=compare(cards,'card',network='Visa',tier='Gold',compare_by=attribute)
    article=result['explanation']
    assert article['attribute']==attribute
    assert article['sections'][0]['id']=='meaning'
    if attribute in {'interest_rate','cash_advance_fee','foreign_currency_markup'}:
        assert not any(section['id']=='published' for section in article['sections'])
        assert any('এই খরচের তথ্য নেই' in p['text_bn'] for s in article['sections'] for p in s['paragraphs'])

def test_cash_article_preserves_higher_of_condition_and_atm_scope(cards):
    cards.get(Institution,1).slug='ebl'
    row=cards.query(ServiceOffer).filter_by(institution_id=1,attribute='late_fee').one()
    row.attribute='cash_advance_fee';row.value_num=180;row.value_text='180';row.unit='bdt'
    row.condition='whichever is higher; 2.5% or Tk. 180 at EBL ATM';row.quote='Synthetic cash fee 2.5% or Tk. 180 at EBL ATM'
    cards.commit()
    result=compare(cards,'card',network='Visa',tier='Gold',compare_by='cash_advance_fee')
    paragraph=next(s for s in result['explanation']['sections'] if s['id']=='published')['paragraphs'][0]
    assert '২.৫% অথবা ১৮০ টাকা, যেটি বেশি' in paragraph['text_bn']
    assert 'নিজস্ব এটিএম' in paragraph['text_bn']
    assert 'BDT 180, whichever is higher' in paragraph['text_en']
    assert 'for an EBL ATM' in paragraph['text_en']
