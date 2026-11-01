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
