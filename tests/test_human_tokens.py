"""Tiny handwritten synthetic facts; no exports, real recordings or paid calls."""
import asyncio,json
from unittest.mock import patch,AsyncMock
import httpx,pytest
from test_voice_agent import db,BANKS
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext,join_acronyms
from ilma_api.human_resolver import resolve
from ilma_api.human_tokens import FactToken,fill,build_registry,PROTECTION_WORDS,BANNED
from ilma_api.human_stream import Draft,Header,generate
from ilma_api.human_turn import run,prepare,packet,paginate

@pytest.fixture(autouse=True)
def contextual_mode(isolate_voice_mode,monkeypatch):
    from ilma_api import settings
    monkeypatch.setattr(settings,'HUMAN_VOICE_ENABLED',True)

@pytest.mark.parametrize('text',['ই বি এল','ই.বি.এল','E B L','E.B.L.'])
def test_spelled_acronym_switches_to_named_bank(text):
    r=resolve(text,Conversation(institution_id=1),BANKS)
    assert r.bank_id==2

def test_correction_keeps_comparison_term_and_product():
    c=Conversation(institution_id=1,product='dps',tenor=12,last_intent='compare')
    r=resolve('না, ই বি এল এর সাথে বলুন',c,BANKS)
    assert (r.bank_id,r.product,r.tenor,r.intent)==(2,'dps',12,'compare')
    assert r.compare_bank_ids==[2,1]
    r=resolve('না, তিন বছরের হবে',c,BANKS)
    assert r.tenor==36 and r.intent=='compare'

@pytest.mark.parametrize('text',[
 'আমি প্রাইমের কথাই বলছি','ব্যাংকটা বদলে প্রাইম ধরুন','না প্রাইম সম্পর্কে জানতে চেয়েছি',
 'শুধরে নিন প্রাইম বলেছি','Correct the bank to Prime','না প্রাইম হবে ইবিএল নয়',
 'আগের প্রশ্নটা প্রাইমের জন্য করুন','I meant Prime Bank, not Eastern.',
 'ব্যাংকের নাম প্রাইম হবে','প্রাইমের জন্যই জানতে চেয়েছি','The previous question was about Prime.'
])
def test_short_bank_corrections_resolve_affirmative_name(text):
    banks=[*BANKS,dict(id=3,slug='primebank',name_bn='পরীক্ষা প্রাইম ব্যাংক',name_en='Prime Test Bank',aliases=['Prime Bank'],type='bank',coverage='full')]
    r=resolve(text,Conversation(institution_id=2,product='dps',tenor=12,last_intent='compare'),banks)
    assert r.bank_id==3
    assert r.product=='dps' and r.tenor==12

def test_year_on_year_profit_is_not_a_bank_comparison():
    r=resolve('আগের বছরের তুলনায় লাভ কেমন',Conversation(institution_id=1),BANKS)
    assert r.intent=='bank_figures'

def test_advice_words_override_a_savings_product_slot():
    r=resolve('Choose a bank for my savings',Conversation(institution_id=1),BANKS)
    assert r.intent=='advice_request'

def test_deposit_drops_card_slots_and_bank_switch_drops_tenor():
    c=Conversation(institution_id=1,product='card',network='Visa',tier='Gold',tenor=12)
    r=resolve('এই ব্যাংকের ডিপিএস',c,BANKS)
    assert r.product=='dps' and r.network is r.tier is r.tenor is None
    r=resolve('ইবিএল সম্পর্কে বলুন',c,BANKS)
    assert r.bank_id==2 and r.tenor is None

@pytest.mark.parametrize('text',['ব্যাংক বন্ধ হলে কী হবে','আমার টাকা কি সুরক্ষিত','deposit insurance'])
def test_only_explicit_protection_questions_request_insurance(text):
    r=resolve(text,Conversation(institution_id=1),BANKS)
    assert r.direct_protection and r.intent=='insurance'
    assert not resolve('ব্যাংক নিরাপদ কি',Conversation(institution_id=1),BANKS).direct_protection

