"""Shared conversation rendering and memory for the fact-token voice engine."""
import copy,re,time
from ilma_api import settings
from ilma_api.human_contract import HumanReply,STATE,LABELS,ALLOWED
from ilma_api.human_checker import sentences
from ilma_api.human_memory import save,token
from ilma_api.database_tasks import call
from ilma_api.voice_numbers import pronounce

def enabled():return bool(getattr(settings,'HUMAN_VOICE_ENABLED',True) and settings.META_MODEL_API_KEY and 'contributor' not in settings.MUSE_SPARK_MODEL.lower())

def exact_choice(text,c,memory,choice):
    if choice:return choice
    value=' '.join(text.casefold().strip(' .!?,।').split())
    offered=memory.get('last_next',{})
    if offered.get('affirmative_action') and value in {'হ্যাঁ','হ্যা','জি','yes','yeah'}:return offered['affirmative_action']
    if offered.get('negative_action') and value in {'না','no','no thanks'}:return offered['negative_action']
    for option in memory.get('last_next',{}).get('options',[]):
        labels=[option['value'],option['label'],*LABELS.get(option['value'],())]
        if value in (' '.join(label.casefold().strip(' .!?,।').split()) for label in labels):return option['value']
    return None

def guess(text):
    # Used only on provider/checker failure. Free text always reaches Spark first.
    patterns=[('stop',r'^(?:থামুন|থামান|stop)$'),('repeat',r'আবার|পুনরায়|আগের উত্তর|আগের কথা|repeat|again|last answer|previous reply|once more'),('smalltalk',r'হ্যালো|সালাম|ধন্যবাদ|কেমন আছেন|thank|hello|\bhi\b'),
      ('out_of_scope',r'আবহাওয়া|কৌতুক|রান্না|রেসিপি|ক্রিকেট|কবিতা|weather|joke|recipe|poem|cricket'),
      ('advice_request',r'কোথায়.*রাখ|কোন ব্যাংকে.*রাখ|which bank should|recommend|best bank'),
      ('bank_history',r'আগের|অতীত|পূর্ব|ইতিহাস|ঘটনা|ঝামেলা|কেলেঙ্কারি|past|history|scandal|পাস্ট ইভেন্ট'),
      ('compare',r'তুলনা|মিলিয়ে|compare|another bank'),('service_detail',r'এফডিআর|ডিপিএস|\bfdr\b|\bdps\b|কার্ড|loan|সঞ্চয়'),
      ('bank_reasons',r'বিস্তারিত|কারণ|details|why|reasons'),('bank_figures',r'মুনাফা|লোকসান|মূলধন|খেলাপি|figures|profit|capital|rating'),
      ('bank_profile',r'শাখা|প্রতিষ্ঠা|যাত্রা|profile|founded|branches'),('insurance',r'বীমা|বিমা|সুরক্ষা|insurance|বন্ধ হলে'),('services_list',r'সেবা|services'),
      ('bank_condition',r'নিরাপদ|safe'),('bank_overview',r'কেমন|সম্পর্কে|পরিচয়|খোঁজখবর|how|about|introduce|overview')]
    return next((intent for intent,pattern in patterns if re.search(pattern,text,re.I)),'unclear')

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
    if len(options)<2:
        defaults={'BANK':['fdr','dps'],'HISTORY':['services','ask_bank'],'SERVICE':['compare','services'],'COMPARE':['services','ask_bank'],'SERVICES':['fdr','dps'],'ASK_BANK':['listen','ask_bank']}.get(state,['services','ask_bank'])
        for value in defaults:
            if value not in {o['value'] for o in options}:options.append({'value':value,'label':LABELS[value][0 if c.language=='bn' else 1]})
            if len(options)==2:break
    return {'question':answer.next_question,'options':options}

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
    return dict(expects_reply=bool(question),type='agent_turn',intent=answer.intent,language=c.language,offer_typing=c.misses>=2,sentences=[dict(text=f['text_bn' if c.language=='bn' else 'text_en'],fact_ids=[f['fact_id']],source=f['source']) for f in used],facts=used,checked=checked,next=next,conversation=c.model_dump(),action=action,text=speech,speech=speech,speech_tts=pronounce(speech,c.language),speech_format='paragraph',speech_fact_ids=answer.used_fact_ids,sources=[f['source'] for f in used],speech_text=speech,speech_parts=[speech],trace={'steps':trace,'total_ms':0,'status_rule_notice':'ব্যাংকের অবস্থা তথ্যভিত্তিক নিয়মে ঠিক হয়।' if c.language=='bn' else 'Bank conditions come from sourced rules.'},omit_history=False)

def controls(intent,c,body,question='',buttons=()):
    return HumanReply(intent=intent,bank={'id':c.institution_id,'source':'conversation','mention':None},product=c.product,basis=c.basis,tenor_months=c.tenor,network=c.network,tier=c.tier,compare_banks=[],needs_facts=None,used_fact_ids=[],reply=body,sentence_fact_ids=[[] for _ in sentences(body)],next_question=question,buttons=list(buttons),language=c.language or 'bn')

async def run(text,context,banks,db,candidates=(),choice=None,watch_identity=None,client=None,device_hash=None,on_sentence=None):
    from ilma_api.human_turn import run as token_turn
    return await token_turn(text,context,banks,db,candidates,choice,watch_identity,client,device_hash,on_sentence)

async def finish(result,user,id,memory,db,started,pending=None):
    from ilma_api.reviewed_answers import apply as apply_reviewed
    result=apply_reviewed(result,user,memory.pop('_reviewed_context',None),memory)
    if result.get('reviewed_answer_key'):pending=None
    result['conversation']['conversation_token']=token(id);result['trace']['total_ms']=round((time.monotonic()-started)*1000)
    pending_facts=result.pop('_all_facts',result['facts']) if pending else []
    # Resolved slots and checked replies retain context without saving names or
    # arbitrary words accidentally spoken into the microphone.
    stored_user='[user input redacted]'
    result['protocol']=memory.get('protocol',2)
    prior=[{**turn,'user':stored_user} for turn in memory.get('last_turns',[])]
    saved={**memory,'conversation':result['conversation'],'last_turns':[*prior,dict(user=stored_user,reply=result['speech'],intent=result.get('intent'),bank_id=result['conversation']['institution_id'],fact_ids=result['speech_fact_ids'])][-4:],
           'last_result':{key:copy.deepcopy(value) for key,value in result.items() if key not in {'trace','speech_parts','speech_text','memory_turn'}},'last_next':result['next'],'pending_reply':pending,'pending_facts':pending_facts}
    await call(db,lambda owned:save(owned,id,saved))
    result['memory_turn']={'question':stored_user,'answer':result['speech']}
    return result

async def repeat_turn(c,id,memory,db,trace,started):
    result=copy.deepcopy(memory['last_result']);result.update(speech_text=result['speech'],speech_parts=[result['speech']],trace={'steps':trace,'total_ms':round((time.monotonic()-started)*1000),'status_rule_notice':'Repeated checked reply.'})
    result['intent']='repeat'
    result['conversation']['turn']=min(20,c.turn+1)
    if memory.get('pending_reply'):result['_all_facts']=memory.get('pending_facts',result['facts'])
    return await finish(result,'[repeat]',id,memory,db,started,memory.get('pending_reply'))
