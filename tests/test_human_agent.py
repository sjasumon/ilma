"""Handwritten synthetic checks for contextual turns and factual speech."""
import asyncio,json
from unittest.mock import AsyncMock,patch
import httpx
import pytest
from test_voice_agent import db,BANKS
from ilma_api import settings
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_agent import run,controls
from ilma_api.human_stream import Draft,Header,generate
from ilma_api.human_checker import check
from ilma_api.human_memory import redact_user,token,verified_id
from ilma_api.human_facts import comparison_facts,fact_pack
from ilma_api.db import AppConversation,AppRateCounter

def answer(intent='bank_figures',reply='The published problem-loan ratio is 2 percent.',ids=('test-npl-1',)):
    a=controls(intent,Conversation(institution_id=1,language='en'),reply)
    return a.model_copy(update={'used_fact_ids':list(ids),'sentence_fact_ids':[list(ids)]})

def test_checker_rejects_number_status_advice_repeat_and_unknown_citation(db):
    facts=fact_pack(db,1)['facts'];a=answer()
    assert check(a,facts,BANKS)==[]
    assert 'unsupported_number' in check(a.model_copy(update={'reply':'The ratio is 99 percent.'}),facts,BANKS)
    assert 'advice' in check(a.model_copy(update={'reply':'You should put your money here.'}),facts,BANKS)
    assert 'repeated_fact' in check(a,facts,BANKS,['test-npl-1'])
    assert check(a.model_copy(update={'used_fact_ids':['invented']}),facts,BANKS)==['unknown_fact_id']

def test_tenor_cannot_become_interest_and_bank_rates_cannot_be_swapped(db):
    facts=comparison_facts(db,1,'fdr',12)
    a=answer('compare','BRAC Test Bank quotes 9.1 percent.',('test-fdr-1','test-fdr-2'))
    assert 'unsupported_percentage' in check(a,facts,BANKS)
    a=answer('service_detail','BRAC Test Bank quotes 12 percent.',('test-fdr-1',))
    assert 'unsupported_percentage' in check(a,facts,BANKS)

def test_bangla_term_word_is_not_the_month_may(db):
    facts=comparison_facts(db,1,'fdr',12)
    a=answer('service_detail','১২ মাস মেয়াদে হার ৮.৫ শতাংশ।',('test-fdr-1',)).model_copy(update={'language':'bn'})
    assert 'unsupported_month' not in check(a,facts,BANKS)
    a=a.model_copy(update={'reply':'মে মাসের হার ৮.৫ শতাংশ।'})
    assert 'unsupported_month' in check(a,facts,BANKS)

def test_decimal_word_and_precise_rounding_are_checked_as_one_claim():
    from ilma_api.human_checker import numeric_claims,percent_support
    from decimal import Decimal
    assert numeric_claims('৯৩২ দশমিক ৮৯ কোটি')==[Decimal('932.89')]
    assert numeric_claims('সরকারিভাবে নিশ্চিত নয়')==[]
    assert numeric_claims('নয় শতাংশ')==[Decimal(9)]
    assert numeric_claims('মাইনাস ৫.৫ শতাংশ')==[Decimal('-5.5')]
    allowed=percent_support([{'kind':'peer','values':{'metric':'profit_change','value':20.069296,'median':30.265326}}])
    assert Decimal('20.07') in allowed and Decimal('20.06') not in allowed

def test_capital_ratio_cannot_be_recast_as_money_per_deposit():
    fact={'fact_id':'capital-test','kind':'figure','institution_id':1,'text_en':'Capital ratio 15 percent','text_bn':'মূলধন ১৫ শতাংশ','source':{},'values':{'metric':'crar','value':.15}}
    a=answer('bank_figures','There are 15 taka of capital per 100 taka.',('capital-test',))
    assert 'capital_denominator' in check(a,[fact],BANKS)
    a=a.model_copy(update={'reply':'Capital is 15 percent of risk-weighted assets.'})
    assert 'capital_denominator' not in check(a,[fact],BANKS)

def test_rank_direction_distinguishes_highest_from_lowest():
    fact={'fact_id':'peer-test','kind':'peer','institution_id':1,'text_en':'Problem loans 2 percent','text_bn':'খেলাপি ঋণ ২ শতাংশ','source':{},'values':{'metric':'npl_ratio','value':2,'median':3,'rank':1,'rank_low':1,'rank_high':3}}
    assert 'wrong_rank' in check(answer('bank_figures','This is the highest problem-loan ratio.',('peer-test',)),[fact],BANKS)
    assert 'wrong_rank' not in check(answer('bank_figures','This is the lowest problem-loan ratio.',('peer-test',)),[fact],BANKS)


def test_same_basis_annual_profit_change_uses_sourced_inputs(db):
    from ilma_api.human_facts import annual_profit_change
    from ilma_api.db import Fact
    from datetime import date
    for id,year,value in [('now',2025,300),('before',2024,200)]:
        db.add(Fact(fact_id='synthetic-profit-'+id,institution_id=1,metric='net_profit',value=value,unit='bdt',period=str(year),period_end=date(year,12,31),basis='solo',source_id='synthetic-source',quote='Synthetic profit '+str(value),checked_by='test-fixture',checked_on=date(2026,10,1)))
    db.flush();fact=annual_profit_change(db,1)
    assert fact['values']['value']==50 and len(fact['source']['inputs'])==2



