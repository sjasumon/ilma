"""Explicit Phase 1 acceptance and response-to-pack consistency checks.

This verifies emitted claims against the current database pack. It does not
replace independent review of the underlying financial source documents.
"""
import re,unicodedata

CONTROL_INTENTS={'smalltalk','stop','out_of_scope','unclear','advice_request','best_bank'}

def normalized(text):
    text=unicodedata.normalize('NFC',text).translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789')).casefold()
    text=re.sub(r'[,;।.!?"“”‘’]+',' ',text)
    return ' '.join(text.split())

def audit_answer(result,canonical,registry):
    from ilma_api.human_checker import sentences,numeric_claims,support_numbers,percent_claims,percent_support
    errors=[];facts=result.get('facts',[]);ids=set(result.get('speech_fact_ids',[]))
    returned={f['fact_id']:f for f in facts}
    if ids!=set(returned):errors.append('spoken_card_fact_ids')
    for fid,fact in returned.items():
        original=canonical.get(fid)
        if not original:errors.append('unknown_fact:'+fid);continue
        for key in ('kind','institution_id','values','source','status'):
            if fact.get(key)!=original.get(key):errors.append('changed_'+key+':'+fid)
    speech=result.get('speech','');question=result.get('next',{}).get('question','')
    if question and speech.endswith(question):speech=speech[:-len(question)].rstrip()
    if result.get('intent') in CONTROL_INTENTS and not facts:
        return {'errors':errors,'facts_checked':0,'sentences_checked':0,'scope':'database_pack'}
    allowed=[]
    for key,item in registry.items():
        if not item.fact_ids or not set(item.fact_ids)<=ids or item.kind=='bank' or key.endswith('.bank'):continue
        # Include only whole clauses, including the sentence-boundary pagination
        # used for a long sourced offer. Never accept arbitrary word prefixes.
        clauses=re.split(r'[,;]\s*',item.text)
        variants={item.text}
        if len(clauses)<=8:
            variants.update(' '.join(clauses[a:b]) for a in range(len(clauses)) for b in range(a+1,len(clauses)+1))
        variants.update(sentences(item.text))
        bank=registry.get('bank:'+str(item.bank_id))
        for value in variants:
            for prefix in ('',bank.text+' ' if bank else '',bank.text+'ের ' if bank else ''):
                allowed.append((normalized(prefix+value),item.fact_ids))
    checked=0
    for sentence in sentences(speech):
        checked+=1;text=normalized(sentence)
        candidates=[fids for value,fids in allowed if text==value]
        if not candidates:
            errors.append('unmatched_spoken_claim');continue
        supported=False
        for fids in candidates:
            evidence=[canonical[fid] for fid in fids if fid in canonical]
            if all(value in support_numbers(evidence) for value in numeric_claims(sentence)) and all(value in percent_support(evidence) for value in percent_claims(sentence)):
                supported=True;break
        if not supported:errors.append('unsupported_number_or_percent')
    return {'errors':list(dict.fromkeys(errors)),'facts_checked':len(facts),'sentences_checked':checked,'scope':'database_pack'}

def gate(summary):
    rows=summary.get('cases',[]);n=len(rows)
    groups={intent:[r for r in rows if r['intent']==intent] for intent in ('compare','correction')}
    group_rate=lambda intent:sum(r['passed'] for r in groups[intent])/max(1,len(groups[intent]))
    checks={
      'complete_corpus':not summary.get('partial',False) and not summary.get('sample',False) and n>=400,
      'runtime_snapshot_identified':bool(re.fullmatch('[0-9a-f]{40}',summary.get('evaluated_commit',''))),
      'runtime_source_unchanged':summary.get('runtime_source_unchanged') is True,
      'both_languages':{r.get('language') for r in rows}>={'bn','en'},
      'overall_90_percent':summary.get('accuracy',0)>=.9,
      'comparisons_90_percent':len(groups['compare'])>=30 and group_rate('compare')>=.9,
      'corrections_90_percent':len(groups['correction'])>=30 and group_rate('correction')>=.9,
      'zero_wrong_banks':summary.get('bank_target_failures',1)==0,
      'zero_slot_failures':summary.get('slot_failures',1)==0,
      'zero_required_fact_failures':summary.get('required_fact_failures',1)==0,
      'zero_protection_leaks':summary.get('unsolicited_protection',1)==0,
      'all_answers_audited':bool(rows) and all('claim_audit' in r for r in rows),
      'zero_claim_audit_errors':bool(rows) and all(not r.get('claim_audit',{}).get('errors',['not_audited']) for r in rows),
      'one_call_90_percent':summary.get('one_call_rate',0)>=.9,
      'first_text_p95_at_most_6_seconds':isinstance(summary.get('p95_ms'),(int,float)) and summary['p95_ms']<=6000}
    return {'passed':all(checks.values()),'checks':checks,'comparison_rate':group_rate('compare'),'correction_rate':group_rate('correction'),'factual_scope':'Current canonical ilma fact pack and code-owned clauses; original-source sign-off is separate.'}

def database_auditor(banks):
    from sqlalchemy.orm import Session
    from ilma_api.db import engine
    from ilma_api.voice_agent import Conversation
    from ilma_api.human_turn import prepare
    if engine.dialect.name!='mysql' or engine.url.database!='ilma':raise RuntimeError('Audit requires only the ilma MySQL database')
    def audit(case,setup,result):
        context=Conversation.model_validate(setup['conversation']).model_copy(update={'language':result['language']})
        with Session(engine) as db:
            _,_,_,_,registry,facts=prepare(db,case['text'],context,banks,forced=result['intent'])
        return audit_answer(result,facts,registry)
    return audit
