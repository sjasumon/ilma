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

def apply(result,user,context,memory):
    if not context:return result
    original=result
    try:
        data=json.loads((ROOT/'static/audio/answers/manifest.json').read_text())
        if not data.get('batch_complete') or data.get('expected_clips')!=186 or len(data.get('clips',{}))!=186:return result
        candidates=[v for v in data['clips'].values() if v.get('language')==result['language'] and question_key(user) in v.get('question_keys',[]) and v.get('source_sha256')==context['source_sha256'] and v.get('slots')==context['slots']]
        if not candidates:return result
        previous=memory.get('reviewed_answer_key');item=next((v for v in candidates if v['key']!=previous),candidates[0]);text=item['text']
        if hashlib.sha256(text.encode()).hexdigest()!=item['text_sha256']:return result
        file=item['file']
        if not re.fullmatch(r'(?:bn|en)/q\d{3}\.mp3',file):return result
        path=ROOT/'static/audio/answers'/file
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['audio_sha256']:return result
        matches=list(re.finditer(r'[^।.!?]*\?\s*$',text));question=matches[-1].group().strip() if matches else ''
        body=text[:matches[-1].start()].rstrip() if matches else text
        result=copy.deepcopy(result)
        result.update(text=text,speech=text,speech_text=text,speech_tts=text,speech_parts=[text],reviewed_answer_key=item['key'],reviewed_audio_url='/static/audio/answers/'+file+'?v='+item['audio_sha256'][:16],expects_reply=bool(question))
        result['next']['question']=question
        if re.search(r'সার্ভিস|সেবা|another service',question,re.I) and not re.search(r' না | or ',question,re.I):
            result['next'].update(affirmative_action='services',negative_action='stop')
        result['next']['options']=[{'value':'services','label':'ব্যাংকের সেবা' if result['language']=='bn' else 'Bank services'},{'value':'ask_bank','label':'অন্য ব্যাংক' if result['language']=='bn' else 'Another bank'}]
        if context.get('facts'):
            from ilma_api.human_tokens import card_text
            public=context['facts'];result['facts']=public;result['sources']=[f['source'] for f in public if f.get('source')];result['speech_fact_ids']=[f['fact_id'] for f in public];result['conversation']['fact_ids']=result['speech_fact_ids']
            result['sentences']=[dict(text=card_text(f,result['language']),fact_ids=[f['fact_id']],source=f.get('source',{})) for f in public]
            result['conversation']['last_spoken_fact_ids']=result['speech_fact_ids']
        resolved_intent=context['slots'].get('intent')
        if resolved_intent:
            from ilma_api.human_contract import STATE
            result['intent']=resolved_intent;result['conversation'].update(last_intent=resolved_intent,state=STATE.get(resolved_intent,result['conversation'].get('state')))
        memory['reviewed_answer_key']=item['key']
        return result
    except (OSError,ValueError,KeyError,TypeError):return original
