"""One-call contextual understanding and sourced conversational wording."""
import asyncio,copy,json,logging,random,re,time,uuid
from datetime import date
from decimal import Decimal
import httpx
from pydantic import ValidationError
from ilma_api import settings
from ilma_api.human_contract import HumanReply,STATE,LABELS,ALLOWED
from ilma_api.human_prompt import SYSTEM
from ilma_api.human_checker import check,sentences
from ilma_api.human_memory import load,save,token,redact_user
from ilma_api.human_facts import fact_pack,compact_pack,comparison_facts,service_facts
from ilma_api.database_tasks import call
from ilma_api.voice_numbers import pronounce
from ilma_api.voice_text import normalize_alias,match_candidates
from ilma_api.db import Institution,AppModelCall


def enabled():return bool(getattr(settings,'HUMAN_VOICE_ENABLED',True) and settings.META_MODEL_API_KEY and 'contributor' not in settings.MUSE_SPARK_MODEL.lower())


def exact_choice(text,c,memory,choice):
    if choice:return choice
    value=' '.join(text.casefold().strip(' .!?,।').split())
    for option in memory.get('last_next',{}).get('options',[]):
        labels=[option['value'],option['label'],*LABELS.get(option['value'],())]
        if value in (' '.join(label.casefold().strip(' .!?,।').split()) for label in labels):return option['value']
    return None


