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


def test_repeat_refreshes_previous_release_audio_url(tmp_path,monkeypatch):
    r,c,m,p=fixture(tmp_path,monkeypatch);m['clips']['bn:q001']['source_sha256']=reviewed.fingerprint({});p.write_text(json.dumps(m))
    r.update(reviewed_answer_key='bn:q001',reviewed_audio_url='/static/audio/answers/bn/q001.mp3?v=old',speech=m['clips']['bn:q001']['text'],facts=[],conversation={'institution_id':1})
    out=reviewed.refresh_repeat(r)
    assert out['reviewed_audio_url'].endswith(m['clips']['bn:q001']['audio_sha256'][:16])
    assert r['reviewed_audio_url'].endswith('old'),'Stored input must not be mutated'

@pytest.mark.parametrize('problem',['source','missing'])
def test_repeat_discards_stale_recording_when_it_cannot_be_revalidated(tmp_path,monkeypatch,problem):
    r,c,m,p=fixture(tmp_path,monkeypatch);r.update(reviewed_answer_key='bn:q001',reviewed_audio_url='/static/audio/answers/bn/q001.mp3?v=old',speech=m['clips']['bn:q001']['text'],facts=[],conversation={'institution_id':1})
    if problem=='missing':p.unlink()
    out=reviewed.refresh_repeat(r)
    assert 'reviewed_audio_url' not in out


def test_extended_complete_corpus_preserves_old_answers(tmp_path,monkeypatch):
    from ilma_api.reviewed_sources import complete
    result,context,manifest,path=fixture(tmp_path,monkeypatch)
    original=manifest['clips']['bn:q001']
    for language in ('bn','en'):
        for n in range(94,151):
            key=f'{language}:q{n:03d}'
            manifest['clips'][key]={**original,'key':key,'language':language,'question_keys':[]}
    manifest.update(question_count=150,expected_clips=300)
    assert complete(manifest)
    path.write_text(json.dumps(manifest))
    assert reviewed.apply(result,'প্রশ্ন',context,{})['speech']=='পরীক্ষার উত্তর।'
    manifest['clips']['en:q151']=manifest['clips'].pop('en:q150')
    assert not complete(manifest)


