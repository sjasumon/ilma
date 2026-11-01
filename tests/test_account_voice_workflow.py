"""Tiny synthetic account records verify product correction and source-bound choices."""
import asyncio
from unittest.mock import patch,AsyncMock
import pytest
from test_voice_agent import db,BANKS
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_resolver import resolve
from ilma_api.human_turn import run
from ilma_api.account_voice import answer

@pytest.mark.parametrize('text',['আমাকে ব্র্যাক ব্যাংকের অ্যাকাউন্টস ডিটেইলস বলবেন','ব্র্যাক ব্যাংকের একাউন্টের তথ্য বলুন','Tell me about BRAC Bank accounts','BRAC Bank account details'])
def test_account_topic_clears_dps_and_term(text):
    r=resolve(text,Conversation(institution_id=1,product='dps',tenor=12),BANKS)
    assert r.account_overview and r.product=='account_fee' and r.tenor is None
    assert r.intent=='services_list' and r.bank_id==1


def test_accounts_clarification_then_each_scope_does_not_reuse_dps(db):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=AssertionError('No guess for explicit account topic'))):
            first=await run('ব্র্যাক ব্যাংকের অ্যাকাউন্টস ডিটেইলস বলবেন',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(institution_id=1,product='dps',tenor=12,language='bn')),BANKS,db,device_hash='synthetic-accounts')
            assert 'ডিপিএস' not in first['speech']
            assert first['conversation']['product']=='account_fee'
            assert [o['value'] for o in first['next']['options']]==['savings','account_fees','debit']
            assert 'হিসাবের তথ্য' in first['topic']
            for choice in ['savings','account_fees','debit']:
                c=Conversation.model_validate(first['conversation'])
                result=await run('',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=c),BANKS,db,choice=choice,device_hash='synthetic-account-'+choice)
                assert 'ডিপিএস' not in result['speech']
                assert result['conversation']['product']==('savings' if choice=='savings' else 'account_fee')
                assert result['topic']
    asyncio.run(scenario())


def test_debit_is_not_credit_and_private_balance_does_not_become_product_query():
    c=Conversation(institution_id=1,product='dps')
    r=resolve('ব্র্যাকের ডেবিট কার্ডের ফি',c,BANKS)
    assert r.product=='account_fee' and r.requested_field=='debit'
    assert not resolve('my account balance',c,BANKS).account_overview
    assert not resolve('মূলধনের হিসাব বলুন',c,BANKS).account_overview


def test_fee_voice_uses_synthetic_source_and_fixed_example_only():
    row=dict(offer_id='synthetic-maint',unit='bdt_half_year',value_num=100,vat_percent=None,vat_included=False,rate_is_maximum=False,product='Sample account',source_url='https://example.test/fees',quote='Synthetic fee',page=1,doc_date='2026-10-01',condition='Handwritten synthetic condition',periods_per_year=2)
    bank=dict(id=1,name_bn='নমুনা ব্যাংক',name_en='Sample Bank',debit_main=None,debit_replacement=None,sms=None)
    with patch('ilma_api.account_voice.banks',return_value=[bank]),patch('ilma_api.account_voice.calculate',return_value={'maintenance':row}) as calc:
        text,facts=answer(None,1,False,'en')
    assert calc.call_args.args[1]==100000
    assert 'fixed 1-lakh-taka example' in text and '100 taka per half year' in text
    assert [f['fact_id'] for f in facts]==['synthetic-maint']
    assert facts[0]['source']['quote']=='Synthetic fee'

@pytest.mark.parametrize('text,product,field',[('সুদ','savings',None),('ফি','account_fee','account_fees'),('ডেবিট','account_fee','debit')])
def test_short_account_replies_keep_bank_and_choose_correct_scope(text,product,field):
    r=resolve(text,Conversation(institution_id=1,product='account_fee'),BANKS)
    assert r.product==product and r.bank_id==1
    if field:assert r.requested_field==field


def test_account_context_does_not_override_an_explicit_deposit_or_insurance_topic():
    c=Conversation(institution_id=1,product='account_fee')
    assert resolve('ফিক্সড ডিপোজিটের সুদ কত',c,BANKS).product=='fdr'
    assert not resolve('আমানত বীমার হিসাব',c,BANKS).account_overview
