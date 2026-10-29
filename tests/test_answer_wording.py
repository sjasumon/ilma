"""Handwritten synthetic facts only; no source export or real-bank incident fixture."""
import asyncio,re
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock,patch
import pytest
from test_voice_agent import db,BANKS,context,conv
from ilma_api.db import Fact,Rating,InsuranceRule,ServiceOffer,BankIncident,IncidentSource
from ilma_api.voice_agent import Conversation,run_agent_turn,bank_summary,bank_reasons,bank_figures,bank_history,service_detail
from ilma_api.voice_text import match_candidates
from ilma_api.answer_wording import compose,rounded

@pytest.fixture
def wording_db(db):
    # Deliberately synthetic values, not copied bank records.
    db.add(Fact(fact_id='synthetic-capital',institution_id=1,metric='crar',value=.1807,unit='ratio',period='FY2025',period_end=date(2025,12,31),basis='solo',source_id='synthetic-source',quote='Synthetic capital ratio',checked_by='test-fixture',checked_on=date(2026,10,1)))
    db.add(Fact(fact_id='synthetic-profit',institution_id=1,metric='net_profit',value=Decimal('1234000000'),unit='bdt',period='FY2025',period_end=date(2025,12,31),basis='solo',source_id='synthetic-source',quote='Synthetic profit',checked_by='test-fixture',checked_on=date(2026,10,1)))
    db.add(Rating(fact_id='synthetic-rating',institution_id=1,agency='CRAB',long_term='AAA',outlook='stable',rated_on=date(2026,6,1),valid_to=date(2027,6,1),source_id='synthetic-source',quote='Synthetic rating',checked_by='test-fixture',checked_on=date(2026,10,1)))
    rule=db.get(InsuranceRule,'bank');rule.text_en='Eligible deposits up to the stated limit per depositor per member bank, combining accounts. Conditions and exclusions apply.'
    rule.text_bn='পরীক্ষার শর্তযুক্ত আমানত সুরক্ষা।';rule.limit_bdt=123000
    incident=BankIncident(incident_id='synthetic-history',institution_id=1,kind='audit_warning',title_bn='একটি প্রক্রিয়াগত ত্রুটির অভিযোগ',title_en='an allegation of a procedural error',status='alleged',official=False,status_effect=False,first_reported_on=date(2020,4,1),last_update_on=date(2020,4,1),checked_by='test-fixture',checked_on=date(2026,10,1))
    incident.sources.append(IncidentSource(source_id='synthetic-source',quote='Synthetic report only',language='en'));db.add(incident)
    db.commit();return db


def ask(db,text,c=None,choice=None):
    with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('Scripted questions need no model'))):
        return asyncio.run(run_agent_turn(text,context(c),BANKS,db,match_candidates(text,BANKS) if text else [],choice))

@pytest.mark.parametrize('bn',[True,False])
def test_contextual_capital_wording_names_the_ratio_denominator(wording_db,bn):
    from ilma_api.answer_wording import brief_fact
    item={'fact_id':'synthetic-capital'}
    text=brief_fact(wording_db,item,bn,1)
    assert ('ঝুঁকিভিত্তিক সম্পদ' if bn else 'risk-weighted assets') in text
    row=wording_db.get(Fact,'synthetic-capital');row.value=Decimal('-.0548');wording_db.flush()
    text=brief_fact(wording_db,item,bn,1)
    assert ('মাইনাস' if bn else 'minus') in text
    assert ('লোকসানে' if bn else 'Losses') not in text

@pytest.mark.parametrize('language',['bn','en'])
def test_five_turn_conversation_is_connected_source_backed_and_does_not_repeat(wording_db,language):
    db=wording_db;c=Conversation(state='BANK',institution_id=1,language=language);seen=set();insurance=0
    for choice in ['bank','detail','figures','history','fdr']:
        result=ask(db,'BRAC Bank' if choice=='bank' else '',c,None if choice=='bank' else choice);c=conv(result)
        assert result['text']==result['speech'] and result['speech_parts']==[result['speech']]
        assert not re.search(r'[:;()—]|\bPLC\b|পিএলসি|\b[HWP][1-9]\b',result['speech'])
        assert result['speech'].endswith('?')
        ids=set(result['speech_fact_ids']);assert not seen&ids;seen|=ids
        assert ids<={f['fact_id'] for f in result['facts']}
        insurance+=int('insurance:bank' in ids)
        if choice=='bank':
            assert ('কারণ' if language=='bn' else 'because') in result['speech']
            assert ('প্রায় ১৮%' if language=='bn' else 'about 18%') in result['speech']
            assert ('সাড়ে ১২%' if language=='bn' else '12.5%') in result['speech']
            assert 'insurance:bank' in ids
            assert any(f['fact_id']=='insurance:bank' for f in result['facts'])
        if choice=='detail':
            assert 'synthetic-capital' not in ids
            assert 'test-npl-1' not in ids
            assert 'synthetic-rating' in ids
        if choice=='figures':assert 'synthetic-profit' in ids
        if choice=='history':assert ('সরকারিভাবে নিশ্চিত নয়' if language=='bn' else 'not officially confirmed') in result['speech']
        if choice=='fdr':
            assert '8.5%' in result['speech'] if language=='en' else '৮.৫%' in result['speech']
            assert not re.search(r'Strong|good condition|ভালো অবস্থা|ঝুঁকির',result['speech'])
            assert result['speech_fact_ids'] and len(result['speech'].split())<=70
    assert insurance==1


