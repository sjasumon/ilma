"""Read-only evidence snapshots for explicitly reviewed question extensions."""
import json
from ilma_api import reviewed_answers as reviewed

def complete(data):
    count=data.get('question_count',93)
    if type(count) is not int or not 1<=count<=999:return False
    expected={f'{language}:q{n:03d}' for language in ('bn','en') for n in range(1,count+1)}
    return data.get('batch_complete') is True and data.get('expected_clips')==len(expected) and set(data.get('clips',{}))==expected

def evidence(db,refs):
    from ilma_api.db import Fact,ServiceOffer,BankIncident,InsuranceRule,BankProfile
    models={'fact':Fact,'service':ServiceOffer,'incident':BankIncident,'insurance':InsuranceRule,'profile':BankProfile}
    rows=[]
    for ref in refs:
        model=models.get(ref['kind'])
        if model is None:raise ValueError('Unsupported reviewed evidence')
        obj=db.get(model,ref['id'])
        if obj is None:raise ValueError('Reviewed evidence missing')
        values={c.name:str(getattr(obj,c.name)) for c in model.__table__.columns if c.name not in {'checked_by','checked_on'}}
        source=getattr(obj,'source',None)
        source_url=values.get('source_url') or (source.url if source else '')
        title=source.title if source else values.get('product',values.get('title_bn','Published bank information'))
        rows.append({'kind':ref['kind'],'id':ref['id'],'values':values,'source':{'source_url':source_url,'source_title':title,'quote':values.get('quote',''),'checked':False}})
    return rows

def context(db,user,r,facts,language=None,previous_bank=None):
    base={'source_sha256':reviewed.fingerprint(facts),'slots':reviewed.slots(r),'facts':list(facts.values()),'question_keys':sorted(reviewed.question_keys(user))}
    # The award an overview opens with is sourced from its own tables, outside the fingerprint.
    if r.intent in {'bank_overview','bank_condition'} and r.bank_id:
        from ilma_api.awards import intro_award,fact
        try:found=intro_award(db,r.bank_id)
        except Exception:found=None  # The awards tables may not be loaded yet.
        if found:base['facts'].append(fact(*found,language))
    try:
        data=json.loads((reviewed.ROOT/'static/audio/answers/manifest.json').read_text())
        if not complete(data):return base
        item=next((v for v in data['clips'].values() if (language is None or v.get('language')==language) and reviewed.question_keys(user)&set(v.get('question_keys',[])) and v.get('source_refs') is not None),None)
        if item is None:return base
        rows=evidence(db,item['source_refs'])
        # Reviewed explicit questions use their declared sources, independently of a previous bank.
        from ilma_api.human_facts import threshold_config
        base['source_sha256']=reviewed.fingerprint({'reviewed_evidence':rows,'thresholds':threshold_config()})
        base['slots']=item['slots']
        base['facts']=[f for f in base['facts'] if f.get('kind')=='term']
        ids={int(row['values'].get('institution_id') or row['values'].get('bank_id')) for row in rows if row['values'].get('institution_id') or row['values'].get('bank_id')}
        target=item.get('conversation_bank_id',previous_bank)
        if 'conversation_bank_id' in item and target not in ids:raise ValueError('Reviewed bank absent from evidence')
        base['conversation_bank_id']=target
        for row in rows:
            quote=row['values'].get('quote') or row['values'].get('value_text','')
            base['facts'].append(dict(fact_id='reviewed:'+row['kind']+':'+row['id'],institution_id=None,kind='reviewed_evidence',values=row['values'],source=row['source'],text_bn=quote,text_en=quote))
        return base
    except (OSError,ValueError,KeyError,TypeError):
        # Never let an incomplete evidence snapshot match a recording.
        return {**base,'source_sha256':'unavailable-reviewed-evidence'}
