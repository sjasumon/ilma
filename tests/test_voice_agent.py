"""Handwritten synthetic BRAC/EBL-shaped fixtures, not real bank claims."""
import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pydantic import ValidationError
from ilma_api import settings
from ilma_api.db import Base, Institution, Source, InsuranceRule, ServiceOffer, Fact, AppWatchItem, AppModelCall
from ilma_api.voice_text import VoiceContext
from ilma_api.voice_agent import (Conversation,Plan,ToolArgs,Wording,check_wording,run_agent_turn,spoken_choice,
    bank_summary,bank_reasons,bank_figures,bank_history,services_overview,service_detail,service_compare,insurance,open_proof,watch_bank,end,prepare_schema,validate_plan)
from ilma_api.voice_pipeline import parse_request,run_pipeline

@pytest.fixture
def db():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as session:
        source=Source(source_id='synthetic-source',url='https://example.test/synthetic.pdf',title='Handwritten synthetic schedule',publisher='Example publisher',published_at=date(2026,10,1),page=1,checked_by='test-fixture',checked_on=date(2026,10,1))
        session.add(source)
        for id,slug,en,bn,value in [(1,'bracbank','BRAC Test Bank','পরীক্ষা ব্র্যাক ব্যাংক',8.5),(2,'ebl','EBL Test Bank','পরীক্ষা ইবিএল ব্যাংক',9.1)]:
            session.add(Institution(id=id,slug=slug,name_en=en,name_bn=bn,type='bank',islamic=False,licensed=True,listed=True,coverage='full'))
            session.add(Fact(fact_id=f'test-npl-{id}',institution_id=id,metric='npl_ratio',value=.02,unit='ratio',period='FY2026',period_end=date(2026,6,30),basis='solo',source_id='synthetic-source',quote='Synthetic ratio 2 percent',checked_by='test-fixture',checked_on=date(2026,10,1)))
            session.add(ServiceOffer(offer_id=f'test-fdr-{id}',institution_id=id,category='deposit',product='Synthetic term deposit',product_type='fdr',network=None,tier=None,tenor_months=12,attribute='rate',value_num=value,value_text=str(value),unit='pct_year',condition='Same synthetic terms',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url=source.url,page=1,quote=f'Synthetic rate {value}%',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='test-fixture',checked_on=date(2026,10,1)))
        session.add(InsuranceRule(inst_type='bank',covered=True,limit_bdt=200000,payout_working_days=None,covered_from=date(2026,1,1),text_bn='পরীক্ষার বীমা ২ লাখ টাকা।',text_en='Synthetic insurance 2 lakh taka.',source_id=source.source_id))
        session.commit()
        yield session
    engine.dispose()

BANKS=[dict(id=1,slug='bracbank',name_en='BRAC Test Bank',name_bn='পরীক্ষা ব্র্যাক ব্যাংক',type='bank',coverage='full',aliases=['BRAC Bank']),dict(id=2,slug='ebl',name_en='EBL Test Bank',name_bn='পরীক্ষা ইবিএল ব্যাংক',type='bank',coverage='full',aliases=['Eastern Bank','EBL'])]

def context(c=None):return VoiceContext(agent=True,ui_lang='en',speak=False,conversation=c)
def call(db,text='',c=None,choice=None,candidates=(),client=None,identity=None):return asyncio.run(run_agent_turn(text,context(c),BANKS,db,candidates,choice,identity,client))
def conv(result):return Conversation.model_validate(result['conversation'])

def test_all_tools_are_sourced_and_no_silent_watch(db):
    with patch.object(settings,'META_MODEL_API_KEY',''):
        collections=[bank_summary(db,1),bank_reasons(db,1),bank_figures(db,1),bank_history(db,1),services_overview(db,1),service_detail(db,1,'fdr'),service_compare(db,'fdr'),insurance(db,1),open_proof(db,1,'test-npl-1'),end(db)]
    assert any(collections)
    for rows in collections:
        for row in rows:assert row['fact_id'] and row['text_bn'] and row['text_en'] and row['source']
    assert watch_bank(db,1,'x'*64,False)==[]
    assert db.query(AppWatchItem).count()==0
    assert watch_bank(db,1,'x'*64,True)
    assert db.query(AppWatchItem).count()==1
    assert open_proof(db,1,'test-fdr-2')==[]

@pytest.mark.parametrize('text',['BRAC Test Bank has 99% bad loans.','This bank is best.','এই ব্যাংক নিরাপদ।','Another Invented Bank is Strong.'])
def test_local_checker_rejects_invention_and_advice(db,text):
    facts=bank_summary(db,1)
    wording=Wording.model_validate({'sentences':[{'text':text,'fact_ids':[facts[0]['fact_id']]}]})
    assert not check_wording(wording,facts,BANKS)
    assert not check_wording(Wording.model_validate({'sentences':[{'text':'Strong','fact_ids':['missing']}]}),facts)