def test_tokens_bind_values_and_bank_and_declared_sources():
    reg={'bank:1':FactToken('Example bank',(),1,'bank'),'f:synthetic':FactToken('quotes 8%',('synthetic',),1),'bank:2':FactToken('Other bank',(),2,'bank')}
    assert fill('⟨bank:1⟩ ⟨f:synthetic⟩.',reg,['synthetic'])==('Example bank quotes 8%.',['synthetic'])
    for text,ids,error in [('⟨f:missing⟩',[],'unknown_token'),('⟨f:synthetic⟩',[],'undeclared_fact'),('⟨bank:2⟩ ⟨f:synthetic⟩',['synthetic'],'bank_fact_binding'),('⟨f:synthetic⟩ 99%', ['synthetic'],'raw_value'),('⟨f:synthetic⟩ is highest',['synthetic'],'raw_value'),('⟨f:synthetic⟩ is guaranteed',['synthetic'],'raw_claim')]:
        with pytest.raises(ValueError,match=error):fill(text,reg,ids)

def test_per_sentence_repair_and_code_built_comparison_need_one_call(db):
    async def model(payload,trace,client,**kwargs):
        rows=[e for e in payload['tokens'] if e['token'].startswith('⟨row:') and e['token'].endswith('.offer⟩')]
        bank=lambda e:e['token'].replace('.offer','.bank')
        used=list(dict.fromkeys(fid for row in rows for fid in row['used']))
        trace.append(dict(stage='PLAN',model='synthetic',status='ok',ms=1))
        return Draft(Header(intent='compare',used=used,buttons=['services','ask_bank']),[bank(row)+' '+row['token']+'.' for row in rows])
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model)) as mocked:
            result=await run('Compare FDRs for 12 months',VoiceContext(agent=True,ui_lang='en',speak=False,conversation=Conversation(institution_id=1,language='en')),BANKS,db,device_hash='synthetic')
            continuation=await run('yes',VoiceContext(agent=True,ui_lang='en',speak=False,conversation=Conversation.model_validate(result['conversation'])),BANKS,db)
        assert mocked.await_count==1 and result['checked']=='code'
        assert result['conversation']['tenor']==12
        assert {f['institution_id'] for f in result['facts']+continuation['facts']}=={1,2}
        assert len(result['next']['options'])==2
    asyncio.run(scenario())

@pytest.mark.parametrize('intent',['bank_overview','bank_condition','bank_reasons','bank_figures','services_list','service_detail','compare','bank_profile'])
def test_fallbacks_never_volunteer_protection(db,intent):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(return_value=Draft(error='timeout'))):
            result=await run('Synthetic question',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(institution_id=1,product='fdr',last_intent=intent)),BANKS,db,choice={'bank_overview':'bank_1','bank_condition':'bank_1','bank_reasons':'detail','bank_figures':'figures','services_list':'services','service_detail':'fdr','compare':'compare','bank_profile':'detail'}[intent])
        assert not PROTECTION_WORDS.search(result['speech'])
        assert len(result['next']['options'])==2
        assert len(result['speech_tts'].split())<=45
    asyncio.run(scenario())

def test_stream_protocol_handles_fragmented_header_without_paid_requests():
    async def scenario():
        content='{"intent":"bank_figures","used":["t0"],"buttons":["services","ask_bank"]}\n⟨f:t0⟩।\nQ: আরও শুনবেন?'
        def respond(request):
            body=json.loads(request.content);assert body['stream'] is True
            events=''.join('data: '+json.dumps({'choices':[{'delta':{'content':content[i:i+7]}}]},ensure_ascii=False)+'\n\n' for i in range(0,len(content),7))+'data: [DONE]\n\n'
            return httpx.Response(200,text=events,headers={'Content-Type':'text/event-stream'})
        lines=[]
        async def received(line,header):lines.append(line)
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            draft=await generate({},[],client,on_line=received)
        assert draft.error is None and draft.header.used==['t0'] and lines==['⟨f:t0⟩।']
        assert draft.question.endswith('?')
    asyncio.run(scenario())

