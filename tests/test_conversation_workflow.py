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