def model_client(stage_outputs):
    calls=[]
    def handler(request):
        body=json.loads(request.content);stage=body['response_format']['json_schema']['name'];calls.append(body)
        output=stage_outputs[stage]
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(output)}}],'usage':{'prompt_tokens':10,'completion_tokens':5}})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler)),calls

@pytest.mark.parametrize('text',['BRAC Test Bank has 99%.','BRAC Test Bank is best.','পরীক্ষা ব্র্যাক ব্যাংক নিরাপদ।'])
def test_failed_say_uses_actual_template(db,text):
    client,calls=model_client({'agent_say':{'sentences':[{'text':text,'fact_ids':['status:1']}]}})
    with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
        result=call(db,'BRAC Bank',candidates=[dict(BANKS[0],confidence=1,confirm=False,alias='BRAC Bank')],client=client)
    assert result['checked']=='template'
    assert result['sentences'][0]['text']==bank_summary(db,1)[0]['text_en']
    assert len(calls)==1

@pytest.mark.parametrize('plan',[{'tool':'raw_sql','args':{},'option':None},{'tool':'bank_summary','args':{'institution_id':999},'option':None},{'tool':'bank_summary','args':{'institution_id':1,'product':'crypto'},'option':None}])
def test_invalid_plan_clarifies_without_running_tool(db,plan):
    client,calls=model_client({'agent_plan':plan})
    with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
        result=call(db,'tell me about this bank',Conversation(state='BANK',institution_id=1),client=client)
    assert result['conversation']['state']=='ASK_BANK'
    assert all(f['fact_id'].startswith('script:') for f in result['facts'])
    assert len(calls)==1


def test_full_tap_path_without_any_model_call(db):
    with patch.object(settings,'META_MODEL_API_KEY',''):
        result=call(db,'BRAC Bank',candidates=[dict(BANKS[0],confidence=1,confirm=False,alias='BRAC Bank')])
    assert result['conversation']['state']=='BANK'
    with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('No model on taps'))):
        for choice,state in [('services','SERVICES'),('fdr','SERVICE'),('compare','COMPARE'),('bank','BANK')]:
            result=call(db,c=conv(result),choice=choice)
            assert result['conversation']['state']==state
            assert len(result['trace']['steps'])==5
        assert result['conversation']['institution_id']==2
    assert all(f.get('status') for f in result['facts'] if f['fact_id'].startswith('status:'))


def test_second_claim_check_and_metadata_only_audit(db):
    client,calls=model_client({'agent_say':{'sentences':[{'text':'BRAC Test Bank: Strong','fact_ids':['status:1']}]},'agent_check':{'ok':True,'bad_sentence_ids':[]}})
    # The rules may classify sparse synthetic data as no_data; use the actual label.
    expected=bank_summary(db,1)[0]['text_en']
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        output={'sentences':[{'text':expected,'fact_ids':['status:1']}]} if body['response_format']['json_schema']['name']=='agent_say' else {'ok':True,'bad_sentence_ids':[]}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(output)}}]})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
        result=call(db,'BRAC Bank',candidates=[dict(BANKS[0],confidence=1,confirm=False,alias='BRAC Bank')],client=client)
    assert result['checked']=='model'
    assert db.query(AppModelCall).count()==2
    assert not {'prompt','text','transcript','response','audio'} & set(AppModelCall.__table__.columns.keys())

@pytest.mark.parametrize('state,reply,expected',[
 ('BANK','সেবা','services'),('BANK','দুই','services'),('BANK','আরও বিস্তারিত','detail'),('BANK','one','detail'),
 ('DETAIL','হিসাব','figures'),('DETAIL','দুই','history'),('DETAIL','history','history'),
 ('SERVICES','এফডিআর','fdr'),('SERVICES','ডিপিএস','dps'),('SERVICES','না, কার্ড','card'),('SERVICES','home loan','home_loan'),
 ('SERVICE','তুলনা','compare'),('SERVICE','না','next'),('SERVICE','card','card'),
 ('FIGURES','অন্য ব্যাংক','ask_bank'),('NEXT','দুই','end'),('NEXT','আবার','repeat'),('BANK','পুরো রিপোর্ট','report'),
 ('BANK','থামুন','stop'),('WATCH_CONFIRM','হ্যাঁ','yes')])
def test_twenty_spoken_script_fixtures(state,reply,expected):
    assert spoken_choice(reply,Conversation(state=state,institution_id=1))==expected