def test_model_contract_and_exact_server_repeat(db):
    from ilma_api.human_memory import verified_id
    from ilma_api.db import AppConversation
    async def model(payload,trace,client,**kwargs):
        entry=next(e for e in payload['tokens'] if e['token'].startswith('⟨f:') and 'positive sign' in e['meaning'])
        return Draft(Header(intent='bank_figures',used=entry['used']),[entry['token']+'.'])
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model)) as mocked:
            result=await run('What is the ratio?',VoiceContext(agent=True,ui_lang='en',speak=False,conversation=Conversation(institution_id=1,language='en')),BANKS,db)
            c=Conversation.model_validate(result['conversation'])
            repeated=await run('',VoiceContext(agent=True,ui_lang='en',speak=False,conversation=c),BANKS,db,choice='repeat')
        assert mocked.await_count==1 and result['checked']=='code'
        assert repeated['speech']==result['speech'] and repeated['speech_fact_ids']==result['speech_fact_ids']
        assert len(db.get(AppConversation,verified_id(c.conversation_token)).memory['last_turns'])==2
    asyncio.run(scenario())

def test_short_references_decode_to_original_immutable_facts(db):
    c=Conversation(institution_id=1,language='en')
    r,c,packs,comparisons,registry,facts=prepare(db,'How is it?',c,BANKS)
    payload,decode=packet(r,c,{},registry,facts,'synthetic')
    entry=next(e for e in payload['tokens'] if e['token'].startswith('⟨f:') and e['used'])
    rendered,reverse=decode(entry['token'])
    assert all(reverse[id] in facts for id in entry['used'])
    assert TOKEN_KEY(rendered) in registry

def TOKEN_KEY(value):return value[1:-1]

def test_long_replies_continue_at_sentence_boundaries():
    lines=[(' '.join(['word']*20)+'.',[str(i)]) for i in range(3)]
    head,tail=paginate(lines,'Would you like more?','en')
    assert len(head)==2 and tail==[lines[2]] and head[-1][0].endswith('.')

def test_stream_retries_transient_error_without_a_second_wording_pass():
    async def scenario():
        calls=[]
        def respond(request):
            calls.append(request)
            if len(calls)==1:return httpx.Response(503)
            text='{"intent":"smalltalk","used":[],"buttons":["services","ask_bank"]}\nHello.\nQ: What would you like to know?'
            return httpx.Response(200,json={'choices':[{'message':{'content':text}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            draft=await generate({},[],client)
        assert draft.error is None and len(calls)==2
    asyncio.run(scenario())

def test_checked_sentence_arrives_before_stream_completion():
    async def scenario():
        arrived=asyncio.Event();release=asyncio.Event()
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                head='{"header":{"intent":"bank_figures","used":["t0"],"buttons":["services","ask_bank"]},"lines":["⟨f:t0⟩.",'
                yield ('data: '+json.dumps({'choices':[{'delta':{'content':head}}]})+'\n\n').encode()
                await release.wait()
                yield ('data: '+json.dumps({'choices':[{'delta':{'content':'] ,"question":"More?"}'}}]})+'\n\n').encode()
        async def received(line,header):
            assert line=='⟨f:t0⟩.' and header.used==['t0'];arrived.set()
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=Stream(),headers={'Content-Type':'text/event-stream'}))) as client:
            task=asyncio.create_task(generate({},[],client,on_line=received))
            await asyncio.wait_for(arrived.wait(),1)
            assert not task.done()
            release.set();draft=await task
            # Deliberately malformed trailing JSON is unavailable; the checked
            # first sentence still arrived before the provider closed.
            assert draft.error=='schema'
    asyncio.run(scenario())

def test_interrupted_bank_resolution_is_saved_without_user_words(db):
    from ilma_api.human_memory import verified_id
    from ilma_api.db import AppConversation
    async def scenario():
        messages=[]
        async def received(value):messages.append(value)
        async def model(*args,**kwargs):raise asyncio.CancelledError()
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model)):
            with pytest.raises(asyncio.CancelledError):
                await run('ই বি এল সম্পর্কে বলুন',VoiceContext(agent=True,ui_lang='bn',conversation=Conversation(institution_id=1)),BANKS,db,on_sentence=received)
        context=messages[0]
        assert context['_event']=='resolved_context' and context['conversation']['institution_id']==2
        memory=db.get(AppConversation,verified_id(context['conversation']['conversation_token'])).memory
        assert memory['conversation']['institution_id']==2
        assert 'সম্পর্কে বলুন' not in json.dumps(memory,ensure_ascii=False)
    asyncio.run(scenario())