def test_exact_card_facts_are_unchanged_and_spoken_numbers_are_rounded(wording_db):
    facts=bank_summary(wording_db,1);n=compose(wording_db,facts,{'state':'BANK','institution_id':1,'language':'bn'},'আরও শুনবেন?','bank_summary')
    assert '১৮.০৭%' in ' '.join(f['text_bn'] for f in facts)
    assert 'প্রায় ১৮%' in n.speech and '১৮.০৭%' not in n.speech
    assert wording_db.get(Fact,'synthetic-capital').value==Decimal('.180700')
    assert rounded(Decimal('.4'),True)=='০.৪' and rounded(Decimal('2.73'),True)=='৩'


def test_insurance_does_not_promise_payment_from_bank_closure_or_flat_seventeen_days(wording_db):
    rule=wording_db.get(InsuranceRule,'bank');rule.payout_working_days=17
    rule.text_en+=' On liquidation: 10 working days for the depositor list, then 7 after required information.'
    wording_db.commit()
    result=ask(wording_db,'insurance',Conversation(state='BANK',institution_id=1,language='en'))
    assert 'member bank' in result['speech'] and 'accounts combined' in result['speech']
    assert 'Eligible deposits' in result['speech']
    assert 'after required information' in result['facts'][0]['text_en']
    assert '17' not in result['speech'] and 'will receive' not in result['speech']


def test_explicit_repeat_can_repeat_but_does_not_create_extra_fact_ids(wording_db):
    first=ask(wording_db,'BRAC Bank');second=ask(wording_db,'',conv(first),'repeat')
    assert 'about 18%' in second['speech']
    assert set(second['conversation']['spoken_fact_ids'])==set(first['conversation']['spoken_fact_ids'])


def test_missing_service_is_explicit_and_does_not_narrate_a_status(db):
    result=ask(db,'',Conversation(state='BANK',institution_id=1,language='bn'),'home_loan')
    assert 'এখনো নেই' in result['speech'] and 'ভালো অবস্থা' not in result['speech']


def test_explicit_figure_question_is_answered_even_if_earlier_explained(wording_db):
    first=ask(wording_db,'BRAC Bank')
    next_turn=ask(wording_db,'BRAC Bank CRAR কত',conv(first))
    assert '১৮%' in next_turn['speech'] if next_turn['language']=='bn' else '18%' in next_turn['speech']
    assert 'synthetic-capital' in next_turn['speech_fact_ids']


def test_insurance_finishes_with_a_related_question_not_a_bank_status_question(wording_db):
    result=ask(wording_db,'insurance',Conversation(state='BANK',institution_id=1,language='bn'))
    assert result['conversation']['state']=='NEXT' and 'অন্য ব্যাংকের কথা' in result['next']['question']
    assert 'কেন এমন বললাম' not in result['speech']


def test_legacy_bank_answer_preserves_exact_card_beside_connected_speech(wording_db):
    from ilma_api.voice_pipeline import build_result,readout_result
    from ilma_api.voice_text import VoiceIntent
    for language in ['bn','en']:
        result=build_result(VoiceIntent(intent='bank_status',institution_ids=[1]),[],language,wording_db)
        assert result['text']==result['speech_text']
        assert ('কারণ' if language=='bn' else 'because') in result['text']
        assert ('১৮.০৭%' if language=='bn' else '18.07%') in result['card_text']
        assert ('১৮.০৭%' if language=='bn' else '18.07%') not in result['speech_text']
        assert readout_result('report_card',1,language,wording_db)['text']==result['card_text']
        assert readout_result('report_card',1,language,wording_db)['speech_text']==result['card_text']


