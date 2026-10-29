"""Handwritten synthetic rate examples; no source exports or paid providers."""
import asyncio,copy,json
from datetime import date
from unittest.mock import patch,AsyncMock
import httpx,pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from ilma_api.db import Base,Institution,ServiceOffer
from ilma_api.dps_compare import build,template,validate,maturity,compose,QUESTION
from ilma_api.human_resolver import resolve,is_best_dps_question
from ilma_api.voice_agent import Conversation,run_agent_turn
from ilma_api.voice_text import VoiceContext
from ilma_api.voice_numbers import pronounce

QUESTIONS=['কোন ব্যাংকের ডিপিএস সবথেকে ভালো','ডিপিএস কোথায় ভালো','best DPS কোন ব্যাংকে','কোন ব্যাংকের ডিপিএস সবচেয়ে ভালো?','ডিপিএসের সর্বোচ্চ সুদ কোন ব্যাংকে?','কোন ব্যাংকে ডিপিএসের সুদ সবচেয়ে বেশি?']

@pytest.fixture
def dps_db():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        for id,slug,name,value,months in [(1,'primebank','পরীক্ষা প্রাইম',6,60),(2,'nccbank','পরীক্ষা এনসিসি',5,60),(3,'bracbank','পরীক্ষা ব্র্যাক',4,60),(4,'sbacbank','পরীক্ষা সাউথবাংলা',9,12)]:
            db.add(Institution(id=id,slug=slug,name_bn=name,name_en='Synthetic '+slug,type='bank',islamic=False,licensed=True,listed=True,coverage='full'))
            db.add(ServiceOffer(offer_id='synthetic-dps-'+str(id),institution_id=id,category='deposit',product='Synthetic monthly plan',product_type='dps',tenor_months=months,tenor_min_months=months,tenor_max_months=months,tenor_options=[months],attribute='rate',value_num=value,value_text=str(value),unit='pct_year',condition='Synthetic terms',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/synthetic',page=1,quote='Synthetic Initial Amount 10,000 example; monthly deposit' if id==2 else 'Synthetic rate example',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='synthetic-fixture',checked_on=date(2026,10,1)))
        db.commit()
        with patch('ilma_api.dps_compare.get_institution_report_card',side_effect=lambda session,id:{'status':{'code':'no_data' if id==4 else 'strong'}}):yield db
    engine.dispose()

@pytest.mark.parametrize('question',QUESTIONS)
def test_only_best_dps_family_routes_global_five_year_comparison(question):
    result=resolve(question,Conversation(institution_id=19,product='card',tenor=12,network='Visa',tier='Gold'),[])
    assert result.intent=='compare' and result.product=='dps' and result.tenor==60
    assert result.bank_id is None and result.network is result.tier is None

@pytest.mark.parametrize('question',['কোন ব্যাংক সবথেকে ভালো','এফডিআর কোথায় ভালো','প্রাইম ব্যাংকের ডিপিএস রেট কত','ডিপিএস সবচেয়ে নিরাপদ কোন ব্যাংকে','তিন বছরের ডিপিএস কোথায় ভালো'])
def test_other_questions_keep_existing_routing(question):
    assert not is_best_dps_question(question)

def test_selects_strong_rates_and_flags_higher_different_term_without_fabricating_five_years(dps_db):
    facts=build(dps_db)
    assert [r['bank_id'] for r in facts['top']]==[1,2,3]
    assert facts['flagged'][0]['bank_id']==4 and facts['flagged'][0]['comparison_months']==12
    assert not facts['flagged'][0]['matches_five_years']
    assert 'maturity_estimate_bdt' not in facts['flagged'][0]
    assert facts['conditions'][0]['initial_example_bdt']==10000
    assert validate(template(facts),facts) is None
    assert len(pronounce(template(facts),'bn').split())<60

def test_month_end_formula_zero_rate_and_compounding():
    assert maturity(0)==60000
    assert maturity(6)>60000 and maturity(7)>maturity(6)
    assert maturity(12,monthly=1000,months=2)==2010

def test_numbers_absent_from_sent_fact_list_are_rejected(dps_db):
    facts=build(dps_db)
    answer=template(facts).replace(QUESTION,'3 '+QUESTION)
    assert validate(answer,facts)=='unknown_number'

@pytest.mark.parametrize('kind',['unknown_number','unknown_bank','swap_rates','swap_maturity','drop_flag','drop_caveat','ending'])
def test_rejects_inventions_swapped_facts_and_omissions(dps_db,kind):
    facts=build(dps_db);answer=template(facts)
    if kind=='unknown_number':answer=answer.replace(str(facts['top'][0]['maturity_estimate_bdt']),'999999')
    elif kind=='unknown_bank':answer=answer.replace('প্রাইম','অজানা ব্যাংক')
    elif kind=='swap_rates':answer=answer.replace('প্রাইম 6%','প্রাইম 5%')
    elif kind=='swap_maturity':answer=answer.replace(str(facts['top'][0]['maturity_estimate_bdt']),str(facts['top'][1]['maturity_estimate_bdt']))
    elif kind=='drop_flag':answer=answer.replace('অযাচাইকৃত','ভালো')
    elif kind=='drop_caveat':answer=answer.replace('ধরা হয়নি','ধরা হয়েছে')
    else:answer=answer.replace(QUESTION,'কোন ব্যাংক?')
    assert validate(answer,facts)

def test_meta_receives_only_speakable_facts_and_bad_numbers_fall_back(dps_db):
    async def scenario():
        facts=build(dps_db);calls=[]
        def provider(request):
            body=json.loads(request.content);calls.append(body)
            payload=json.loads(body['messages'][1]['content'])
            assert isinstance(payload,list) and payload[-1]['text_bn']==QUESTION
            assert all(set(row)=={'id','text_bn'} for row in payload)
            answer=template(facts).replace(str(facts['top'][0]['maturity_estimate_bdt']),'999999')
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'answer':answer})}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            answer,reason=await compose(facts,[],client)
        assert answer==template(facts) and reason=='unknown_number' and len(calls)==1
    asyncio.run(scenario())

def test_insufficient_bank_data_stops_before_model_and_never_asks_which_bank(dps_db):
    dps_db.query(ServiceOffer).filter(ServiceOffer.institution_id>2).delete();dps_db.commit()
    async def scenario():
        with patch('ilma_api.dps_compare.compose',AsyncMock()) as model:
            result=await run_agent_turn(QUESTIONS[0],VoiceContext(agent=True,ui_lang='bn',speak=False),[],dps_db)
        model.assert_not_awaited()
        assert result['intent']=='compare' and not result['dps_data_ready']
        assert 'কোন ব্যাংক' not in result['speech']
    asyncio.run(scenario())

def test_default_text_pipeline_uses_comparison_without_stt_change(dps_db):
    from ilma_api.voice_pipeline import run_pipeline
    async def scenario():
        facts=build(dps_db)
        with patch('ilma_api.dps_compare.compose',AsyncMock(return_value=(template(facts),None))),patch('ilma_api.voice_pipeline.transcribe',AsyncMock()) as stt:
            frames=[frame async for frame in run_pipeline(None,QUESTIONS[0],'',VoiceContext(agent=False,ui_lang='bn',speak=False),[],dps_db,mode='text')]
        stt.assert_not_awaited()
        result=next(json.loads(frame.split('data: ',1)[1]) for frame in frames if frame.startswith('event: result'))
        assert result['intent']=='compare' and result['dps_data_ready']
        assert result['speech'].endswith(QUESTION) and len(result['speech_tts'].split())<60
    asyncio.run(scenario())
