"""Two banks joined by "and", term questions and follow-up bank names; synthetic rows only."""
import asyncio
from unittest.mock import patch,AsyncMock
import pytest
from test_voice_agent import db,BANKS
from ilma_api.db import Institution
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_resolver import resolve
from ilma_api.human_turn import run

DBBL=dict(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',coverage='full',aliases=['Dutch Bangla Bank','ডাচ বাংলা ব্যাংক'])
BANKS3=[*BANKS,DBBL]

@pytest.fixture(autouse=True)
def contextual_mode(isolate_voice_mode,monkeypatch):
    from ilma_api import settings
    monkeypatch.setattr(settings,'HUMAN_VOICE_ENABLED',True)

def turn(db,text,lang,c=None,banks=BANKS3):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=AssertionError('no model'))):
            return await run(text,VoiceContext(agent=True,ui_lang=lang,speak=False,conversation=c or Conversation(language=lang)),banks,db)
    return asyncio.run(scenario())

@pytest.mark.parametrize('text,ids',[
 ('আমাকে ডাচ বাংলা ব্যাংক এবং ইবিএল এর সেভিংস অ্যাকাউন্ট এর ডিটেইলস বলবেন কি',[3,2]),
 ('Dutch Bangla Bank and EBL FDR rates',[3,2]),
 ('EBL and BRAC DPS',[2,1]),
 ('ব্র্যাক ও ইবিএলের এফডিআর',[1,2])])
def test_two_banks_joined_by_and_are_both_answered_in_spoken_order(text,ids):
    r=resolve(text,Conversation(),BANKS3)
    assert r.intent=='compare' and r.compare_bank_ids==ids and r.bank_id==ids[0]

def test_a_bank_without_rows_does_not_hide_the_other_banks_rate(db):
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'));db.commit()
    for lang,rate in [('en','9.1'),('bn','৯.১')]:
        text='Dutch Bangla Bank and EBL FDR rates' if lang=='en' else 'ডাচ বাংলা ব্যাংক এবং ইবিএল এর এফডিআর রেট'
        result=turn(db,text,lang)
        assert rate in result['speech'],result['speech']
        assert ('Dutch' in result['speech']) if lang=='en' else ('ডাচ' in result['speech']),result['speech']

@pytest.mark.parametrize('text',['What is NPL','What is FDR?','What is DPS'])
def test_plain_what_is_questions_explain_the_term(text):
    assert resolve(text,Conversation(institution_id=2),BANKS).intent=='explain_term'

def test_a_missing_service_ends_with_a_next_step(db):
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'));db.commit()
    result=turn(db,'আমাকে ডাচ বাংলা ব্যাংক এবং ইবিএল এর সেভিংস অ্যাকাউন্ট এর ডিটেইলস বলবেন কি','bn')
    assert 'পরীক্ষা ডাচ ব্যাংকের' in result['speech'] and 'পরীক্ষা ইবিএল ব্যাংকের' in result['speech']
    assert result['next']['question']

def test_joined_answer_keeps_the_spoken_bank_order(db):
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'));db.commit()
    speech=turn(db,'Dutch Bangla Bank and EBL FDR rates','en')['speech']
    assert speech.index('Dutch Test Bank')<speech.index('EBL Test Bank'),speech

