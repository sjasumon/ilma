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
    for variant in range(3):
        answer=template(facts,variant)
        assert validate(answer,facts) is None and len(pronounce(answer,'bn').split())<=60
        assert 'প্রাইম ব্যাংক' in answer and 'কত টাকা' not in answer and '10000' not in answer

def test_equal_rates_are_spoken_together_with_full_names(dps_db):
    dps_db.add(Institution(id=5,slug='citybank',name_bn='পরীক্ষা সিটি',name_en='Synthetic city',type='bank',islamic=False,licensed=True,listed=True,coverage='full'))
    dps_db.add(ServiceOffer(offer_id='synthetic-dps-5',institution_id=5,category='deposit',product='Synthetic monthly plan',product_type='dps',tenor_months=60,tenor_min_months=60,tenor_max_months=60,tenor_options=[60],attribute='rate',value_num=4,value_text='4',unit='pct_year',condition='Synthetic terms',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/synthetic',page=1,quote='Synthetic rate example',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='synthetic-fixture',checked_on=date(2026,10,1)))
    dps_db.commit()
    facts=build(dps_db);answer=template(facts)
    assert 'ব্র্যাক ও সিটি ব্যাংক, 4%' in answer and validate(answer,facts) is None

def test_model_wording_with_status_before_condition_is_accepted(dps_db):
    facts=build(dps_db)
    answer=template(facts).replace('এদের সবার অবস্থা ভালো।','তিনটি ব্যাংকই ভালো অবস্থায় আছে।')
    assert validate(answer,facts) is None

def test_model_wording_must_keep_terms_and_sentences(dps_db):
    facts=build(dps_db);answer=template(facts)
    assert validate(answer.replace('5 বছরের ডিপিএসে ',''),facts)=='missing_term'
    assert validate(answer.replace('1 বছরের ডিপিএসে ',''),facts)=='missing_flagged_term'
    assert validate(answer.replace('।',','),facts)=='run_on_sentence'

def test_month_end_formula_zero_rate_and_compounding():
    assert maturity(0)==60000
    assert maturity(6)>60000 and maturity(7)>maturity(6)
    assert maturity(12,monthly=1000,months=2)==2010

def test_numbers_absent_from_sent_fact_list_are_rejected(dps_db):
    facts=build(dps_db)
    answer=template(facts).replace(QUESTION,'3 '+QUESTION)
    assert validate(answer,facts)=='unknown_number'

@pytest.mark.parametrize('kind',['unknown_number','unknown_bank','swap_rates','amount','drop_flag','advice','ending'])
def test_rejects_inventions_swapped_facts_and_omissions(dps_db,kind):
    facts=build(dps_db);answer=template(facts)
    if kind=='unknown_number':answer=answer.replace('6%','7%')
    elif kind=='unknown_bank':answer=answer.replace('প্রাইম ব্যাংক','অজানা ব্যাংক')
    elif kind=='swap_rates':answer=answer.replace('প্রাইম ব্যাংক, 6%','প্রাইম ব্যাংক, 5%')
    elif kind=='amount':answer=answer.replace(QUESTION,'আপনি মাসে কত টাকা রাখতে চান?')
    elif kind=='drop_flag':answer=answer.replace('তবে ওই ব্যাংকের অবস্থা যাচাইয়ের তথ্য আমাদের কাছে কম','অবস্থা ভালো')
    elif kind=='advice':answer=answer.replace('সুদের হিসাবে বললে,','সবচেয়ে ভালো হলো,')
    else:answer=answer.replace(QUESTION,'আর কিছু না।')
    assert answer!=template(facts) and validate(answer,facts)

def test_meta_receives_only_speakable_facts_and_bad_numbers_fall_back(dps_db):
    async def scenario():
        facts=build(dps_db);calls=[]
        def provider(request):
            body=json.loads(request.content);calls.append(body)
            payload=json.loads(body['messages'][1]['content'])
            assert isinstance(payload,list) and payload[0]['id']=='scope'
            assert all(set(row)=={'id','text_bn'} for row in payload)
            assert 'কত টাকা' not in body['messages'][1]['content'] and '10000' not in body['messages'][1]['content']
            answer=template(facts).replace('6%','7%')
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
        assert result['speech'].endswith(QUESTION) and len(result['speech_tts'].split())<=60
        assert any('উদাহরণ' in fact['text_bn'] for fact in result['facts'])
    asyncio.run(scenario())

@pytest.mark.parametrize('question',['কোন ব্যাংকে এফডিআরের সুদ সবচেয়ে বেশি?','এফডিআর কোথায় ভালো','Which bank has the best FDR?','সবচেয়ে ভালো এফডিআর কোন ব্যাংকের'])
def test_best_fdr_family_routes_one_year_comparison(question):
    from ilma_api.human_resolver import best_rate_product
    result=resolve(question,Conversation(institution_id=19,product='card'),[])
    assert best_rate_product(question)=='fdr' and result.intent=='compare' and result.product=='fdr' and result.tenor==12 and result.bank_id is None

@pytest.mark.parametrize('question',['প্রাইম ব্যাংকের এফডিআর রেট কত','এফডিআর কী?','কোন ব্যাংকের ডিপিএস সবচেয়ে ভালো?'])
def test_other_questions_are_not_best_fdr(question):
    from ilma_api.human_resolver import is_best_fdr_question
    assert not is_best_fdr_question(question)

def test_fdr_comparison_uses_one_year_rates_without_an_illustration(dps_db):
    for id,value,months in [(1,5,12),(2,4.5,12),(3,4,12),(4,9,6)]:
        dps_db.add(ServiceOffer(offer_id='synthetic-fdr-'+str(id),institution_id=id,category='deposit',product='Synthetic fixed plan',product_type='fdr',tenor_months=months,tenor_min_months=months,tenor_max_months=months,tenor_options=[months],attribute='rate',value_num=value,value_text=str(value),unit='pct_year',condition='Synthetic term',basis='conventional',doc_date=date(2026,10,1),stale=False,source_url='https://example.test/fdr',page=1,quote='Synthetic fixed rate',column_header='',variant='main',hidden=False,hidden_reason='',checked_by='synthetic-fixture',checked_on=date(2026,10,1)))
    dps_db.commit()
    facts=build(dps_db,'fdr')
    assert facts['ready'] and [r['bank_id'] for r in facts['top']]==[1,2,3] and facts['years']==1
    assert all('maturity_estimate_bdt' not in r for r in facts['top']) and not facts['conditions']
    assert facts['flagged'][0]['bank_id']==4 and facts['flagged'][0]['comparison_months']==6
    for variant in range(3):
        answer=template(facts,variant)
        assert validate(answer,facts) is None and 'এফডিআর' in answer and 'ডিপিএস' not in answer and '6 মাসের এফডিআরে' in answer

def test_english_best_rate_question_gets_an_english_answer(dps_db):
    async def scenario():
        with patch('ilma_api.dps_compare.compose',AsyncMock()) as model:
            result=await run_agent_turn('Which bank has the best DPS?',VoiceContext(agent=True,ui_lang='en',speak=False),[],dps_db)
        model.assert_not_awaited()
        return result
    result=asyncio.run(scenario())
    assert result['language']=='en' and result['speech'].startswith('By interest rate, for a 5-year DPS')
    assert not any('ঀ'<=ch<='৿' for ch in result['speech']) and result['speech'].endswith('?')

def test_english_insured_question_is_a_protection_question():
    result=resolve('How much of my deposit is insured at this bank?',Conversation(institution_id=19,language='en'),[])
    assert result.direct_protection


def test_three_rates_and_two_flagged_banks_fit_the_fixed_answer():
    from ilma_api.dps_compare import template,validate
    row=lambda id,name,value,status='strong',**extra:dict(bank_id=id,offer_id='o'+str(id),name_bn=name,rate_percent=value,status=status,**extra)
    top=[row(1,'প্রথম পরীক্ষা ব্যাংক','8'),row(2,'দ্বিতীয় পরীক্ষা ব্যাংক','7.75'),row(3,'তৃতীয় পরীক্ষা ব্যাংক','7.5')]
    flagged=[row(4,'চতুর্থ পরীক্ষা ব্যাংক','9.25','no_data',comparison_months=12,matches_five_years=True),row(5,'পঞ্চম পরীক্ষা ব্যাংক','8.25','watch',comparison_months=12,matches_five_years=True)]
    data=dict(top=top,cutoff_ties=[],flagged=flagged,inventory=top+flagged,years=1,word='এফডিআর',product='fdr')
    assert all(validate(template(data,variant),data) is None for variant in range(3))


def test_fixed_bangla_answer_keeps_warnings_and_passes_the_checks():
    from ilma_api.dps_compare import fixed_bn
    row=lambda id,name,value,status='strong',**extra:dict(bank_id=id,offer_id='o'+str(id),name_bn=name,rate_percent=value,status=status,**extra)
    top=[row(1,'প্রথম ব্যাংক','8.25'),row(2,'দ্বিতীয় ব্যাংক','8'),row(3,'তৃতীয় ব্যাংক','8')]
    same=row(4,'চতুর্থ ব্যাংক','9.25','no_data',comparison_months=12,matches_five_years=True)
    other=row(4,'চতুর্থ ব্যাংক','10','no_data',comparison_months=12,matches_five_years=False)
    for flagged in (same,other):
        data=dict(top=top,cutoff_ties=[],flagged=[flagged],inventory=top+[flagged],years=1,word='এফডিআর',product='fdr')
        text=fixed_bn(data)
        assert validate(text,data) is None
        assert text.index('এই ব্যাংকগুলো ভালো অবস্থায় আছে।')<text.index('চতুর্থ') and 'তবে ওই ব্যাংকের' in text