def test_network_failure_does_not_count_as_user_miss(db):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(return_value=Draft(error='timeout'))):
            result=await run('Tell me the past events',VoiceContext(agent=True,ui_lang='en',conversation=Conversation(institution_id=1,language='en',misses=1)),BANKS,db,device_hash='synthetic')
        assert result['conversation']['institution_id']==1 and result['intent']=='bank_history'
        assert result['conversation']['misses']==1
    asyncio.run(scenario())

def test_quota_precedes_model(db):
    async def scenario():
        model=AsyncMock()
        with patch('ilma_api.human_turn.generate',model),patch('ilma_api.voice_pipeline.consume_question',side_effect=RuntimeError('quota')):
            with pytest.raises(RuntimeError,match='quota'):
                await run('Any past events?',VoiceContext(agent=True,ui_lang='en',conversation=Conversation(institution_id=1,language='en')),BANKS,db)
        model.assert_not_awaited()
    asyncio.run(scenario())


def test_memory_redacts_identifiers_and_amounts_and_signatures():
    safe=redact_user('আমার ৫ লাখ টাকা আছে account 123456789 FDR 12 months')
    assert '৫ লাখ' not in safe and '123456789' not in safe and '12 months' in safe
    value=token('a'*32)
    assert verified_id(value)=='a'*32 and verified_id(value[:-1]+('0' if value[-1]!='0' else '1')) is None


def test_comparison_retains_bank_and_ignores_card_filters(db):
    rows=comparison_facts(db,1,'fdr',12,'conventional',network='Visa',tier='Gold')
    assert {r['institution_id'] for r in rows}=={1,2}


def test_someone_else_asking_for_a_pin_gets_the_scam_warning():
    from ilma_api.human_answers import refusal
    assert 'scam' in refusal('A man from the bank called asking for my PIN',False)[0]
    assert 'প্রতারণা' in refusal('ব্যাংক থেকে ফোন করে পিন চাইছে',True)[0]
    assert 'scam' not in refusal('My PIN is 1234, can you check my balance?',False)[0]

def test_cleaned_transcript_still_finds_the_question_that_was_said():
    from ilma_api.voice_text import clean_transcript
    from ilma_api.reviewed_answers import question_key
    said='ঘরে বসে অল্প অল্প করে জমাতে চাই'
    assert question_key(clean_transcript(said))!=question_key(said)
    assert VoiceContext(raw_text=said).raw_text==said

def test_mishearings_name_brac_only_beside_the_word_bank():
    from ilma_api.human_resolver import resolve
    fresh=Conversation(language='en')
    for said in ('Tell me about Black Bank','Brack Bank FDR','ব্ল্যাক ব্যাংক সম্পর্কে বলুন','ব্রাক ব্যাংক সম্পর্কে বলুন'):
        assert resolve(said,fresh,BANKS).bank_id==1,said
    assert resolve('What is black money?',fresh,BANKS).bank_id is None

def test_unrelated_short_names_do_not_look_like_a_bank():
    from ilma_api.voice_text import different_start
    assert different_start('sbac','black') and different_start('brac','zebra')
    assert not different_start('city','sitty') and not different_start('brac','bragg')


def test_account_fee_facts_can_be_saved_in_conversation_memory(monkeypatch):
    from datetime import date
    from ilma_api import account_voice
    row=dict(offer_id='synthetic',value_num=300,unit='bdt_card',vat_included=False,vat_percent=15,rate_is_maximum=False,doc_date=date(2026,1,1),source_url='https://example.test',quote='Synthetic',source_title='Synthetic',condition='Synthetic',page=1,product='Synthetic card')
    monkeypatch.setattr(account_voice,'banks',lambda db:[dict(id=1,name_bn='পরীক্ষা ব্যাংক',name_en='Test Bank',debit_main=row,debit_replacement=None)])
    _,facts=account_voice.answer(None,1,True,'en')
    json.dumps(facts)


def test_redaction_keeps_ordinary_account_words_but_hides_numbers():
    from ilma_api.human_memory import redact_user
    for said in ('can you tell me uh Black Bank account details','BRAC Bank account fees','What is the PIN for a debit card?'):
        assert redact_user(said)==said,said
    for said,secret in (('my account 12345678','12345678'),('account no: 0123-4567','0123-4567'),('my pin is 1234','1234'),('PIN: 4321','4321'),('password hunter2','hunter2'),('otp 556677','556677'),('আমার পিন ১২৩৪','১২৩৪'),('পিন হলো ৯৮৭৬','৯৮৭৬'),('অ্যাকাউন্ট নম্বর ১২৩৪৫','১২৩৪৫')):
        out=redact_user(said)
        assert secret not in out and '[identifier omitted]' in out,(said,out)


def test_saved_answer_keys_still_use_the_frozen_filter():
    from ilma_api.reviewed_answers import question_key
    import hashlib
    from ilma_api.voice_text import normalize_alias
    said='Can you tell me BRAC Bank account details?'
    assert question_key(said)==hashlib.sha256(normalize_alias('Can you tell me BRAC Bank [identifier omitted]').encode()).hexdigest()
