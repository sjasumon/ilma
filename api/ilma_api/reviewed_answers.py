"""Owner-reviewed public answers bound to exact questions, resolved slots and current facts."""
import copy,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def fingerprint(facts):
    return hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def slots(r):
    return {k:getattr(r,k) for k in ('bank_id','product','tenor','basis','network','tier','intent','compare_bank_ids','requested_field','requested_metric')}

def question_key(text):
    from ilma_api.voice_text import normalize_alias
    from ilma_api.human_memory import redact_user
    return hashlib.sha256(normalize_alias(redact_user(text)).encode()).hexdigest()

def question_keys(text):
    """A spoken question usually has no closing mark, and the stored question may."""
    text=text.strip()
    return {question_key(text+mark) for mark in ('','?','.')}

def has_answer(text,language):
    try:
        data=json.loads((ROOT/'static/audio/answers/manifest.json').read_text())
        keys=question_keys(text)
        return any(v.get('language')==language and keys&set(v.get('question_keys',[])) for v in data['clips'].values())
    except (OSError,ValueError,KeyError):return False

def digits(text):
    return str(text).translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))

def numbers(text):
    """Stated numbers without calendar years; 2.50 and 2.5 are the same figure."""
    values=set()
    for n in re.findall(r'\d+(?:[.,]\d+)*',digits(text)):
        try:values.add(format(float(n.replace(',','')),'g'))
        except ValueError:continue
    return {n for n in values if not re.fullmatch(r'(?:19|20)\d\d',n)}

def stated_numbers(f):
    """The numbers a fact asserts, not the numbers in its product name or source quote."""
    from ilma_api.human_tokens import card_text
    v=f.get('values') or {}
    if f.get('kind')=='service':return numbers(v.get('rate',''))
    if f.get('kind')=='reviewed_evidence':
        raw=v.get('value_num') or v.get('value') or ''
        try:return {format(float(raw),'g'),format(round(float(raw)*100,6),'g')}
        except ValueError:return numbers(raw)
    try:return numbers(card_text(f,'en'))
    except (KeyError,TypeError,ValueError):return set()

STATUS_WORDS=re.compile(r'অবস্থা|ঝুঁকি|condition|\brisk\b',re.I)
AWARD_WORDS=re.compile(r'পুরস্কার|স্বীকৃতি|সেরা|\bnamed\b|\bawards?\b',re.I)
AWARD_CAVEAT=re.compile(r'প্রমাণ নয়|\bnot proof\b',re.I)
UNSPOKEN={'coverage','peer','inventory'}
SENTENCE=r'(?<=[।?!])\s+|(?<=\.)\s+'

def said_in(f,sentence,said,intent):
    kind=f.get('kind')
    if kind=='status':return bool(STATUS_WORDS.search(sentence))
    if kind=='award':return bool(AWARD_WORDS.search(sentence)) and not AWARD_CAVEAT.search(sentence)
    # An incident is matched by its year, and only when the question was about incidents.
    if kind=='history':return intent=='bank_history' and str((f.get('values') or {}).get('event_date',''))[:4] in digits(sentence)
    return bool(stated_numbers(f)&said)

def spoken_lines(body,language,facts,cited,intent):
    """One card line per spoken sentence, carrying only the facts that sentence states."""
    pool=[f for f in {f['fact_id']:f for f in [*facts,*cited]}.values() if f.get('kind') not in UNSPOKEN]
    sentences=[s.strip() for s in re.split(SENTENCE,body.strip()) if s.strip()]
    own={}
    for sentence in sentences:
        said=numbers(sentence);found=[f for f in pool if said_in(f,sentence,said,intent)]
        rates=[f for f in found if f.get('kind')=='service']
        named=[f for f in rates if str((f.get('values') or {}).get('product','')).casefold().split(' ')[-1] in sentence.casefold()]
        own[sentence]=[f for f in found if f.get('kind')!='service']+(named or rates)[:max(2,len(said))]
    kept={f['fact_id'] for row in own.values() for f in row}
    # A declared source or a cited term backs the claim when no sentence quotes its number.
    whole=[f for f in pool if f['fact_id'] not in kept and (f.get('kind')=='reviewed_evidence' or f.get('kind')=='term' and f in cited)]
    if whole and sentences:
        claim=next((s for s in sentences if re.search(r'\d',digits(s))),sentences[0])
        own[claim]=[*own[claim],*whole]
    lines=[dict(text=s,fact_ids=[f['fact_id'] for f in row],source=row[0].get('source',{})) for s,row in own.items() if row]
    public={f['fact_id']:f for row in own.values() for f in row}
    return lines,list(public.values())