def test_extension_evidence_changes_invalidate_audio(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from ilma_api import reviewed_sources
    result,context,manifest,path=fixture(tmp_path,monkeypatch)
    item=manifest['clips']['bn:q001'];item['source_refs']=[{'kind':'service','id':'synthetic-rate'}]
    r=SimpleNamespace(**{k:None for k in ('bank_id','product','tenor','basis','network','tier','intent','compare_bank_ids','requested_field','requested_metric')})
    item['slots']=reviewed.slots(r)
    evidence=[dict(kind='service',id='synthetic-rate',values={'value_num':'3','quote':'Synthetic rate with eligibility'},source={})]
    monkeypatch.setattr(reviewed_sources,'evidence',lambda db,refs:evidence)
    from ilma_api.human_facts import threshold_config
    item['source_sha256']=reviewed.fingerprint({'reviewed_evidence':evidence,'thresholds':threshold_config()})
    path.write_text(json.dumps(manifest))
    context=reviewed_sources.context(None,'প্রশ্ন',r,{})
    assert reviewed.apply(result,'প্রশ্ন',context,{})['reviewed_answer_key']=='bn:q001'
    evidence[0]['values']['value_num']='4'
    changed=reviewed_sources.context(None,'প্রশ্ন',r,{})
    assert 'reviewed_audio_url' not in reviewed.apply(result,'প্রশ্ন',changed,{})
    def missing(db,refs):raise ValueError('Missing source')
    monkeypatch.setattr(reviewed_sources,'evidence',missing)
    assert 'reviewed_audio_url' not in reviewed.apply(result,'প্রশ্ন',reviewed_sources.context(None,'প্রশ্ন',r,{}),{})


def test_extension_uses_language_specific_slots_and_preserves_source_bank(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from ilma_api import reviewed_sources
    from ilma_api.human_facts import threshold_config
    result,old_context,manifest,path=fixture(tmp_path,monkeypatch)
    fields={k:None for k in ('bank_id','product','tenor','basis','network','tier','intent','compare_bank_ids','requested_field','requested_metric')}
    rows=[dict(kind='service',id='synthetic',values={'institution_id':'1','quote':'Synthetic condition'},source={})]
    digest=reviewed.fingerprint({'reviewed_evidence':rows,'thresholds':threshold_config()})
    for lang,intent in [('bn','bank_condition'),('en','bank_overview')]:
        item=manifest['clips'][lang+':q001'];item.update(question_keys=[reviewed.question_key('Synthetic question')],source_refs=[dict(kind='service',id='synthetic')],slots={**fields,'bank_id':1,'intent':intent},source_sha256=digest,conversation_bank_id=1)
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(reviewed_sources,'evidence',lambda db,refs:rows)
    prior=SimpleNamespace(**{**fields,'bank_id':2,'intent':'service_detail'})
    context=reviewed_sources.context(None,'Synthetic question',prior,{},'en')
    assert context['slots']['intent']=='bank_overview'
    assert context['slots']['bank_id']==1 and context['conversation_bank_id']==1
    assert context['source_sha256']==digest
    # An example bank in a general answer must not replace the user's bank.
    for lang in ('bn','en'):manifest['clips'][lang+':q001'].pop('conversation_bank_id')
    path.write_text(json.dumps(manifest))
    assert reviewed_sources.context(None,'Synthetic question',prior,{},'en',2)['conversation_bank_id']==2
    assert reviewed_sources.context(None,'Synthetic question',prior,{},'en',None)['conversation_bank_id'] is None


@pytest.mark.parametrize('question,expected,affirmative',[('Compare or another service?',['compare','services'],None),('Would you like to compare?',['compare','ask_bank'],'compare'),('Would you like another service?',['services','ask_bank'],'services'),("Would you like this bank's services?",['services','ask_bank'],'services'),('Would you like to hear more?',['services','ask_bank'],'detail')])
def test_reviewed_closing_controls_match_the_recorded_offer(tmp_path,monkeypatch,question,expected,affirmative):
    result,context,manifest,path=fixture(tmp_path,monkeypatch)
    clip=manifest['clips']['bn:q001'];clip['text']='Synthetic body. '+question;clip['text_sha256']=hashlib.sha256(clip['text'].encode()).hexdigest();path.write_text(json.dumps(manifest))
    result['next'].update(affirmative_action='detail',negative_action='old')
    out=reviewed.apply(result,'প্রশ্ন',context,{})
    assert out['next']['question']==question
    assert [option['value'] for option in out['next']['options']]==expected
    assert out['next'].get('affirmative_action')==affirmative
    assert out['next'].get('negative_action')==('stop' if affirmative else None)


def test_verified_saved_answer_exits_stale_typing_recovery(tmp_path,monkeypatch):
    result,context,manifest,path=fixture(tmp_path,monkeypatch)
    result.update(offer_typing=True,conversation={'misses':2,'institution_id':1})
    out=reviewed.apply(result,'প্রশ্ন',context,{})
    assert out['reviewed_answer_key']=='bn:q001'
    assert out['conversation']['misses']==0 and out['offer_typing'] is False


def card_fact(id,kind,text,**values):
    return dict(fact_id=id,kind=kind,institution_id=1,values=values,text_en=text,text_bn=text,source=dict(source_url='https://example.test/'+id))

def test_card_holds_only_the_facts_each_sentence_states():
    capital=card_fact('capital','figure','Capital ratio 15.49% · minimum 12.5% · 2025')
    loans=card_fact('loans','figure','Bad loans 2.24%, which is low (2025).')
    status=card_fact('status','status','Synthetic Bank: Low risk')
    incident=card_fact('incident','history','Synthetic incident headline 15.49')
    rates=[card_fact(f'rate-{n}','service','',rate=2,product=f'Synthetic {n}',unit='pct_year') for n in range(60)]
    body='Synthetic Bank has an award. An award is not proof that a bank is safe. Its bad loans are 2.24%, as of 2025. It is in good condition: its capital ratio is 15.49%, against a 12.5% minimum.'
    lines,public=reviewed.spoken_lines(body,'en',[capital,loans,status,incident,*rates],[status],'bank_overview')
    assert [line['text'] for line in lines]==['Its bad loans are 2.24%, as of 2025.','It is in good condition: its capital ratio is 15.49%, against a 12.5% minimum.']
    assert {f['fact_id'] for f in public}=={'capital','loans','status'}
    assert len(lines)<=4

def test_card_keeps_a_cited_incident_only_for_a_history_question():
    incident=card_fact('incident','history','Synthetic incident headline')
    assert reviewed.spoken_lines('A synthetic event happened.','en',[incident],[incident],'bank_overview')==([],[])
    lines,public=reviewed.spoken_lines('A synthetic event happened.','en',[incident],[incident],'bank_history')
    assert [f['fact_id'] for f in public]==['incident'] and len(lines)==1

def test_card_names_the_account_a_sentence_states_among_equal_rates():
    rates=[card_fact(id,'service','',rate=2,product=name,unit='pct_year') for id,name in [('a','Synthetic Campus Account'),('b','Synthetic Women Savings'),('c','Synthetic Junior Plan')]]
    lines,public=reviewed.spoken_lines('The Women Savings pays 2%.','en',rates,[],'service_detail')
    assert [f['fact_id'] for f in public]==['b'] and len(lines)==1

def test_declared_evidence_backs_an_answer_with_no_quoted_number():
    row=card_fact('reviewed:profile:1','reviewed_evidence','Synthetic quote')
    lines,public=reviewed.spoken_lines('A plain reviewed sentence. Another one.','en',[row],[],None)
    assert len(lines)==1 and [f['fact_id'] for f in public]==['reviewed:profile:1']

def test_bangla_digits_match_the_stored_figure():
    loans=card_fact('loans','figure','Bad loans 2.24%, which is low (2025).')
    lines,_=reviewed.spoken_lines('খেলাপি ঋণ ২.২৪%।','bn',[loans],[],'bank_overview')
    assert lines[0]['fact_ids']==['loans']

def test_award_and_status_sentences_keep_their_sources_without_being_cited():
    award=card_fact('award','award','Synthetic award')
    status=card_fact('status','status','Synthetic Bank: Low risk')
    lines,public=reviewed.spoken_lines('Synthetic Bank was named best bank. It is in good condition.','en',[award,status],[],'bank_overview')
    assert [line['fact_ids'] for line in lines]==[['award'],['status']] and len(public)==2

def test_award_caveat_is_not_cited_as_the_award():
    award=card_fact('award','award','Synthetic award')
    lines,_=reviewed.spoken_lines('Synthetic Bank was named best bank. An award is not proof that a bank is safe.','en',[award],[],'bank_overview')
    assert [line['text'] for line in lines]==['Synthetic Bank was named best bank.']
    lines,_=reviewed.spoken_lines('পরীক্ষা ব্যাংককে সেরা ব্যাংক বলেছে। তবে পুরস্কার ব্যাংকের নিরাপত্তার প্রমাণ নয়।','bn',[award],[],'bank_overview')
    assert [line['text'] for line in lines]==['পরীক্ষা ব্যাংককে সেরা ব্যাংক বলেছে।']