def test_variant_fingerprint_ignores_user_words_but_invalidates_changed_facts(db):
    from ilma_api.human_variants import fingerprint
    r,c,_,_,registry,facts=prepare(db,'General introduction',Conversation(institution_id=1,language='en'),BANKS,forced='bank_overview')
    payload,_=packet(r,c,{},registry,facts,'synthetic')
    changed={**payload,'words':'Another person asks about this bank'}
    assert fingerprint(payload,registry)==fingerprint(changed,registry)
    assert fingerprint(payload,registry)!=fingerprint({**payload,'fact_revision':'changed-source'},registry)

def test_islamic_slot_is_retained_on_followup_and_reset_on_bank_switch():
    banks=[*BANKS,dict(id=3,slug='islamic-test',name_bn='পরীক্ষা ইসলামি ব্যাংক',name_en='Islamic Test Bank',aliases=['Islamic Test'],islamic=True,type='bank',coverage='full')]
    r=resolve('Islamic Test Bank FDR',Conversation(institution_id=1),banks)
    assert r.bank_id==3 and r.basis=='islamic'
    r=resolve('আর ডিপিএস?',Conversation(institution_id=3,basis='islamic'),banks)
    assert r.basis=='islamic'
    r=resolve('EBL',Conversation(institution_id=3,basis='islamic'),banks)
    assert r.bank_id==2 and r.basis=='conventional'

def test_missing_bank_asks_once_without_a_paid_call(db):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock()) as model:
            result=await run('What is the FDR rate?',VoiceContext(agent=True,ui_lang='en',speak=False),BANKS,db)
        model.assert_not_awaited()
        assert result['conversation']['institution_id'] is None
        assert 'Which bank' in result['speech'] and len(result['next']['options'])==2
    asyncio.run(scenario())

def test_provider_timeout_after_checked_prefix_keeps_the_prefix(db):
    async def model(payload,trace,client,**kwargs):
        entry=next(e for e in payload['tokens'] if e['token'].startswith('⟨f:') and 'positive sign' in e['meaning'])
        return Draft(Header(intent='bank_figures',used=entry['used']),[entry['token']+'.'],error='timeout')
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model)) as mocked:
            result=await run('What is the ratio?',VoiceContext(agent=True,ui_lang='en',speak=False,conversation=Conversation(institution_id=1,language='en')),BANKS,db)
        assert mocked.await_count==1 and result['checked']=='code'
        assert 'positive sign' in result['speech']
        assert any(step['stage']=='STREAM' and step['reason']=='timeout' for step in result['trace']['steps'])
        assert not any(step['stage']=='FALLBACK' for step in result['trace']['steps'])
    asyncio.run(scenario())

@pytest.mark.parametrize('question,intent',[
 ('এই প্রতিষ্ঠানের একটা ধারণা চাই','bank_overview'),
 ('এই সিদ্ধান্তের ভিত্তি বলুন',None),
 ('ব্যাংকের পণ্য সম্পর্কে একটা ধারণা দিন','services_list'),
 ('Tell me about its services','services_list'),
 ('সবার চেয়ে নিরাপদ কোন ব্যাংক','best_bank'),
 ('Name the number 1 bank','best_bank')])
def test_specific_service_and_assessment_requests_do_not_become_generic_intro(question,intent):
    assert resolve(question,Conversation(institution_id=1),BANKS).intent==intent

def test_answer_leads_with_bank_name_before_a_term_meaning(db):
    async def model(payload,trace,client,**kwargs):
        term=next(e for e in payload['tokens'] if e['token'].startswith('⟨f:') and 'জমানোর স্কিম' in e['meaning'])
        rate=next(e for e in payload['tokens'] if e['token'].startswith('⟨f:') and 'এফডিআরে' in e['meaning'])
        return Draft(Header(intent='service_detail',used=term['used']+rate['used']),[term['token']+'।','⟨bank:1⟩ের '+rate['token']+'।'])
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model)):
            return await run('এফডিআর আর ডিপিএস সম্পর্কে বলুন',VoiceContext(agent=True,ui_lang='bn',speak=False,conversation=Conversation(institution_id=1,language='bn')),BANKS,db)
    result=asyncio.run(scenario())
    assert result['speech'].startswith('পরীক্ষা ব্র্যাক ব্যাংকের ')
    assert 'জমানোর স্কিম।' in result['speech'] and '।।' not in result['speech']
