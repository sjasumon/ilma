"""Tiny handwritten synthetic award rows; no exported pack, real pages or paid calls."""
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from ilma_api.db import Base,Institution,BankAward,BankAwardSource
from ilma_api.migrate_awards import read,load
from ilma_api.human_tokens import FactToken
from ilma_api.human_turn import introduction,award_answer
from ilma_api.voice_agent import Conversation

AWARDERS=[{'awarder_id':'synthetic_mag','name':'Synthetic Magazine','name_bn':'পরীক্ষা ম্যাগাজিন','awarder_type':'intl_publication','country':'X','website':'https://example.test',
  'entry_fee':'','winner_package':'','publishes_method':'','publishes_winners':'yes','paid_flag':'unknown','evidence_url':'','evidence_quote':'','note':''}]
def award(id,bank,year,confirmation,name='Synthetic Awards: Best Bank in Testland',name_bn='পরীক্ষা পুরস্কার: টেস্টল্যান্ডের সেরা ব্যাংক',paid='unknown',hide='0',medal=''):
    return {'award_id':id,'bank_code':bank,'awarder_id':'synthetic_mag','award_name_en':name,'award_name_bn':name_bn,'short_name_bn':'সেরা ব্যাংক','category':'','award_year':year,
      'announced_on':'','result':'won','rank':'','medal':medal,'scope':'country','confirmation':confirmation,'paid_flag':paid,'hide_in_app':hide,'source_count':'1'}
AWARDS=[award('a-old','EBL','2023','awarder_confirmed'),award('a-new','EBL','2025','awarder_confirmed'),award('a-paid','EBL','2026','awarder_confirmed',paid='likely_paid'),
  award('a-self','EBL','2026','self_reported'),award('a-risky','ISLAMIBANK','2024','awarder_confirmed'),award('a-undated','EBL','','self_reported')]
SOURCE={'url':'https://example.test/winners','source_kind':'awarder','outlet':'Synthetic Magazine','published_on':'2025-07-01','quote':'Synthetic winner sentence','language':'en','is_pr_copy':'0','page_no':'','document_id':'1'}
SOURCES=[{**SOURCE,'award_id':a['award_id']} for a in AWARDS]+[{**SOURCE,'award_id':'a-new'}]

