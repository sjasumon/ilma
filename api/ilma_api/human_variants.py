"""Fact-bound offline introductions. Database rows contain protocol, never user input."""
import hashlib,json
from datetime import datetime
from sqlalchemy import select
from ilma_api.db import AppVoiceVariant
from ilma_api.human_stream import Draft,Header,SYSTEM
from ilma_api.human_tokens import fill,BANNED,PROTECTION_WORDS,TOKEN
from ilma_api.voice_numbers import pronounce

VERSION='introductions-v2-1'

def fingerprint(payload,registry):
    # Includes sources, values, material-peer clauses, prompt and speech wording.
    data=[VERSION,SYSTEM,payload['language'],payload['intent_hint'],payload['slots'],
          [{k:v for k,v in item.items() if k!='recommended'} for item in payload['tokens']],
          payload.get('fact_revision'),payload['line_choices'],payload['question_choices']]
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()

def checked(draft,payload,decode,registry):
    if draft.error or not draft.header or draft.header.intent!=payload['intent_hint']:return False
    if draft.question not in payload['question_choices'] or not draft.question.endswith('?'):return False
    _,reverse=decode('');used=[reverse.get(fid,fid) for fid in draft.header.used]
    sentences=[];kinds=set();numeric=0;emitted=set()
    import re
    for line in draft.lines:
        if line not in payload['line_choices']:return False
        decoded,_=decode(line)
        try:text,ids=fill(decoded,registry,used)
        except ValueError:return False
        sentences.append(text)
        emitted.update(ids)
        for key in TOKEN.findall(decoded):
            if key in registry:kinds.add(registry[key].kind)
        numeric+=len(re.findall(r'[0-9০-৯]+(?:[.,][0-9০-৯]+)*',text))
    text=' '.join(sentences)+' '+draft.question
    words=len(pronounce(text,payload['language']).split())
    mandatory={reverse.get(fid,fid) for fid in payload.get('required_intro_facts',[])}
    return ('status' in kinds and mandatory<=emitted and 35<=words<=45 and numeric<=1
            and not BANNED.search(text) and not PROTECTION_WORDS.search(text))

def choose(db,key,memory,payload,decode,registry):
    seen=memory.get('intro_variants',{}).get(key,[])
    rows=db.scalars(select(AppVoiceVariant).where(AppVoiceVariant.fingerprint==key)
                    .order_by(AppVoiceVariant.served_count,AppVoiceVariant.ordinal).with_for_update()).all()
    usable=[]
    for row in rows:
        try:draft=Draft(Header.model_validate(row.protocol['header']),row.protocol['lines'],row.protocol['question'])
        except (ValueError,KeyError,TypeError):continue
        if checked(draft,payload,decode,registry):usable.append((row,draft))
    if not usable:return None
    row,draft=next(((row,draft) for row,draft in usable if row.ordinal not in seen),usable[0])
    row.served_count+=1;row.last_served_at=datetime.utcnow()
    history=dict(memory.get('intro_variants',{}));history[key]=[*(seen if len(seen)<len(usable) else []),row.ordinal]
    memory['intro_variants']=dict(list(history.items())[-8:]);db.flush()
    return draft

def store(db,key,ordinal,bank_id,language,intent,draft,model):
    row=db.get(AppVoiceVariant,(key,ordinal))
    if row is None:row=AppVoiceVariant(fingerprint=key,ordinal=ordinal);db.add(row)
    row.bank_id=bank_id;row.language=language;row.intent=intent;row.model=model
    row.protocol={'header':draft.header.model_dump(),'lines':draft.lines,'question':draft.question}
    db.flush()