def apply(result,user,context,memory):
    if not context:return result
    original=result
    try:
        data=json.loads((ROOT/'static/audio/answers/manifest.json').read_text())
        from ilma_api.reviewed_sources import complete
        if not complete(data):return result
        asked=question_keys(user)|set(context.get('question_keys',[]))
        candidates=[v for v in data['clips'].values() if v.get('language')==result['language'] and asked&set(v.get('question_keys',[])) and v.get('source_sha256')==context['source_sha256'] and v.get('slots')==context['slots']]
        if not candidates:return result
        previous=memory.get('reviewed_answer_key');item=next((v for v in candidates if v['key']!=previous),candidates[0]);text=item['text']
        if hashlib.sha256(text.encode()).hexdigest()!=item['text_sha256']:return result
        tts=item.get('tts_text',text)
        if 'tts_text' in item and (not isinstance(tts,str) or not tts.strip() or hashlib.sha256(tts.encode()).hexdigest()!=item.get('tts_sha256')):return result
        file=item['file']
        if not re.fullmatch(r'(?:bn|en)/q\d{3}\.mp3',file):return result
        path=ROOT/'static/audio/answers'/file
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['audio_sha256']:return result
        matches=list(re.finditer(r'[^।.!?]*\?\s*$',text));question=matches[-1].group().strip() if matches else ''
        body=text[:matches[-1].start()].rstrip() if matches else text
        result=copy.deepcopy(result)
        result['offer_typing']=False;result['conversation']['misses']=0
        if 'conversation_bank_id' in context:result['conversation']['institution_id']=context['conversation_bank_id']
        result.update(text=text,speech=text,speech_text=text,speech_tts=tts,speech_parts=[text],reviewed_answer_key=item['key'],reviewed_source_sha256=context['source_sha256'],reviewed_audio_url='/static/audio/answers/'+file+'?v='+item['audio_sha256'][:16],expects_reply=bool(question))
        result['next']['question']=question
        result['next'].pop('affirmative_action',None);result['next'].pop('negative_action',None)
        service_offer=bool(re.search(r'সার্ভিস|সেবা|\bservices?\b',question,re.I))
        compare_offer=bool(re.search(r'মিলিয়ে|তুলনা|compare',question,re.I))
        detail_offer=bool(re.search(r'আরও.*(?:শুন|জানার)|আর কিছু শুন|hear more|hear anything else|know more|anything else.*(?:know|hear)',question,re.I))
        alternatives=bool(re.search(r' না | or ',question,re.I))
        if not alternatives and (service_offer or compare_offer or detail_offer):
            result['next'].update(affirmative_action='compare' if compare_offer else 'services' if service_offer else 'detail',negative_action='stop')
        values=['compare','services'] if compare_offer and service_offer else ['compare','ask_bank'] if compare_offer else ['services','ask_bank']
        from ilma_api.human_contract import LABELS
        result['next']['options']=[{'value':value,'label':LABELS[value][0 if result['language']=='bn' else 1]} for value in values]
        if context.get('facts'):
            cited=[f for f in original.get('facts',[]) if f.get('fact_id') in set(original.get('speech_fact_ids',[]))]
            lines,public=spoken_lines(body,result['language'],context['facts'],cited,context['slots'].get('intent'))
            result['facts']=public;result['sources']=[f['source'] for f in public if f.get('source')];result['speech_fact_ids']=[f['fact_id'] for f in public];result['conversation']['fact_ids']=result['speech_fact_ids']
            result['sentences']=lines
            result['conversation']['last_spoken_fact_ids']=result['speech_fact_ids']
        resolved_intent=context['slots'].get('intent')
        if resolved_intent:
            from ilma_api.human_contract import STATE
            result['intent']=resolved_intent;result['conversation'].update(last_intent=resolved_intent,state=STATE.get(resolved_intent,result['conversation'].get('state')))
        memory['reviewed_answer_key']=item['key']
        return result
    except (OSError,ValueError,KeyError,TypeError):return original


def refresh_repeat(result):
    """Refresh a stored answer's recording after a release; never replay a stale URL."""
    result=copy.deepcopy(result)
    key=result.get('reviewed_answer_key')
    if not key:return result
    try:
        data=json.loads((ROOT/'static/audio/answers/manifest.json').read_text());item=data['clips'][key]
        from ilma_api.reviewed_sources import complete
        if not complete(data):raise ValueError('Incomplete release')
        if item['text']!=result['speech'] or hashlib.sha256(item['text'].encode()).hexdigest()!=item['text_sha256']:raise ValueError('Changed display text')
        cached_source=result.get('reviewed_source_sha256') or fingerprint({f['fact_id']:f for f in result.get('facts',[])})
        if cached_source!=item['source_sha256'] or (not item.get('context_independent') and item['slots'].get('bank_id')!=result['conversation'].get('institution_id')):raise ValueError('Changed source or bank')
        tts=item.get('tts_text',item['text'])
        if 'tts_text' in item and (not isinstance(tts,str) or not tts.strip() or hashlib.sha256(tts.encode()).hexdigest()!=item.get('tts_sha256')):raise ValueError('Changed spoken script')
        if not re.fullmatch(r'(?:bn|en)/q\d{3}\.mp3',item['file']):raise ValueError('Invalid recording path')
        path=ROOT/'static/audio/answers'/item['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['audio_sha256']:raise ValueError('Changed audio')
        result['reviewed_audio_url']='/static/audio/answers/'+item['file']+'?v='+item['audio_sha256'][:16];result['speech_tts']=tts
    except (OSError,KeyError,ValueError,TypeError):
        result.pop('reviewed_audio_url',None);result.pop('reviewed_answer_key',None)
    return result