@pytest.mark.parametrize('text',['deposit insurance','What is deposit insurance?','deposit protection','আমানত সুরক্ষা'])
def test_generic_insurance_request_outranks_spurious_weak_bank_match(wording_db,text):
    c=Conversation(state='SERVICE',institution_id=1,language='en',product='fdr')
    spurious={**BANKS[1],'confidence':.75,'alias':'EBL Test Bank','confirm':False}
    with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('No planner for generic insurance'))):
        result=asyncio.run(run_agent_turn(text,context(c),BANKS,wording_db,[spurious]))
    assert result['conversation']['state']=='NEXT'
    assert result['conversation']['institution_id']==1
    assert result['conversation']['language']=='en'
    assert result['facts'][0]['fact_id']=='insurance:bank'


@pytest.mark.parametrize('language',['bn','en'])
def test_repeat_replays_the_selected_details_and_specific_figure(wording_db,language):
    result=ask(wording_db,'BRAC Bank',Conversation(language=language))
    result=ask(wording_db,'',conv(result),'detail')
    repeated=ask(wording_db,'',conv(result),'repeat')
    assert repeated['speech']==result['speech']
    assert repeated['speech_fact_ids']==result['speech_fact_ids']
    assert 'synthetic-capital' not in repeated['speech_fact_ids']
    result=ask(wording_db,'BRAC Bank net profit',conv(result))
    repeated=ask(wording_db,'',conv(result),'repeat')
    assert repeated['speech']==result['speech']
    assert repeated['speech_fact_ids']==['synthetic-profit']


def test_source_action_does_not_replace_the_last_answer_to_repeat(wording_db):
    first=ask(wording_db,'BRAC Bank')
    proof=ask(wording_db,'',conv(first),'proof')
    assert proof['action']['type']=='open_proof'
    assert proof['conversation']['last_tool']==first['conversation']['last_tool']
    assert proof['conversation']['last_spoken_fact_ids']==first['speech_fact_ids']
    repeated=ask(wording_db,'',conv(proof),'repeat')
    assert repeated['speech']==first['speech']


def test_insurance_questions_use_context_without_spurious_bank_clarification(wording_db):
    for text in ['How does deposit insurance work?','Explain deposit insurance']:
        result=ask(wording_db,text,Conversation(state='BANK',institution_id=1,language='en'))
        assert result['conversation']['state']=='NEXT' and result['conversation']['institution_id']==1
        assert result['conversation']['misses']==0


def test_opening_proof_does_not_request_speech(wording_db):
    from ilma_api.voice_pipeline import run_pipeline
    first=ask(wording_db,'BRAC Bank')
    async def run():
        register=AsyncMock(return_value=None)
        ctx=context(conv(first)).model_copy(update={'choice':'proof','speak':True})
        with patch('ilma_api.audio_cache.register_speech',new=register):
            frames=[f async for f in run_pipeline(None,'','',ctx,BANKS,wording_db,mode='text')]
        import json
        result=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: result'))
        assert result['action']['type']=='open_proof' and not result['audio_pending']
        assert not any(f.startswith('event: speech') for f in frames)
        register.assert_not_awaited()
    asyncio.run(run())


def test_repeat_of_already_explained_reply_does_not_restart_old_figures(wording_db):
    first=ask(wording_db,'BRAC Bank')
    again=ask(wording_db,'BRAC Bank',conv(first))
    assert again['speech_fact_ids']==[]
    repeated=ask(wording_db,'',conv(again),'repeat')
    assert repeated['speech']==again['speech'] and repeated['speech_fact_ids']==[]
    current=first
    for choice in ['detail','figures','figures','figures']:
        current=ask(wording_db,'',conv(current),choice)
    assert current['speech_fact_ids']==[]
    repeated=ask(wording_db,'',conv(current),'repeat')
    assert repeated['speech']==current['speech'] and repeated['speech_fact_ids']==[]



def test_card_minimum_and_fdr_caption_keep_exact_data_without_health_labels(wording_db):
    capital=next(f for f in bank_summary(wording_db,1) if f['fact_id']=='synthetic-capital')
    assert '১৮.০৭%' in capital['text_bn'] and 'ন্যূনতম ১২.৫%' in capital['text_bn']
    offer=service_detail(wording_db,1,'fdr')[0]
    for language in ['bn','en']:
        text=offer['text_'+language]
        assert not re.search(r'PLC|পিএলসি|Strong|ভালো অবস্থা|conditions apply|শর্ত প্রযোজ্য',text)
    assert '৮.৫%' in offer['text_bn'] and '৮,৫০০' in offer['text_bn']
    assert 'if this rate applies' in offer['text_en'] and 'before tax' in offer['text_en']
    assert 'Synthetic rate' in offer['source']['quote']