async def spark(payload,db,trace,turn_id,client=None,repair=None):
    from ilma_api.voice_agent import safe_schema
    started=time.monotonic();status='unavailable';usage={};reason='provider';provider_error=[]
    body={'model':settings.MUSE_SPARK_MODEL,'temperature':.7,'reasoning_effort':'minimal','max_tokens':650,
          'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({**payload,**({'repair_errors':repair} if repair else {})},ensure_ascii=False,default=str)}],
          'response_format':{'type':'json_schema','json_schema':{'name':'human_voice_turn','strict':True,'schema':safe_schema(HumanReply)}}}
    async def attempts(http):
        deadline=time.monotonic()+4.5
        for attempt in range(2):
            remaining=deadline-time.monotonic()
            if remaining<=.05:raise asyncio.TimeoutError()
            try:
                response=await asyncio.wait_for(http.post(settings.MUSE_SPARK_API_URL,headers={'Authorization':'Bearer '+settings.META_MODEL_API_KEY},json=body,timeout=httpx.Timeout(remaining,connect=min(2,remaining))),remaining)
                if response.status_code in {429,500,502,503,504} and attempt==0:
                    await asyncio.sleep(min(.1+random.random()*.15,max(0,deadline-time.monotonic())));continue
                if response.status_code!=200:
                    try:error=response.json().get('error',{})
                    except ValueError:error={}
                    parameter=str(error.get('param') or '') if isinstance(error,dict) else ''
                    provider_error.append('http_'+str(response.status_code)+(':'+parameter if re.fullmatch(r'[A-Za-z_.-]{1,64}',parameter) else ''))
                    raise ValueError('provider_status')
                data=response.json();return HumanReply.model_validate_json(data['choices'][0]['message']['content']),data.get('usage') or {}
            except (httpx.TimeoutException,httpx.ConnectError,asyncio.TimeoutError):
                if attempt or time.monotonic()>=deadline:raise
                await asyncio.sleep(.05+random.random()*.1)
        raise ValueError('provider')
    try:
        if client is None:
            from ilma_api.http_clients import shared
            client=shared()
        if client is None:
            async with httpx.AsyncClient(follow_redirects=False) as http:answer,usage=await attempts(http)
        else:answer,usage=await attempts(client)
        status='ok';return answer
    except (httpx.HTTPError,asyncio.TimeoutError,ValueError,KeyError,TypeError,IndexError) as error:
        reason='timeout' if isinstance(error,(httpx.TimeoutException,asyncio.TimeoutError)) else 'schema' if isinstance(error,ValidationError) else provider_error[-1] if provider_error else 'provider'
        return None
    finally:
        elapsed=round((time.monotonic()-started)*1000);trace.append(dict(stage='PLAN',model=settings.MUSE_SPARK_MODEL,ms=elapsed,status=status,reason=reason if status!='ok' else 'understand_and_say'))
        try:
            def audit(owned):
                owned.add(AppModelCall(turn_id=turn_id,stage='PLAN',model=settings.MUSE_SPARK_MODEL,latency_ms=elapsed,status=status,failure_reason=reason if status!='ok' else None,input_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens')));owned.flush()
            await call(db,audit)
        except Exception:trace[-1]['audit']='unavailable'


def guess(text):
    # Used only on provider/checker failure. Free text always reaches Spark first.
    patterns=[('stop',r'^(?:থামুন|থামান|stop)$'),('repeat',r'আবার|পুনরায়|repeat|again'),('smalltalk',r'হ্যালো|সালাম|ধন্যবাদ|thank|hello|\bhi\b'),
      ('advice_request',r'কোথায়.*রাখ|কোন ব্যাংকে.*রাখ|which bank should|recommend|best bank'),
      ('bank_history',r'আগের|অতীত|পূর্ব|ইতিহাস|ঘটনা|ঝামেলা|কেলেঙ্কারি|past|history|scandal|পাস্ট ইভেন্ট'),
      ('compare',r'তুলনা|মিলিয়ে|compare|another bank'),('service_detail',r'এফডিআর|ডিপিএস|\bfdr\b|\bdps\b|কার্ড|loan|সঞ্চয়'),
      ('bank_reasons',r'বিস্তারিত|কারণ|details|why|reasons'),('bank_figures',r'মুনাফা|লোকসান|মূলধন|খেলাপি|figures|profit|capital|rating'),
      ('bank_profile',r'শাখা|প্রতিষ্ঠা|যাত্রা|profile|founded|branches'),('insurance',r'বীমা|বিমা|সুরক্ষা|insurance|বন্ধ হলে'),('services_list',r'সেবা|services'),
      ('bank_condition',r'নিরাপদ|safe'),('bank_overview',r'কেমন|সম্পর্কে|how|about')]
    return next((intent for intent,pattern in patterns if re.search(pattern,text,re.I)),'unclear')


async def audit_rejection(db,turn_id,errors):
    def store(owned):
        owned.add(AppModelCall(turn_id=turn_id,stage='CHECK',model='code',latency_ms=0,status='rejected',failure_reason=','.join(errors)[:255]));owned.flush()
    try:await call(db,store)
    except Exception:logging.getLogger(__name__).warning('human_check_audit_unavailable')


def choose_initial(db,text,context,banks,memory):
    from ilma_api.voice_agent import Conversation
    c=Conversation.model_validate(memory.get('conversation') or (context.conversation.model_dump() if context.conversation else {'institution_id':context.bank_id,'language':context.ui_lang}))
    c=c.model_copy(update={'language':context.ui_lang})
    if c.institution_id and not db.get(Institution,c.institution_id):c=c.model_copy(update={'institution_id':None})
    candidates=match_candidates(text,banks) if text else []
    strong=[b for b in candidates if b['confidence']>=.9 and not b.get('confirm')]
    ids=list(dict.fromkeys(([c.institution_id] if c.institution_id else [])+[b['id'] for b in strong[:2]]))
    packs=[fact_pack(db,id,c.product if id==c.institution_id else None,c.tenor if id==c.institution_id else None,c.basis,c.network,c.tier) for id in ids]
    return c,candidates,packs


def resolve_bank(answer,text,c,banks,candidates):
    id=answer.bank.id
    if answer.bank.source=='conversation' or id is None and c.institution_id:return c.institution_id
    if id==c.institution_id:return id
    known=next((b for b in banks if b['id']==id),None)
    if not known:return None
    if any(b['id']==id and b['confidence']>=.9 and not b.get('confirm') for b in candidates):return id
    mention=normalize_alias(answer.bank.mention or '')
    if mention and mention in normalize_alias(text):
        aliases=[normalize_alias(n) for n in [known['name_en'],known['name_bn'],*known.get('aliases',[])]]
        if mention in aliases:return id
        if re.search(r'bank|ব্যাংক',answer.bank.mention or '',re.I) and any(b['id']==id and b['confidence']>=.75 for b in candidates):return id
    return c.institution_id


def update_slots(c,answer,id,text):
    changed=c.institution_id is not None and id!=c.institution_id
    product=answer.product if answer.product is not None else None if changed else c.product
    tenor=answer.tenor_months if answer.tenor_months is not None else None if changed else c.tenor
    network=answer.network if product=='card' else None;tier=answer.tier if product=='card' else None
    if product=='card' and not changed:network=network or c.network;tier=tier or c.tier
    return c.model_copy(update={'institution_id':id,'product':product,'tenor':tenor,'network':network,'tier':tier,'basis':answer.basis or c.basis,'language':answer.language,'last_intent':answer.intent})


def options_for(answer,c,facts):
    state=STATE.get(answer.intent,c.state);values=[v for v in answer.buttons if v in ALLOWED.get(state,set()) or v in {'end','repeat','more'}][:2]
    options=[]
    peers=[id for id in dict.fromkeys(f['institution_id'] for f in facts) if id!=c.institution_id]
    for value in values:
        if value.startswith('bank_'):
            index=int(value[-1])-1
            if index>=len(peers):continue
            bank=next((f for f in facts if f['institution_id']==peers[index]),None)
            label=bank.get('bank_name_bn' if c.language=='bn' else 'bank_name_en') if bank else None
            if not label:continue
        else:label=LABELS.get(value,('অন্য কিছু','Something else'))[0 if c.language=='bn' else 1]
        options.append({'value':value,'label':label})
    return {'question':answer.next_question,'options':options}


def limit_body(answer):
    # Complete sentences only; remainder stays in signed server memory.
    parts=sentences(answer.reply);budget=60-max(6,len(answer.next_question.split()));selected=[]
    for index,part in enumerate(parts):
        if sum(len(p.split()) for p in selected)+len(part.split())>budget:break
        selected.append(part)
    if len(selected)==len(parts):return answer,None
    if not selected:return answer,None  # checker retries a single overlong sentence
    tail=parts[len(selected):];pending={'reply':' '.join(tail),'sentence_fact_ids':answer.sentence_fact_ids[len(selected):],'next_question':answer.next_question,'buttons':answer.buttons,'intent':answer.intent}
    ids=list(dict.fromkeys(id for row in answer.sentence_fact_ids[:len(selected)] for id in row))
    return answer.model_copy(update={'reply':' '.join(selected),'sentence_fact_ids':answer.sentence_fact_ids[:len(selected)],'used_fact_ids':ids,'next_question':'আরও শুনবেন?' if answer.language=='bn' else 'Would you like to hear more?','buttons':['more','end']}),pending


def render(answer,c,facts,trace,checked='code'):
    if c.language=='bn':
        digits=str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')
        answer=answer.model_copy(update={'reply':answer.reply.translate(digits),'next_question':answer.next_question.translate(digits)})
    known={f['fact_id']:f for f in facts};used=[known[id] for id in answer.used_fact_ids if id in known]
    question=answer.next_question.strip();speech=(answer.reply.strip()+' '+question).strip()
    c=c.model_copy(update={'state':STATE.get(answer.intent,c.state),'turn':min(20,c.turn+1),'last_intent':answer.intent,'spoken_fact_ids':list(dict.fromkeys([*c.spoken_fact_ids,*answer.used_fact_ids]))[-128:],
      'last_spoken_fact_ids':answer.used_fact_ids,'fact_ids':answer.used_fact_ids,'insurance_said':c.insurance_said or any(f['kind']=='insurance' for f in used),
      'compare_bank_ids':list(dict.fromkeys(f['institution_id'] for f in used if f.get('institution_id') and f['institution_id']!=c.institution_id))[:3] if answer.intent=='compare' else c.compare_bank_ids})
    next=options_for(answer,c,used)
    action={'type':'end'} if answer.intent=='smalltalk' and re.search(r'ধন্যবাদ|thank',answer.reply,re.I) and not question or c.turn>=20 else {'type':'stop'} if answer.intent=='stop' else None
    return dict(type='agent_turn',intent=answer.intent,language=c.language,offer_typing=c.misses>=2,sentences=[dict(text=f['text_bn' if c.language=='bn' else 'text_en'],fact_ids=[f['fact_id']],source=f['source']) for f in used],facts=used,checked=checked,next=next,conversation=c.model_dump(),action=action,text=speech,speech=speech,speech_tts=pronounce(speech,c.language),speech_format='paragraph',speech_fact_ids=answer.used_fact_ids,sources=[f['source'] for f in used],speech_text=speech,speech_parts=[speech],trace={'steps':trace,'total_ms':0,'status_rule_notice':'ব্যাংকের অবস্থা তথ্যভিত্তিক নিয়মে ঠিক হয়।' if c.language=='bn' else 'Bank conditions come from sourced rules.'},omit_history=False)


def controls(intent,c,body,question='',buttons=()):
    return HumanReply(intent=intent,bank={'id':c.institution_id,'source':'conversation','mention':None},product=c.product,basis=c.basis,tenor_months=c.tenor,network=c.network,tier=c.tier,compare_banks=[],needs_facts=None,used_fact_ids=[],reply=body,sentence_fact_ids=[[] for _ in sentences(body)],next_question=question,buttons=list(buttons),language=c.language or 'bn')


async def run(text,context,banks,db,candidates=(),choice=None,watch_identity=None,client=None,device_hash=None):
    from ilma_api.voice_agent import Conversation
    from ilma_api.voice_pipeline import consume_question
    started=time.monotonic();turn_id=uuid.uuid4().hex;trace=[dict(stage='ASR',model='none',ms=0,status='transcript_received')]
    initial=context.conversation or Conversation(institution_id=context.bank_id,language=context.ui_lang)
    id,memory=await call(db,lambda owned:load(owned,initial.conversation_token))
    c,candidates,packs=await call(db,lambda owned:choose_initial(owned,text,context,banks,memory))
    selected=exact_choice(text,c,memory,choice)
    safe=redact_user(text)
    if c.turn>=19:selected='end'
    if selected:
        return await action_turn(selected,safe,c,id,memory,packs,banks,db,trace,started,watch_identity)
    if context.audio_truncated:
        a=controls('unclear',c,'শেষ অংশটা শুনতে পাইনি। প্রশ্নটি একটু ছোট করে আবার বলবেন?' if c.language=='bn' else 'I may have missed the ending. Could you ask a shorter question?','',['repeat','end'])
        result=render(a,c,[],trace,'template');result['audio_truncated']=True
        return await finish(result,safe,id,memory,db,started)
    # Charge before the paid model. Pure UI lookups/buttons remain available.
    await call(db,lambda owned:consume_question(owned,watch_identity or device_hash or 'human-anonymous'))
    payload={'user_words':safe,'raw_transcript':safe,'alias_candidates':[{k:v for k,v in b.items() if k in {'id','name_bn','name_en','confidence','alias'}} for b in candidates[:3]],
      'memory':{'current_bank_id':c.institution_id,'product':c.product,'tenor_months':c.tenor,'basis':c.basis,'network':c.network,'tier':c.tier,'last_turns':memory.get('last_turns',[])[-4:],'spoken_fact_ids':c.spoken_fact_ids,'insurance_said':c.insurance_said,'last_intent':c.last_intent},
      'fact_packs':[compact_pack(p,context.ui_lang) for p in packs],'language':context.ui_lang,'allowed_buttons':list(LABELS)}
    if context.audio_truncated:payload['audio_notice']='Recording reached 15 seconds. Say the ending may not have been heard; invite a shorter question.'
    payload['memory']['clarify_candidates']=memory.get('clarify_candidates',[])
    answer=await spark(payload,db,trace,turn_id,client);pending=None;all_facts=[f for p in packs for f in p['facts']]
    if answer:
        from ilma_api.other_banks import find_other_bank
        if find_other_bank(safe):
            result=await call(db,lambda owned:make_fallback(owned,safe,c,packs,banks,trace))
            return await finish(result,safe,id,memory,db,started)
        medium=[b for b in candidates if .7<=b['confidence']<.9]
        if answer.intent=='unclear' and answer.bank.source=='asked' and medium and (not c.institution_id or re.search(r'bank|ব্যাংক',safe,re.I)):
            choices=list(dict.fromkeys(([c.institution_id] if c.institution_id else [])+[b['id'] for b in medium]))[:2]
            memory['clarify_candidates']=choices
            labels=[next(b['name_bn' if c.language=='bn' else 'name_en'] for b in banks if b['id']==id) for id in choices]
            question=(' নাকি '.join(labels)+' বলছেন?' if c.language=='bn' else 'Did you mean '+' or '.join(labels)+'?')
            result=render(controls('unclear',c,question),c,[],trace,'code')
            result['next']={'question':question,'options':[dict(value='bank_'+str(i+1),label=label) for i,label in enumerate(labels)]}
            return await finish(result,safe,id,memory,db,started)
        if answer.intent=='correction':
            prior=c.last_intent if c.last_intent not in {None,'correction','unclear','stop','repeat'} else 'bank_overview'
            answer=answer.model_copy(update={'intent':prior,'needs_facts':'compare' if prior=='compare' else 'bank',
                'compare_banks':list(dict.fromkeys([*answer.compare_banks,*([c.institution_id] if c.institution_id and prior=='compare' else [])]))[:4]})
        target=resolve_bank(answer,safe,c,banks,candidates)
        # A low-score incidental phrase never replaces a contextual bank.
        answer=answer.model_copy(update={'bank':answer.bank.model_copy(update={'id':target}),'language':context.ui_lang})
        proposed=update_slots(c,answer,target,safe)
        c=proposed
        need=answer.needs_facts or answer.intent=='compare' or (answer.intent=='service_detail' and (answer.product!=payload['memory']['product'] or answer.tenor_months!=payload['memory']['tenor_months'] or answer.basis and answer.basis!=payload['memory']['basis'])) or (target and target not in [p['bank']['id'] for p in packs if p['bank']])
        if need:
            packs,extra=await call(db,lambda owned:retrieve(owned,answer,proposed,banks))
            all_facts=[f for p in packs for f in p['facts']]+extra
            payload.update(fact_packs=[compact_pack(p,context.ui_lang) for p in packs],retrieved_facts=extra,needs_facts_resolved=True)
            answer=await spark(payload,db,trace,turn_id,client)
            if answer:answer=answer.model_copy(update={'bank':answer.bank.model_copy(update={'id':target}),'language':context.ui_lang})
        if answer:
            if answer.intent=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
            answer,pending=limit_body(answer)
            errors=check(answer,all_facts,banks,c.spoken_fact_ids,allow_repeat=explicit_revisit(text,answer),insurance_said=c.insurance_said)
            if errors:
                trace.append(dict(stage='CHECK',model='code',ms=0,status='rejected',reason=','.join(errors)))
                logging.getLogger(__name__).warning('human_reply_rejected reasons=%s',','.join(errors))
                await audit_rejection(db,turn_id,errors)
                answer=await spark(payload,db,trace,turn_id,client,errors)
                if answer:
                    answer=answer.model_copy(update={'bank':answer.bank.model_copy(update={'id':target}),'language':context.ui_lang});answer,pending=limit_body(answer)
                    errors=check(answer,all_facts,banks,c.spoken_fact_ids,allow_repeat=explicit_revisit(text,answer),insurance_said=c.insurance_said)
                    if errors:
                        trace.append(dict(stage='CHECK',model='code',ms=0,status='rejected',reason=','.join(errors)))
                        logging.getLogger(__name__).warning('human_reply_rejected reasons=%s',','.join(errors))
                        await audit_rejection(db,turn_id,errors)
            if not errors and answer:
                c=update_slots(c,answer,target,safe)
                c=c.model_copy(update={'misses':min(2,c.misses+1) if answer.intent=='unclear' else 0})
                trace.extend([dict(stage='SAY',model=settings.MUSE_SPARK_MODEL,ms=0,status='ok'),dict(stage='CHECK',model='code',ms=0,status='ok')])
                result=render(answer,c,all_facts,trace)
                if pending:result['_all_facts']=all_facts
                return await finish(result,safe,id,memory,db,started,pending)
    # Network/schema/check failure is not evidence that the user was unclear.
    result=await call(db,lambda owned:make_fallback(owned,safe,c,packs,banks,trace))
    return await finish(result,safe,id,memory,db,started,result.pop('_pending_reply',None))


def explicit_revisit(text,answer):
    return answer.intent=='repeat' or answer.intent in {'bank_figures','bank_condition','service_detail','insurance'} and bool(re.search(r'কত|কী|কি|আবার|\bwhat|\bhow|\brate|\bratio',text,re.I))


def retrieve(db,answer,c,banks):
    ids=list(dict.fromkeys(([c.institution_id] if c.institution_id else [])+answer.compare_banks))[:4]
    packs=[fact_pack(db,id,c.product,c.tenor,c.basis,c.network,c.tier) for id in ids if any(b['id']==id for b in banks)]
    extra=comparison_facts(db,c.institution_id,c.product or 'fdr',c.tenor,c.basis,answer.compare_banks,c.network,c.tier) if answer.intent=='compare' or answer.needs_facts=='compare' else []
    return packs,extra


async def finish(result,user,id,memory,db,started,pending=None):
    result['conversation']['conversation_token']=token(id);result['trace']['total_ms']=round((time.monotonic()-started)*1000)
    pending_facts=result.pop('_all_facts',result['facts']) if pending else []
    saved={**memory,'conversation':result['conversation'],'last_turns':[*memory.get('last_turns',[]),dict(user=user,reply=result['speech'],intent=result.get('intent'),bank_id=result['conversation']['institution_id'],fact_ids=result['speech_fact_ids'])][-4:],
           'last_result':{key:copy.deepcopy(value) for key,value in result.items() if key not in {'trace','speech_parts','speech_text'}},'last_next':result['next'],'pending_reply':pending,'pending_facts':pending_facts}
    await call(db,lambda owned:save(owned,id,saved))
    result['memory_turn']={'question':user,'answer':result['speech']}
    return result


async def repeat_turn(c,id,memory,db,trace,started):
    result=copy.deepcopy(memory['last_result']);result.update(speech_text=result['speech'],speech_parts=[result['speech']],trace={'steps':trace,'total_ms':round((time.monotonic()-started)*1000),'status_rule_notice':'Repeated checked reply.'})
    result['intent']='repeat'
    result['conversation']['turn']=min(20,c.turn+1)
    if memory.get('pending_reply'):result['_all_facts']=memory.get('pending_facts',result['facts'])
    return await finish(result,'[repeat]',id,memory,db,started,memory.get('pending_reply'))


def make_fallback(db,text,c,packs,banks,trace,intent=None,comparison=None):
    from ilma_api.answer_wording import brief_fact,brief_insurance,brief_offer,bank_name,clean
    from ilma_api.voice_agent import service_request
    intent=intent or guess(text);bn=c.language=='bn';ending='।' if bn else '.'
    if intent=='repeat':intent='bank_overview'
    confident=[b for b in match_candidates(text,banks) if b['confidence']>=.9 and not b.get('confirm')]
    if confident and intent=='unclear':intent='bank_overview'
    if confident and confident[0]['id']!=c.institution_id:c=c.model_copy(update={'institution_id':confident[0]['id'],'product':None,'tenor':None,'network':None,'tier':None})
    request=service_request(text,c,c.institution_id)
    if request:
        intent='compare' if intent=='compare' else 'service_detail'
        c=c.model_copy(update={'product':request.args.product,'tenor':request.args.tenor,'network':request.args.network,'tier':request.args.tier})
    if intent=='smalltalk':
        thanks=bool(re.search(r'ধন্যবাদ|thank',text,re.I));body=('আপনাকেও ধন্যবাদ। আবার জানতে চাইলে মাইক চাপুন।' if bn else 'Thank you too. Tap the microphone whenever you have another question.') if thanks else ('হ্যালো, আমি ইলমা।' if bn else 'Hello, I’m ILMA.')
        a=controls(intent,c,body,'' if thanks else 'কোন ব্যাংকের কথা জানতে চান?' if bn else 'Which bank would you like to discuss?',[] if thanks else ['ask_bank','end'])
        return render(a,c,[],trace,'template')
    if intent in {'advice_request','best_bank'}:
        a=controls('advice_request',c,'কোন ব্যাংকে টাকা রাখবেন সেটা আপনার সিদ্ধান্ত, আমি পরামর্শ দিই না। তবে ব্যাংকের অবস্থা আর প্রকাশিত হার পাশাপাশি বোঝাতে পারি।' if bn else 'That decision is yours, and I do not give advice. I can explain bank conditions and published rates side by side.','এফডিআর না ডিপিএস নিয়ে ভাবছেন?' if bn else 'Are you thinking of a fixed deposit or a DPS?',['fdr','dps'])
        return render(a,c,[],trace,'template')
    from ilma_api.other_banks import find_other_bank
    if find_other_bank(text):
        a=controls('unclear',c,'এই ব্যাংকের তথ্য এখনো যোগ হয়নি।' if bn else 'Information for this bank has not been added yet.','অন্য ব্যাংকের কথা জানতে চান?' if bn else 'Would you like to ask about another bank?',['ask_bank','end'])
        return render(a,c,[],trace,'template')
    if intent in {'stop','out_of_scope','unclear'}:
        body=('পড়া থামালাম।' if bn else 'I’ve stopped speaking.') if intent=='stop' else ('আমি ব্যাংকের তথ্য নিয়ে কথা বলতে পারি।' if bn else 'I can help with bank information.') if intent=='out_of_scope' else ('এখন উত্তর সাজাতে একটু সমস্যা হচ্ছে।' if bn else 'I’m having trouble preparing that answer right now.')
        a=controls(intent,c,body,'' if intent=='stop' else 'কোন ব্যাংকের তথ্য শুনবেন?' if bn else 'Which bank would you like to discuss?',[] if intent=='stop' else ['ask_bank','end'])
        return render(a,c,[],trace,'template')
    if not c.institution_id:
        a=controls('unclear',c,'ব্যাংকের নাম বললে খুঁজে দেখতে পারি।' if bn else 'Tell me the bank name and I can look it up.','কোন ব্যাংকের কথা বলছেন?' if bn else 'Which bank do you mean?',['ask_bank','end'])
        return render(a,c,[],trace,'template')
    from ilma_api.bank_services import DEMO_CODES
    bank=db.get(Institution,c.institution_id)
    if not bank or bank.slug not in DEMO_CODES|{'nbl','islamibank'}:
        a=controls('unclear',c,'এই ব্যাংকের তথ্য এখনো যোগ হয়নি।' if bn else 'Information for this bank has not been added yet.','অন্য ব্যাংকের কথা জানতে চান?' if bn else 'Would you like to ask about another bank?',['ask_bank','end'])
        return render(a,c,[],trace,'template')
    pack=fact_pack(db,c.institution_id,c.product if intent=='service_detail' else None,c.tenor,c.basis,c.network,c.tier)
    facts=pack['facts'];name=bank_name(db,c.institution_id,bn);rows=[];ids=[];question='আর কিছু জানতে চান?' if bn else 'What else would you like to know?';buttons=['services','ask_bank']
    def add(text,fact):
        if text:rows.append(clean(text)+ending);ids.append([fact['fact_id']] if fact else [])
    if intent in {'bank_overview','bank_condition','bank_reasons','bank_figures'}:
        if intent in {'bank_overview','bank_condition'}:
            f=next((f for f in facts if f['kind']=='status'),None)
            label=pack['status'].get('label_bn' if bn else 'label_en','অবস্থা যাচাই হয়নি' if bn else 'Condition unverified')
            add(f'{name} সম্পর্কে বলি, অবস্থার তথ্য হলো {label}' if bn else f'For {name}, the condition is {label}',f)
        figures=[f for f in facts if f['kind']=='figure' and (f['fact_id'] not in c.spoken_fact_ids or intent in {'bank_condition','bank_figures'})]
        if intent=='bank_figures':figures.sort(key=lambda f:f['values'].get('metric')!='net_profit')
        for f in figures[:2]:add(brief_fact(db,f,bn,c.institution_id),f)
        if intent in {'bank_overview','bank_condition'} and not c.insurance_said:
            f=next((f for f in facts if f['kind']=='insurance'),None)
            if f:add(brief_insurance(db,c.institution_id,bn),f)
        buttons=['detail','services'] if intent in {'bank_overview','bank_condition'} else ['figures','history'] if intent=='bank_reasons' else ['services','ask_bank']
    elif intent=='bank_history':
        for f in [f for f in facts if f['kind']=='history']:
            when=format_date_local(f['values']['event_date'],bn)
            qualifier='খবরে এসেছে' if bn else 'news reports described'
            add(f'{when} {qualifier}, {f["text_bn" if bn else "text_en"]}' if bn else f'In {when}, {qualifier} {f["text_en"]}',f)
            if not f['values']['official']:add('এটি খবরের তথ্য, সরকারিভাবে নিশ্চিত নয়, তাই অবস্থার হিসাবে ধরা হয়নি' if bn else 'This is reported news, not officially confirmed, and is excluded from the condition',f)
        if not rows:add('আমাদের সংগ্রহে এই ব্যাংকের বড় ঘটনার খবর নেই' if bn else 'Our collection has no major incident reports for this bank',None)
    elif intent=='bank_profile':
        for f in [f for f in facts if f['kind']=='profile'][:2]:add(f'{name} সম্পর্কে প্রতিবেদনে {f["values"]["field"]} হিসেবে {f["values"]["value"]} লেখা আছে' if bn else f'The report lists {name}’s {f["values"]["field"]} as {f["values"]["value"]}',f)
        if not rows:add('এই ব্যাংকের প্রোফাইলের নির্ভরযোগ্য উদ্ধৃতি এখনো আমাদের কাছে নেই' if bn else 'We do not yet have a reliable quoted profile for this bank',None)
    elif intent=='services_list':
        products=list(dict.fromkeys(f['values']['product_type'] for f in facts if f['kind']=='service'))
        from ilma_api.answer_wording import PRODUCTS
        names=[PRODUCTS.get(p,(p,p))[0 if bn else 1] for p in products[:4]]
        add(f'{name}ে '+', '.join(names)+' সম্পর্কে প্রকাশিত তথ্য আছে' if bn else f'{name} has published information on '+', '.join(names),None)
        question='কোন সেবা নিয়ে জানতে চান?' if bn else 'Which service would you like to discuss?';buttons=['fdr','dps']
    elif intent=='service_detail':
        selected=[f for f in facts if f['kind']=='service' and f['values']['product_type']==c.product]
        for f in selected[:6]:
            v=f['values'];term=v['tenor_options'] or [v['tenor_min_months'],v['tenor_max_months']]
            term=[t for t in dict.fromkeys(term) if t]
            term_text=', '.join(str(int(t/12))+' বছর' if t%12==0 else str(t)+' মাস' for t in term) if bn else ', '.join(str(int(t/12))+' years' if t%12==0 else str(t)+' months' for t in term)
            text=f'{name}ে {v["product"]}ে {term_text} মেয়াদে হার {v["rate"]}%' if bn else f'{name} quotes {v["rate"]}% for {v["product"]}, for {term_text}'
            if v['dated']:text+=', হারতালিকা '+v['doc_date'] if bn else ', schedule dated '+v['doc_date']
            add(text,f)
        if not rows:add('চাওয়া মেয়াদে এই সেবার হার আমাদের কাছে নেই' if bn else 'We do not have a published quote for this service and requested term',None)
        question='অন্য ব্যাংকের সাথে মিলিয়ে দেখবেন?' if bn else 'Would you like to compare with another bank?';buttons=['compare','services']
    elif intent=='compare':
        facts=comparison or comparison_facts(db,c.institution_id,c.product or 'fdr',c.tenor,c.basis,(),c.network,c.tier)
        for f in facts:
            other=db.get(Institution,f['institution_id']);v=f['values'];label=v.get('status_bn' if bn else 'status_en','অবস্থা যাচাই হয়নি' if bn else 'condition unverified')
            text=f'{bank_name(db,other.id,True)}ে {v["product"]}ে হার {v["rate"]}%, আর {label}' if bn else f'{bank_name(db,other.id,False)} quotes {v["rate"]}% for {v["product"]}, with {label.lower()}'
            if v.get('nearest'):text+=', মেয়াদ আলাদা' if bn else ', at a different term'
            if v['dated']:text+=', তালিকা '+v['doc_date'] if bn else ', schedule '+v['doc_date']
            add(text,f)
        if not rows:add('অন্য ব্যাংকে এই পণ্যের প্রকাশিত তথ্য আমাদের কাছে নেই' if bn else 'We have no published information for this product at another bank',None)
        buttons=['services','ask_bank']
    elif intent=='insurance':
        f=next((f for f in facts if f['kind']=='insurance'),None);add(brief_insurance(db,c.institution_id,bn),f)
        buttons=['ask_bank','end']
    elif intent=='explain_term':add('মূলধন হলো ব্যাংকের নিজের অর্থ, যা ক্ষতি সামলাতে কাজে লাগে' if bn else 'Capital is the bank’s own money, which helps it absorb losses',None)
    if not rows:add('এই তথ্যটি আমাদের কাছে এখনো নেই' if bn else 'We do not have that information yet',None)
    a=HumanReply(intent=intent,bank={'id':c.institution_id,'source':'conversation','mention':None},product=c.product,basis=c.basis,tenor_months=c.tenor,network=c.network,tier=c.tier,compare_banks=[],needs_facts=None,used_fact_ids=list(dict.fromkeys(id for row in ids for id in row)),reply=' '.join(rows),sentence_fact_ids=ids,next_question=question,buttons=buttons,language=c.language)
    a,pending=limit_body(a);result=render(a,c,facts,trace,'template');result['_pending_reply']=pending
    if pending:result['_all_facts']=facts
    return result


def format_date_local(value,bn):
    from ilma_api.rules.reasons import MONTHS_BN
    value=date.fromisoformat(value)
    return f'{value.year} সালের {MONTHS_BN[value.month]} মাসে' if bn else value.strftime('%B %Y')


async def action_turn(selected,text,c,id,memory,packs,banks,db,trace,started,watch_identity):
    if selected=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
    if selected=='more' and memory.get('pending_reply'):
        pending=memory['pending_reply'];a=controls(pending['intent'],c,pending['reply'],pending['next_question'],pending['buttons'])
        a=a.model_copy(update={'sentence_fact_ids':pending['sentence_fact_ids'],'used_fact_ids':list(dict.fromkeys(id for ids in pending['sentence_fact_ids'] for id in ids))})
        facts=memory.get('pending_facts',[]);a,tail=limit_body(a);result=render(a,c,facts,trace,'template')
        if tail:result['_all_facts']=facts
        return await finish(result,'[more]',id,memory,db,started,tail)
    if selected in {'end','stop'}:
        body=('আজ অনেক কথা হলো। আবার জানতে চাইলে মাইক চাপুন।' if c.turn>=20 else 'আবার কিছু জানতে চাইলে মাইক চাপুন।') if c.language=='bn' else 'Tap the microphone whenever you have another question.'
        a=controls('stop',c,body);result=render(a,c,[],trace,'template')
        if selected=='end':result['action']={'type':'end'}
        return await finish(result,'['+selected+']',id,memory,db,started)
    if selected=='report' and c.institution_id:
        result=render(controls('stop',c,'পুরো রিপোর্ট খুলেছি।' if c.language=='bn' else 'I’ve opened the full report.'),c,[],trace,'template');result['action']={'type':'open_report','institution_id':c.institution_id}
        return await finish(result,'[report]',id,memory,db,started)
    if selected=='listen':
        result=render(controls('smalltalk',c,'কী জানতে চান?' if c.language=='bn' else 'What would you like to know?'),c,[],trace,'template')
        return await finish(result,'[listen]',id,memory,db,started)
    mapping={'detail':'bank_reasons','figures':'bank_figures','history':'bank_history','services':'services_list','compare':'compare','insurance':'insurance','ask_bank':'unclear','listen':'unclear'}
    if selected in {'fdr','dps','card','home_loan'}:
        changed=c.product!=selected;c=c.model_copy(update={'product':selected,'tenor':None if changed else c.tenor,'network':c.network if selected=='card' else None,'tier':c.tier if selected=='card' else None});intent='service_detail'
    else:intent=mapping.get(selected,'unclear')
    if selected=='ask_bank':c=c.model_copy(update={'institution_id':None,'product':None,'tenor':None,'network':None,'tier':None})
    if selected.startswith('bank_') and selected[-1].isdigit():
        index=int(selected[-1])-1;peers=memory.get('clarify_candidates') or c.compare_bank_ids
        if index<len(peers):c=c.model_copy(update={'institution_id':peers[index],'product':None,'tenor':None,'network':None,'tier':None});intent='bank_overview'
        memory['clarify_candidates']=[]
    trace.extend([dict(stage='PLAN',model='exact_option',ms=0,status='skipped'),dict(stage='ACT',model='database',ms=0,status='ok'),dict(stage='SAY',model='template',ms=0,status='ok'),dict(stage='CHECK',model='code',ms=0,status='ok')])
    result=await call(db,lambda owned:make_fallback(owned,'',c,packs,banks,trace,intent))
    return await finish(result,text or '['+selected+']',id,memory,db,started,result.pop('_pending_reply',None))