def test_watch_requires_confirmed_yes_and_six_turn_limit(db):
    result=call(db,c=Conversation(state='BANK',institution_id=1),choice='watch',identity='x'*64)
    assert result['conversation']['state']=='WATCH_CONFIRM' and db.query(AppWatchItem).count()==0
    result=call(db,c=conv(result),choice='yes',identity='x'*64)
    assert db.query(AppWatchItem).count()==1
    result=call(db,c=Conversation(state='BANK',institution_id=1,turn=5),choice='services')
    assert result['action']['type']=='end' and result['conversation']['turn']==6


def test_json_tap_request_and_input_bounds():
    c=Conversation(state='BANK',institution_id=1).model_dump()
    audio,text,mime,ctx=parse_request('application/json',json.dumps({'choice':'services','context':{'conversation':c}}).encode(),'text')
    assert ctx.choice=='services' and audio is None and not text
    from ilma_api.voice import VoiceError
    for payload in [{'choice':'raw_sql','context':{'conversation':c}},{'choice':'services'},{'text':'x','context':{'conversation':{'turn':99}}}]:
        with pytest.raises(VoiceError):parse_request('application/json',json.dumps(payload).encode(),'text')


def test_schema_only_ilma_runtime():
    from unittest.mock import Mock
    engine=Mock();engine.dialect.name='mysql';engine.url.database='project_db'
    with pytest.raises(ValueError):prepare_schema(engine)


def test_model_cannot_turn_maybe_into_watch_consent(db):
    client,calls=model_client({'agent_plan':{'tool':'watch_bank','args':{'institution_id':1},'option':'yes'}})
    with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
        result=call(db,'maybe',Conversation(state='WATCH_CONFIRM',institution_id=1),client=client,identity='x'*64)
    assert db.query(AppWatchItem).count()==0 and result['conversation']['state']=='WATCH_CONFIRM'


def test_spoken_bank_alias_and_comparison_conditions(db):
    from ilma_api.voice_text import match_candidates
    candidates=match_candidates('Eastern Bank',BANKS)
    with patch.object(settings,'META_MODEL_API_KEY',''):
        result=call(db,'Eastern Bank',candidates=candidates)
    assert result['conversation']['institution_id']==2
    assert len(service_compare(db,'fdr',institution_id=1))==2
    db.get(ServiceOffer,'test-fdr-2').condition='A different minimum deposit slab';db.commit()
    assert len(service_compare(db,'fdr',institution_id=1))==1
    db.get(ServiceOffer,'test-fdr-1').stale=True;db.commit()
    assert all(f['institution_id']!=1 for f in service_compare(db,'fdr'))


def test_model_check_rejection_uses_template(db):
    expected=bank_summary(db,1)[0]['text_en']
    client,_=model_client({'agent_say':{'sentences':[{'text':expected,'fact_ids':['status:1']}]},'agent_check':{'ok':False,'bad_sentence_ids':[0]}})
    with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
        result=call(db,'BRAC Bank',candidates=[dict(BANKS[0],confidence=1,confirm=False,alias='BRAC Bank')],client=client)
    assert result['checked']=='template'
    assert [s['stage'] for s in result['trace']['steps']]==['ASR','PLAN','ACT','SAY','CHECK']


def test_model_call_cancellation_is_not_swallowed(db):
    from ilma_api.voice_agent import model_call
    async def run():
        client=AsyncMock();client.post.side_effect=asyncio.CancelledError
        with patch.object(settings,'META_MODEL_API_KEY','synthetic-key'):
            with pytest.raises(asyncio.CancelledError):await model_call('SAY',{},Wording,db,[],'synthetic-turn',client)
    asyncio.run(run())


def test_spoken_name_omits_only_legal_suffix(db):
    row=db.get(Institution,1);row.name_en='BRAC Test Bank PLC';row.name_bn='পরীক্ষা ব্র্যাক ব্যাংক পিএলসি';db.commit()
    summary=bank_summary(db,1)[0]
    assert summary['text_en'].startswith('BRAC Test Bank:') and 'পিএলসি' not in summary['text_bn']
    assert db.get(Institution,1).name_en.endswith('PLC')


def test_audio_target_without_truncating_content():
    import base64,subprocess
    from ilma_api.voice import ffmpeg_executable
    from ilma_api.agent_audio import normalize_agent_audio
    data=subprocess.run([ffmpeg_executable(),'-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=21','-c:a','libmp3lame','-f','mp3','pipe:1'],capture_output=True,check=True).stdout
    url='data:audio/mpeg;base64,'+base64.b64encode(data).decode()
    audio,metadata=asyncio.run(normalize_agent_audio(url))
    assert audio.startswith('data:audio/mpeg;base64,')
    assert metadata['original_duration_ms']>20000 and metadata['duration_ms']<20000
    assert 1<metadata['tempo']<=1.15
