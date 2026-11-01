"""Synthetic reviewed recordings: bank/source/hash guards, no copied source exports."""
import copy,hashlib,json
import pytest
from ilma_api import reviewed_answers as reviewed
from test_voice_agent import db

def fixture(tmp_path,monkeypatch):
    directory=tmp_path/'static/audio/answers';(directory/'bn').mkdir(parents=True)
    audio=b'synthetic recording';(directory/'bn/q001.mp3').write_bytes(audio);text='পরীক্ষার উত্তর।'
    clip=dict(key='bn:q001',file='bn/q001.mp3',text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),audio_sha256=hashlib.sha256(audio).hexdigest(),language='bn',source_sha256='a'*64,slots={'bank_id':1},question_keys=[reviewed.question_key('প্রশ্ন')])
    clips={f'{lang}:q{n:03d}':{**clip,'key':f'{lang}:q{n:03d}','language':lang,'question_keys':[]} for lang in ['bn','en'] for n in range(1,94)};clips['bn:q001']=clip
    manifest=dict(batch_complete=True,expected_clips=186,clips=clips);path=directory/'manifest.json';path.write_text(json.dumps(manifest));monkeypatch.setattr(reviewed,'ROOT',tmp_path)
    result=dict(language='bn',speech='Old synthetic answer',next={'question':'Old question?','options':[]},conversation={},facts=[],sources=[])
    context={'source_sha256':'a'*64,'slots':{'bank_id':1}}
    return result,context,manifest,path

def test_exact_reviewed_text_and_saved_audio_are_selected(tmp_path,monkeypatch):
    r,c,m,p=fixture(tmp_path,monkeypatch);memory={};out=reviewed.apply(r,'প্রশ্ন',c,memory)
    assert out['speech']=='পরীক্ষার উত্তর।' and out['speech_tts']=='পরীক্ষার উত্তর।'
    assert out['reviewed_audio_url'].startswith('/static/audio/answers/bn/q001.mp3?v=')
    assert out['next']['question']=='' and out['expects_reply'] is False
    assert memory['reviewed_answer_key']=='bn:q001'

@pytest.mark.parametrize('problem',['source','bank','question','text','audio','partial','missing','traversal','tts','empty_tts'])
def test_changed_source_bank_text_or_audio_never_plays_reviewed_recording(tmp_path,monkeypatch,problem):
    r,c,m,p=fixture(tmp_path,monkeypatch);user='প্রশ্ন'
    if problem=='source':c['source_sha256']='b'*64
    elif problem=='bank':c['slots']['bank_id']=2
    elif problem=='question':user='অন্য প্রশ্ন'
    elif problem=='text':m['clips']['bn:q001']['text']='Edited'
    elif problem=='audio':(tmp_path/'static/audio/answers/bn/q001.mp3').write_bytes(b'changed')
    elif problem=='partial':m['batch_complete']=False
    elif problem=='missing':m['clips'].pop('en:q093')
    elif problem=='traversal':m['clips']['bn:q001']['file']='../private.mp3'
    elif problem=='tts':m['clips']['bn:q001'].update(tts_text='Changed speech',tts_sha256='b'*64)
    elif problem=='empty_tts':m['clips']['bn:q001'].update(tts_text='',tts_sha256=hashlib.sha256(b'').hexdigest())
    p.write_text(json.dumps(m));out=reviewed.apply(r,user,c,{})
    assert 'reviewed_audio_url' not in out and out['speech']=='Old synthetic answer'

def test_single_offered_service_accepts_yes_and_no_without_guessing():
    from ilma_api.human_agent import exact_choice
    from ilma_api.voice_agent import Conversation
    c=Conversation();memory={'last_next':{'affirmative_action':'services','negative_action':'stop','options':[]}}
    assert exact_choice('হ্যাঁ',c,memory,None)=='services'
    assert exact_choice('yes',c,memory,None)=='services'
    assert exact_choice('না',c,memory,None)=='stop'
    assert exact_choice('yes',c,{'last_next':{'options':[{'value':'fdr','label':'FDR'},{'value':'dps','label':'DPS'}]}},None) is None


def test_complete_answers_do_not_offer_the_legacy_rates_question():
    from ilma_api.human_turn import next_steps
    from ilma_api.voice_agent import Conversation
    for language in ['bn','en']:
        c=Conversation(language=language)
        for intent in ['bank_overview','bank_condition','services_list','advice_request','best_bank','service_detail']:
            question,options=next_steps(intent,c,'test')
            assert question=='' and options


def test_question_lookup_uses_privacy_redaction_not_a_disclosed_amount():
    from ilma_api.human_memory import redact_user
    for question in ['আমার ৫ লাখ টাকা কোথায় বিনিয়োগ করব?','My account number is 12345678, what is my balance?']:
        assert reviewed.question_key(question)==reviewed.question_key(redact_user(question))


def test_saved_recording_is_sent_by_pipeline_without_runtime_synthesis(db):
    import asyncio
    from unittest.mock import AsyncMock,patch
    from test_voice_agent import BANKS
    from ilma_api.human_agent import controls,render
    from ilma_api.voice_agent import Conversation
    from ilma_api.voice_text import VoiceContext
    from ilma_api.voice_pipeline import run_pipeline
    c=Conversation(institution_id=1,language='en')
    result=render(controls('bank_overview',c,'Synthetic reviewed answer.'),c,[],[dict(stage='ASR',model='none',ms=0,status='ok')])
    result['reviewed_audio_url']='/static/audio/answers/en/q001.mp3?v=aaaaaaaaaaaaaaaa'
    async def scenario():
        with patch('ilma_api.human_agent.enabled',return_value=True),patch('ilma_api.human_turn.run',AsyncMock(return_value=result)),patch('ilma_api.audio_cache.register_speech',AsyncMock()) as register:
            frames=[frame async for frame in run_pipeline(None,'Tell me about BRAC Bank','',VoiceContext(agent=True,ui_lang='en',speak=True,conversation=c),BANKS,db,mode='text',device_hash='synthetic-review')]
        register.assert_not_awaited()
        wire=''.join(f.decode() if isinstance(f,bytes) else f for f in frames)
        assert 'event: speech\n' in wire and '/static/audio/answers/en/q001.mp3' in wire
        assert 'event: speech_unavailable' not in wire and 'event: error' not in wire
    asyncio.run(scenario())


def test_display_and_spoken_script_have_separate_checked_hashes(tmp_path,monkeypatch):
    r,c,m,p=fixture(tmp_path,monkeypatch)
    m['clips']['bn:q001'].update(tts_text='পরীক্ষার কথ্য উত্তর।',tts_sha256=hashlib.sha256('পরীক্ষার কথ্য উত্তর।'.encode()).hexdigest())
    p.write_text(json.dumps(m));out=reviewed.apply(r,'প্রশ্ন',c,{})
    assert out['speech']=='পরীক্ষার উত্তর।' and out['speech_tts']=='পরীক্ষার কথ্য উত্তর।'
    assert out['reviewed_audio_url']
