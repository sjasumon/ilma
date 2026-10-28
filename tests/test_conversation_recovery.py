"""Synthetic conversation and language regressions; no human audio/source exports."""
import asyncio,json,random
from unittest.mock import AsyncMock,patch
import pytest
from test_voice_agent import db,BANKS,conv
from test_voice_api import wav
from ilma_api.voice_agent import Conversation,run_agent_turn,spoken_choice,control,script_next
from ilma_api.voice_text import VoiceContext,match_candidates,decide_language
from ilma_api.voice_pipeline import run_pipeline


def turn(db,reply,c=None,choice=None,ui='en',banks=BANKS):
    ctx=VoiceContext(agent=True,speak=False,ui_lang=ui,conversation=c)
    with patch('ilma_api.voice_agent.model_call',new=AsyncMock(return_value=None)):
        return asyncio.run(run_agent_turn(reply,ctx,banks,db,match_candidates(reply,banks) if reply else [],choice))

@pytest.mark.parametrize('reply,state,expected',[
 ('আরও বিস্তারিত','BANK','DETAIL'),('ব্যাংকের সেবা','DETAIL','SERVICES'),('more details','DETAIL','DETAIL'),
 ('আর্থিক হিসাব','DETAIL','FIGURES'),('আগের ঘটনা','DETAIL','HISTORY'),('এক','DETAIL','FIGURES'),
 ('প্রথমটা','DETAIL','FIGURES'),('দ্বিতীয়টা','DETAIL','HISTORY'),('খবর','SERVICES','HISTORY'),
 ('এফডিআর রেট কত','HISTORY','SERVICE'),('এফডিআর রেট কত','ASK_BANK','SERVICE')])
def test_cross_state_commands_keep_bank_and_render_content(db,reply,state,expected):
    result=turn(db,reply,Conversation(state=state,institution_id=1))
    assert result['conversation']['state']==expected
    assert result['conversation']['institution_id']==1
    assert result['sentences'] and result['text']!=script_next(state,'en')['question']
    assert all(step['model'] in {'none','script','database/rules','template','code'} for step in result['trace']['steps'])
    if expected=='SERVICE':assert result['conversation']['product']=='fdr'


def test_two_ambiguous_misses_keep_state_bank_product_and_enable_typing(db):
    banks=BANKS+[dict(id=3,slug='dhaka',name_bn='ঢাকা ব্যাংক',name_en='Dhaka Bank',type='bank',coverage='licence_only',aliases=['ঢাকা ব্যাংক','Dhaka Bank'])]
    c=Conversation(state='DETAIL',institution_id=1,product='fdr',last_tool='bank_reasons',language='bn')
    for n in (1,2):
        result=turn(db,'ঢাকা',c,banks=banks);c=conv(result)
        assert c.state=='DETAIL' and c.institution_id==1 and c.product=='fdr' and c.last_tool=='bank_reasons'
        assert c.misses==n and result['offer_typing']==(n==2)
        assert 'বুঝতে পারিনি' in result['text'] and ('লিখে বলুন' in result['text'])==(n==2)
    recovered=turn(db,'সেবা',c)
    assert recovered['conversation']['state']=='SERVICES' and recovered['conversation']['misses']==0 and not recovered['offer_typing']


def test_question_only_guard_uses_feedback_and_preserves_state(db,caplog):
    c=Conversation(state='DETAIL',institution_id=1,language='en',last_tool='bank_reasons')
    with patch('ilma_api.voice_agent.bank_reasons',return_value=[]):
        # TOOLS stores function references, so replace that entry explicitly.
        question=script_next(c.state,'en')['question']
        with patch.dict('ilma_api.voice_agent.TOOLS',bank_reasons=lambda db,id:[control('synthetic',question,question)]):
            result=turn(db,'details',c)
    assert result['conversation']['state']=='DETAIL' and result['text']=='I did not understand.'
    assert 'voice_agent_question_loop' in caplog.text


def test_ten_seeded_valid_turns_never_reset_to_question_only(db):
    rng=random.Random(9);c=Conversation(state='BANK',institution_id=1,language='en')
    replies=['details','services','figures','history','FDR rate','more details','ব্যাংকের সেবা','আর্থিক হিসাব','আগের ঘটনা','বীমা']
    for _ in range(10):
        previous=script_next(c.state,c.language)['question']
        result=turn(db,rng.choice(replies),c);c=conv(result)
        assert result['sentences'] and result['text'] and result['text']!=previous
        assert c.institution_id==1 and not result['offer_typing'] and not result['action']
    assert c.turn==10

@pytest.mark.parametrize('text,ui,want',[
 ('ইস্টার্ন ব্যাংক কেমন আছে','en','bn'),('Is City Bank safe?','bn','en'),('IFIC Bank-এর FDR rate কত?','en','bn')])