@pytest.fixture
def db(tmp_path):
    for name,rows in [('awarders.csv',AWARDERS),('awards.csv',AWARDS),('award_sources.csv',SOURCES)]:
        with open(tmp_path/name,'w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,list(rows[0]));writer.writeheader();writer.writerows(rows)
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([Institution(id=1,slug='ebl',name_bn='পরীক্ষা ইস্টার্ন',name_en='Synthetic Eastern',type='bank',islamic=False,licensed=True,listed=True,coverage='full'),
          Institution(id=2,slug='islamibank',name_bn='পরীক্ষা ইসলামী',name_en='Synthetic Islami',type='bank',islamic=True,licensed=True,listed=True,coverage='full')])
        session.commit()
        added,skipped=load(session,read(tmp_path));session.commit()
        assert added=={'awarder':1,'bank_award':6,'bank_award_source':6} and not skipped
        assert load(session,read(tmp_path))[0]=={'awarder':0,'bank_award':0,'bank_award_source':0}
        yield session
    engine.dispose()

def facts(bank,status,founded=None):
    rows={f'status:{bank}':{'fact_id':f'status:{bank}','kind':'status','institution_id':bank,'status':{'code':status},'values':{}}}
    if founded:rows['profile:1']={'fact_id':'profile:1','kind':'profile','institution_id':bank,'values':{'field':'founded_year','value':founded}}
    return rows

def registry(bank,name):return {'bank:'+str(bank):FactToken(name,(),bank,'bank')}

def test_repeated_source_rows_are_stored_once(db):
    assert db.query(BankAwardSource).filter_by(award_id='a-new').count()==1

def test_strong_bank_introduction_names_founding_year_and_most_recent_confirmed_award(db):
    lines,extra=introduction(db,Conversation(institution_id=1,language='bn'),registry(1,'পরীক্ষা ইস্টার্ন'),facts(1,'strong','1992'))
    assert [s for s,_ in lines]==['পরীক্ষা ইস্টার্ন যাত্রা শুরু করে ১৯৯২ সালে, আর ২০২৫ সালে পরীক্ষা ম্যাগাজিন একে টেস্টল্যান্ডের সেরা ব্যাংক বলেছে।']
    assert lines[0][1]==['profile:1','award:a-new']
    assert list(extra)==['award:a-new'] and 'নিরাপত্তার প্রমাণ নয়' in extra['award:a-new']['text_bn']
    assert not any(word in s for s,_ in lines for word in ('তাই','নিরাপদ'))

def test_introduction_names_the_bank_in_the_award_when_no_founding_year(db):
    lines,_=introduction(db,Conversation(institution_id=1,language='en'),registry(1,'Synthetic Eastern'),facts(1,'strong'))
    assert [s for s,_ in lines]==['Synthetic Eastern was named Best Bank in Testland by Synthetic Magazine in 2025.']
    bn,_=introduction(db,Conversation(institution_id=1,language='bn'),registry(1,'পরীক্ষা ইস্টার্ন'),facts(1,'strong'))
    assert [s for s,_ in bn]==['পরীক্ষা ইস্টার্নকে ২০২৫ সালে পরীক্ষা ম্যাগাজিন টেস্টল্যান্ডের সেরা ব্যাংক বলেছে।']

@pytest.mark.parametrize('status',['high','no_data','watch'])
def test_no_introduction_award_unless_the_bank_is_strong(db,status):
    assert introduction(db,Conversation(institution_id=2,language='bn'),registry(2,'পরীক্ষা ইসলামী'),facts(2,status))==([],{})

def test_direct_award_question_lists_verified_awards_and_warns_for_high_risk(db,monkeypatch):
    monkeypatch.setattr('ilma_api.report_card.get_institution_report_card',lambda session,id:{'status':{'code':'high' if id==2 else 'strong'}})
    lines,items=award_answer(db,Conversation(institution_id=1,language='bn'),registry(1,'পরীক্ষা ইস্টার্ন'))
    assert [s for s,_ in lines]==['পরীক্ষা ইস্টার্নকে ২০২৫ সালে পরীক্ষা ম্যাগাজিন টেস্টল্যান্ডের সেরা ব্যাংক বলেছে।','২০২৩ সালে পরীক্ষা ম্যাগাজিন একে টেস্টল্যান্ডের সেরা ব্যাংক বলেছে।']
    assert items[0]['text_bn'].startswith('স্বীকৃতি: পরীক্ষা পুরস্কার: টেস্টল্যান্ডের সেরা ব্যাংক — ')
    assert [i['fact_id'] for i in items]==['award:a-new','award:a-old']
    risky,_=award_answer(db,Conversation(institution_id=2,language='bn'),registry(2,'পরীক্ষা ইসলামী'))
    assert risky[-1][0].startswith('তবে পুরস্কার ব্যাংকের এখনকার অবস্থা বোঝায় না।')

def test_award_question_resolves_to_awards_intent():
    from ilma_api.human_resolver import resolve
    for text in ['এই ব্যাংক কী কী পুরস্কার পেয়েছে?','Has this bank won any awards?']:
        assert resolve(text,Conversation(institution_id=1),[]).intent=='bank_awards'

def test_award_with_an_unregistered_awarder_is_skipped(db,tmp_path):
    rows=[{**award('a-orphan','EBL','2020','self_reported'),'awarder_id':'missing'}]
    with open(tmp_path/'awards.csv','w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,list(rows[0]));writer.writeheader();writer.writerows(rows)
    added,skipped=load(db,read(tmp_path))
    assert skipped==['a-orphan'] and db.get(BankAward,'a-orphan') is None