def test_general_question_skips_an_account_for_one_age_group(db):
    from ilma_api.db import ServiceOffer
    from datetime import date
    for oid,name,rate in [('test-50plus','EBL 50 Plus Savings',2.0),('test-general','EBL High Earning Account',4.0)]:
        db.add(ServiceOffer(offer_id=oid,institution_id=2,category='deposit',product=name,product_type='savings',network=None,tier=None,tenor_months=None,attribute='rate',value_num=rate,value_text=str(rate),unit='pct_year',condition='',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/synthetic.pdf',page=1,quote=f'Synthetic rate {rate}%',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='test-fixture',checked_on=date(2026,10,1)))
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'));db.commit()
    speech=turn(db,'Dutch Bangla Bank and EBL savings rates','en')['speech']
    assert '50 Plus' not in speech and '4%' in speech,speech

def test_a_range_is_not_set_against_a_one_year_rate_as_if_alike(db):
    from ilma_api.db import ServiceOffer
    from datetime import date
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'))
    db.add(ServiceOffer(offer_id='test-dbbl-range',institution_id=3,category='deposit',product='Fixed deposit',product_type='fdr',network=None,tier=None,tenor_months=None,attribute='rate_range',value_num=None,value_text='7.75-9.75',unit='pct_year',condition='',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/dbbl.pdf',page=1,quote='Synthetic range',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='manual_sumon',checked_on=date(2026,10,1)))
    db.commit()
    speech=turn(db,'Dutch Bangla Bank and EBL FDR rates','en')['speech']
    assert 'Dutch Test Bank has no 1-year FDR rate in our data' in speech and '7.75% to 9.75%' in speech and '9.1%' in speech,speech
    assert speech.index('Dutch Test Bank')<speech.index('EBL Test Bank'),speech

def test_a_slabbed_savings_account_gives_its_range_not_one_slab(db):
    from ilma_api.db import ServiceOffer
    from datetime import date
    for oid,rate in [('test-he-1',2.0),('test-he-2',7.0)]:
        db.add(ServiceOffer(offer_id=oid,institution_id=2,category='deposit',product='EBL High Earning Account',product_type='savings',network=None,tier=None,tenor_months=None,attribute='rate',value_num=rate,value_text=str(rate),unit='pct_year',condition='',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/synthetic.pdf',page=1,quote=f'Synthetic rate {rate}%',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='test-fixture',checked_on=date(2026,10,1)))
    db.add(Institution(id=3,slug='dutchbangl',name_en='Dutch Test Bank',name_bn='পরীক্ষা ডাচ ব্যাংক',type='bank',islamic=False,licensed=True,listed=True,coverage='full'));db.commit()
    speech=turn(db,'Dutch Bangla Bank and EBL savings rates','en')['speech']
    assert '2% to 7% by balance' in speech,speech


def test_one_bank_in_a_comparison_is_compared_with_all_banks():
    from ilma_api.human_resolver import resolve
    r=resolve('compare EBL and Bank DPS',Conversation(language='en'),BANKS)
    assert r.intent=='compare' and r.compare_bank_ids==[] and r.bank_id==2

def test_other_banks_is_not_a_bank_name():
    from ilma_api.human_resolver import resolve
    c=Conversation(language='en',institution_id=2,product='dps',last_intent='service_detail')
    for said in ('compare with other banks','অন্য ব্যাংকের সাথে মিলিয়ে দেখুন'):
        r=resolve(said,c,BANKS)
        assert r.intent=='compare' and not r.candidates and r.bank_id==2,said


def test_compare_starts_with_the_bank_said_first():
    from ilma_api.human_resolver import resolve
    assert resolve('compare EBL and BRAC Bank DPS',Conversation(language='en'),BANKS).bank_id==2
    assert resolve('compare BRAC Bank and EBL DPS',Conversation(language='en'),BANKS).bank_id==1

def test_month_rates_take_the_best_general_scheme_at_a_term():
    from ilma_api.human_answers import month_rates
    row=lambda id,name,rate:dict(fact_id=id,values=dict(product=name,rate=rate,tenor_options=[36,60]))
    assert month_rates([row('l','Lakhopati Deposit Scheme',6),row('k','Kotipoti DPS',9),row('w','DPS for Women',10)])[60]==(9,'k')


def test_sound_alike_names_beside_bank_find_the_bank():
    from ilma_api.voice_text import sound_key,match_candidates
    assert {sound_key(w) for w in ('brac','black','bragg','break','brick','ব্র্যাক','ব্ল্যাক','ব্রেক')}=={'brk'}
    assert sound_key('eastern')==sound_key('ইস্টার্ন')
    banks=[dict(id=1,slug='bracbank',name_en='BRAC Bank PLC',name_bn='ব্র্যাক ব্যাংক পিএলসি',type='bank',coverage='full',aliases=['BRAC Bank']),dict(id=2,slug='ebl',name_en='Eastern Bank PLC',name_bn='ইস্টার্ন ব্যাংক পিএলসি',type='bank',coverage='full',aliases=['EBL'])]
    for said,bank in (('tell me about Brick Bank DPS',1),('Breck bank FDR',1),('ব্রেক ব্যাংকের এফডিআর',1),('Eastren Bank FDR',2)):
        assert match_candidates(said,banks)[0]['id']==bank,said
    for said in ('the best bank','my bank account','a good bank','any bank','brick wall'):
        assert match_candidates(said,banks)==[],said

def test_lost_second_bank_name_is_flagged():
    from ilma_api.human_resolver import resolve
    r=resolve('compare EBL and Bank DPS',Conversation(language='en'),BANKS)
    assert r.missing_second and r.compare_bank_ids==[]
    assert not resolve('compare EBL DPS',Conversation(language='en'),BANKS).missing_second