def test_weak_intro_retains_conditional_protection_and_negative_figure_uses_tenths(wording_db):
    row=wording_db.get(Fact,'synthetic-capital');row.value=Decimal('-.0548');row.quote='Synthetic capital minus 5.48 percent';wording_db.commit()
    first=ask(wording_db,'BRAC Bank',Conversation(language='bn'))
    assert 'insurance:bank' in first['speech_fact_ids'] and 'শর্ত' in first['speech']
    assert len(first['speech'].split())<=45
    figure=ask(wording_db,'মূলধন কত',conv(first))
    assert 'মাইনাস সাড়ে ৫%' in figure['speech']
    assert '-৫.৪৮%' in figure['sentences'][0]['text']



def test_non_currency_offer_units_are_not_spoken_as_money(wording_db):
    from ilma_api.answer_wording import brief_offer
    row=wording_db.get(ServiceOffer,'test-fdr-1');row.unit='count';row.attribute='lounge_access';row.product_type='card';row.value_num=5;wording_db.commit()
    item={'fact_id':row.offer_id,'institution_id':1}
    assert 'taka' not in brief_offer(wording_db,item,False)
    assert 'টাকা' not in brief_offer(wording_db,item,True)
    assert 'card' in brief_offer(wording_db,item,False)


def test_long_source_wording_pages_with_no_lost_words_or_premature_fact_completion(wording_db):
    record=wording_db.get(BankIncident,'synthetic-history')
    # Handwritten repeated synthetic clauses stress paging, not copied source data.
    title='একটি প্রক্রিয়াগত ত্রুটির অভিযোগ নিয়ে তদন্ত করা হয়েছে, '
    record.title_bn=title*12;wording_db.commit()
    result=ask(wording_db,'',Conversation(state='BANK',institution_id=1,language='bn'),'history')
    chunks=[];original_id='synthetic-history';pages=0
    while True:
        pages+=1;assert pages<10
        assert len(result['speech'].split())<=70
        assert original_id in result['speech_fact_ids']
        chunks.append(result['speech'])
        c=conv(result)
        if not c.speech_page_fact_ids:break
        assert original_id not in c.spoken_fact_ids,'Do not mark the unseen remainder as completed'
        assert result['next']['options'][0]['value']=='more'
        replay=ask(wording_db,'',c,'repeat')
        assert replay['speech']==result['speech']
        result=ask(wording_db,'আরও শুনব',c)
    assert pages>1 and original_id in c.spoken_fact_ids
    assert sum(t.count('প্রক্রিয়াগত') for t in chunks)==12


def test_tts_uses_resolved_reply_language_not_the_old_ui_language(wording_db):
    from ilma_api.voice_pipeline import run_pipeline
    import json
    async def run():
        register=AsyncMock(return_value=None)
        ctx=context(Conversation(state='BANK',institution_id=1,language='bn')).model_copy(update={'speak':True})
        with patch('ilma_api.audio_cache.register_speech',new=register):
            frames=[f async for f in run_pipeline(None,'How is BRAC Bank?','',ctx,BANKS,wording_db,mode='text')]
        result=next(json.loads(f.split('data: ',1)[1]) for f in frames if f.startswith('event: result'))
        assert result['language']=='en'
        assert register.await_args.args[1]=='en'
        assert '%' not in result['speech_tts'] and 'percent' in result['speech_tts']
    asyncio.run(run())


def test_continuation_spoken_options_and_ordinals_match_visible_choices():
    from ilma_api.voice_agent import spoken_choice
    c=Conversation(state='HISTORY',institution_id=1,speech_page=1,speech_page_fact_ids=['synthetic-history'])
    for word in ['আরও শুনুন','এক','one','হ্যাঁ','yes']:assert spoken_choice(word,c)=='more'
    for word in ['দুই','two','না','no']:assert spoken_choice(word,c)=='end'


def test_every_spoken_source_is_visible_in_the_exact_card(wording_db):
    result=ask(wording_db,'BRAC Bank')
    visible={id for sentence in result['sentences'] for id in sentence['fact_ids']}
    assert set(result['speech_fact_ids'])<=visible
    assert {fact['fact_id'] for fact in result['facts']}<=visible
