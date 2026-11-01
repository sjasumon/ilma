"""Multi-turn failures reproduced using tiny synthetic SQLite facts, never shared data."""
import asyncio
from unittest.mock import patch,AsyncMock
from test_voice_agent import db,BANKS
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_resolver import resolve
from ilma_api.human_turn import run


def test_pension_two_banks_comparison_then_bangla_definition(db):
    async def exercise():
        c=Conversation(language='en')
        texts=[('Where I can save pension money?','en'),('Tell me about EBL and BRAC Bank','en'),('Compare BRAC Bank and EBL','en'),('ইন্টারেস্ট আর প্রফিটের মধ্যে পার্থক্য কী?','bn')]
        results=[]
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=AssertionError('These resolved turns require no model'))):
            for text,language in texts:
                result=await run(text,VoiceContext(agent=True,ui_lang=language,speak=False,conversation=c),BANKS,db,device_hash='synthetic-sequence')
                results.append(result);c=Conversation.model_validate(result['conversation'])
        assert results[0]['intent']=='advice_request'
        for result in results[1:3]:
            assert result['intent']=='compare'
            assert 'BRAC' in result['speech'] and 'EBL' in result['speech']
            assert 'FDR' not in result['speech']
            assert result['conversation']['product'] is None
        last=results[-1]
        assert last['intent']=='explain_term' and last['language']=='bn'
        assert 'সুদ' in last['speech'] and 'মুনাফা' in last['speech']
        assert not any(f.get('kind')=='figure' for f in last['facts'] if f['fact_id'] in last['speech_fact_ids'])
        assert last['conversation']['misses']==0 and last['offer_typing'] is False
    asyncio.run(exercise())


def test_generic_comparison_is_not_implicitly_a_rate_question():
    c=Conversation(language='en')
    r=resolve('tell me about EBL and BRAC Bank',c,BANKS)
    assert r.intent=='compare' and r.compare_bank_ids==[2,1] and r.product is None
    c=Conversation(institution_id=2,compare_bank_ids=[1],last_intent='compare')
    r=resolve('compare FDR rates',c,BANKS)
    assert r.product=='fdr' and r.compare_bank_ids==[2,1]


def test_general_definition_ignores_an_earlier_bank_product():
    from ilma_api.human_facts import term_facts
    c=Conversation(institution_id=1,product='fdr',last_intent='compare')
    for text in ['সুদ আর মুনাফার পার্থক্য কী?','ইন্টারেস্ট আর প্রফিটের মধ্যে তফাত কী?','What is the difference between interest and profit?']:
        r=resolve(text,c,BANKS)
        assert r.intent=='explain_term' and r.product is None and r.requested_metric is None
        assert [f['fact_id'] for f in term_facts(text)]==['term:interest_profit_difference']
    assert resolve('সুদের আয় আর নিট মুনাফার পার্থক্য কী?',c,BANKS).requested_metric=='net_profit'


def bangla_pair_banks():
    return [
        {**BANKS[0],'slug':'dutchbangl','name_bn':'পরীক্ষা ডাচ বাংলা ব্যাংক','name_en':'Dutch Test Bank','aliases':['ডাচ বাংলা ব্যাংক']},
        {**BANKS[1],'name_bn':'পরীক্ষা ইস্টার্ন ব্যাংক','aliases':['ইস্টার্ন ব্যাংক']},
        {**BANKS[0],'id':3,'slug':'sbacbank','name_bn':'পরীক্ষা সাউথ বাংলা ব্যাংক','name_en':'South Test Bank','aliases':['সাউথ বাংলা ব্যাংক']},
    ]


def test_bangla_pair_with_two_imperfect_names_preserves_and_not_or():
    banks=bangla_pair_banks()
    for text in ['আমাকে ডাস বাংলা ব্যাংক এবং স্টার্ন ব্যাংক সম্বন্ধে বলবেন','ডাচ বাংলা ব্যাংক এবং স্টার্ন ব্যাংক সম্বন্ধে বলবেন']:
        r=resolve(text,Conversation(language='bn'),banks)
        assert r.confirm_pair and r.confirm_ids==[1,2] and r.compare_bank_ids==[1,2]
    r=resolve('ডাচ বাংলা ব্যাংক এবং ইস্টার্ন ব্যাংক সম্বন্ধে বলবেন',Conversation(language='bn'),banks)
    assert r.intent=='compare' and not r.confirm_ids and not r.confirm_pair
    alternative=resolve('ডাস বাংলা ব্যাংক নাকি স্টার্ন ব্যাংক',Conversation(language='bn'),banks)
    assert not alternative.confirm_pair
    assert resolve('ডাচ বাংলা ব্যাংক এবং ইস্টার্ন ব্যাংক',Conversation(language='bn'),banks).intent=='compare'


def test_confirming_bangla_pair_keeps_both_banks(db):
    from ilma_api.db import Institution
    banks=bangla_pair_banks()
    row=db.get(Institution,1);row.name_bn=banks[0]['name_bn'];row.name_en=banks[0]['name_en'];db.commit()
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=AssertionError('No model during pair confirmation'))):
            first=await run('আমাকে ডাস বাংলা ব্যাংক এবং স্টার্ন ব্যাংক সম্বন্ধে বলবেন',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(language='bn')),banks,db,device_hash='synthetic-pair')
            assert ' এবং ' in first['speech'] and ' নাকি ' not in first['speech']
            assert first['expects_reply'] is True
            assert [o['value'] for o in first['next']['options']]==['confirm_bank','reject_bank']
            assert first['conversation']['institution_id'] is None
            c=Conversation.model_validate(first['conversation'])
            result=await run('হ্যাঁ',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=c),banks,db,device_hash='synthetic-pair')
            assert result['intent']=='compare' and result['conversation']['product'] is None
            used=[f for f in result['facts'] if f['fact_id'] in result['speech_fact_ids']]
            assert {f['institution_id'] for f in used}=={1,2}
    asyncio.run(scenario())


def test_rejecting_bangla_pair_does_not_select_first_bank(db):
    banks=bangla_pair_banks()
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=AssertionError('No guessing on rejection'))):
            result=await run('ডাস বাংলা ব্যাংক এবং স্টার্ন ব্যাংক সম্বন্ধে বলবেন',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(language='bn')),banks,db,device_hash='synthetic-no-pair')
            c=Conversation.model_validate(result['conversation'])
            result=await run('না',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=c),banks,db,device_hash='synthetic-no-pair')
            assert result['intent']=='unclear' and result['conversation']['institution_id'] is None
            assert not result['speech_fact_ids']
    asyncio.run(scenario())


def test_and_inside_a_full_bank_name_is_not_a_two_bank_request():
    banks=[{**BANKS[0],'id':3,'slug':'nbl','name_en':'National Test Bank','aliases':['National']},{**BANKS[1],'id':4,'slug':'nccbank','name_en':'National Credit and Commerce Bank','aliases':['Commerce Bank']}]
    r=resolve('Tell me about National Credit and Commerce Bank',Conversation(language='en'),banks)
    assert r.bank_id==4 and not r.confirm_pair and not r.compare_bank_ids