@pytest.mark.parametrize('mode',['text','voice'])
def test_transcript_language_is_used_for_agent_answer_and_speech(db,text,ui,want,mode):
    banks=BANKS+[dict(id=3,slug='citybank',name_bn='সিটি ব্যাংক',name_en='City Bank',type='bank',coverage='full',aliases=['City Bank'])]
    banks[1]={**banks[1],'aliases':['ইস্টার্ন ব্যাংক','Eastern Bank','EBL']}
    async def run():
        with patch('ilma_api.voice_agent.model_call',new=AsyncMock(return_value=None)),patch('ilma_api.voice_pipeline.convert_audio',new=AsyncMock(return_value=wav())),patch('ilma_api.voice_pipeline.transcribe',new=AsyncMock(return_value=text)):
            return [frame async for frame in run_pipeline(b'synthetic-audio' if mode=='voice' else None,text,'audio/webm',VoiceContext(agent=True,ui_lang=ui,speak=False),banks,db,mode=mode)]
    frames=asyncio.run(run())
    transcript=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: transcript'))
    result=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: result'))
    assert transcript['language']==want
    assert result['conversation']['language']==want and result['language']==want


def test_taps_keep_conversation_language_and_bare_name_uses_preference(db):
    result=turn(db,'',Conversation(state='BANK',institution_id=1,language='bn'),choice='services',ui='en')
    assert result['language']=='bn' and result['conversation']['language']=='bn'
    assert result['next']['options'][0]['label']=='এফডিআর'
    assert decide_language('BRAC Bank',match_candidates('BRAC Bank',BANKS),'en')=='en'


def test_new_named_bank_and_product_are_retained(db):
    result=turn(db,'Eastern Bank FDR rate',Conversation(state='DETAIL',institution_id=1,language='bn'))
    assert result['conversation']['institution_id']==2 and result['conversation']['product']=='fdr'
    assert result['conversation']['state']=='SERVICE'


def test_speech_registration_uses_detected_language(db):
    async def run():
        register=AsyncMock(return_value=None)
        with patch('ilma_api.audio_cache.register_speech',new=register):
            frames=[f async for f in run_pipeline(None,'BRAC Bank কেমন আছে','',VoiceContext(agent=True,ui_lang='en',speak=True,conversation=Conversation(state='DETAIL',institution_id=1,language='en')),BANKS,db,mode='text')]
        assert register.await_count==1 and register.await_args.args[1]=='bn'
        assert any(f.startswith('event: speech_unavailable') for f in frames)
    asyncio.run(run())


def test_unrecognized_single_word_is_a_miss_without_model_guessing(db):
    async def run():
        with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('No model for a single unrecognized word'))):
            return await run_agent_turn('অর্থহীনশব্দ',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(state='DETAIL',institution_id=1,language='bn')),BANKS,db,[])
    result=asyncio.run(run())
    assert result['conversation']['state']=='DETAIL' and result['conversation']['misses']==1


@pytest.mark.parametrize('reply,language',[('more details','bn'),('more detals','bn'),('আরও বিস্তারিত','en'),('two','bn')])
@pytest.mark.parametrize('state',['BANK','DETAIL'])
def test_current_option_reply_keeps_language_in_transcript_answer_and_speech(db,reply,language,state):
    async def run():
        register=AsyncMock(return_value=None)
        ctx=VoiceContext(agent=True,ui_lang=language,speak=True,conversation=Conversation(state=state,institution_id=1,language=language))
        with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('No model for options'))),patch('ilma_api.audio_cache.register_speech',new=register):
            frames=[f async for f in run_pipeline(None,reply,'',ctx,BANKS,db,mode='text')]
        transcript=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: transcript'))
        result=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: result'))
        assert transcript['language']==language and result['language']==language and result['conversation']['language']==language
        assert register.await_args.args[1]==language and result['conversation']['institution_id']==1
    asyncio.run(run())


def test_real_english_question_can_still_change_bangla_conversation_language(db):
    result=turn(db,'How is BRAC Bank doing?',Conversation(state='BANK',institution_id=1,language='bn'),ui='bn')
    assert result['language']=='en'

@pytest.mark.parametrize('reply',['breakbank','ব্রেক ব্যাংক'])
def test_approved_brac_mishearing_aliases_are_idempotent_and_route(db,reply):
    from ilma_api.migrate_brac_aliases import add_aliases,SOURCE
    from ilma_api.db import Institution,InstitutionAlias
    assert add_aliases(db)==2;db.commit();assert add_aliases(db)==0
    bank=db.get(Institution,1)
    banks=[{**BANKS[0],'aliases':[a.alias for a in bank.aliases]} ,BANKS[1]]
    matches=match_candidates(reply,banks)
    assert len(matches)==1 and matches[0]['id']==1 and matches[0]['confidence']==1 and not matches[0]['confirm']
    assert {a.source for a in bank.aliases}=={SOURCE}
    result=turn(db,reply,banks=banks)
    assert result['conversation']['institution_id']==1 and result['conversation']['state']=='BANK'
    assert bank.name_en=='BRAC Test Bank' and bank.name_bn=='পরীক্ষা ব্র্যাক ব্যাংক'
