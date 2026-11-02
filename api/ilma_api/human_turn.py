"""Resolved, single-call token turns with local sentence repair and sourced cards."""
import asyncio,copy,hashlib,json,re,time,uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
from ilma_api import settings
from ilma_api.database_tasks import call
from ilma_api.human_memory import load,redact_user,save,token
from ilma_api.human_resolver import resolve,is_banglish
from ilma_api import human_answers as answers
from ilma_api.human_tokens import build_registry,fill,TOKEN,FactToken,card_text,material,BANNED,PROTECTION_WORDS,PRODUCTS as PRODUCT_LABEL,number as number_text,product as product_name,term as term_text,GENERIC
from ilma_api.human_stream import generate
from ilma_api.human_facts import fact_pack,service_facts,comparison_facts,term_facts,card_waiver,manual_notes
from ilma_api.human_contract import STATE,LABELS,ALLOWED
from ilma_api.voice_numbers import pronounce
from ilma_api.rules.reasons import format_date
from ilma_api.db import AppModelCall

def variant(key,c,count=5):
    return int(hashlib.sha256(f'{key}:{c.turn}:{c.institution_id}'.encode()).hexdigest()[:8],16)%count

def next_steps(intent,c,key,more=False):
    bn=c.language=='bn'
    if more:return ('আরও শুনবেন?' if bn else 'Would you like to hear more?'),['more','end']
    if intent in {'bank_overview','bank_condition','services_list','advice_request','best_bank'}:
        return '',['services','ask_bank']
    if intent=='bank_reasons':return ('আর্থিক হিসাব, না আগের ঘটনা শুনবেন?' if bn else 'Would you like financial figures or past events?'),['figures','history']
    if intent=='service_detail':return '',['compare','services']
    if intent in {'unclear','out_of_scope'}:return ('আবার বলবেন, না অন্য ব্যাংক দেখবেন?' if bn else 'Ask again, or choose another bank?'),['listen','ask_bank']
    return '',['services','ask_bank']


def details(facts,bank):
    return {f['values']['field']:f for f in facts.values() if f['kind']=='profile_detail' and f['institution_id']==bank}

def interim_token(facts,bank,bn):
    """A part-year bad-loan figure is said beside the annual one, with its own period."""
    found=details(facts,bank).get('interim_npl')
    if not found:return {}
    end=date.fromisoformat(found['values']['as_of'])
    return {'asked:interim':FactToken(f"{end.year} সালের প্রথম {end.month} মাসে হার {found['values']['value']}%" if bn else f"For the first {end.month} months of {end.year}, it is {found['values']['value']}%",(found['fact_id'],),bank,'figure')}

def founding_tokens(d,bank,bn):
    tokens={}
    if 'founded_date' in d:
        when=format_date(d['founded_date']['values']['value'],bn)
        tokens['asked:founded']=FactToken(f'{when} সালে প্রতিষ্ঠিত হয়' if bn else f'was founded on {when}',(d['founded_date']['fact_id'],),bank,'profile')
    name=d.get('founder_bn' if bn else 'founder')
    if name:tokens['asked:founder']=FactToken(f"ব্যাংকটি প্রতিষ্ঠা করেন {name['values']['value']}" if bn else f"Its founder is {name['values']['value']}",(name['fact_id'],),bank,'profile')
    return tokens

def note_tokens(notes,product,bank,bn):
    ids=tuple(n['fact_id'] for n in notes);ranges=[n for n in notes if n['values']['attribute']=='rate_range']
    label=PRODUCT_LABEL.get(product,('সেবা','service'))
    if ranges:
        low,high=ranges[0]['values']['value_text'].split('-')
        return {'note:product':FactToken(f'{label[0]}ের সুদ মেয়াদের ওপর ভিত্তি করে {low}% থেকে {high}%' if bn else f'{label[1]} rates run from {low}% to {high}% by term',ids,bank,'service_note')}
    def scheme(n):
        when=term_text(n['values'],bn);name=n['values']['value_text' if bn else 'product']
        return name+((f' {when} মেয়াদে' if bn else f' for {when}') if when else '')
    return {'note:product':FactToken((f'{label[0]} স্কিম: ' if bn else f'{label[1]} schemes: ')+', '.join(scheme(n) for n in notes),ids,bank,'service_note'),
     'note:norate':FactToken('এগুলোর সুদের হার আমাদের কাছে নেই' if bn else 'We do not have their rates',(),bank,'gap')}

GROUPS={'retail':('রিটেইল ব্যাংকিং','retail banking'),'sme':('এসএমই ব্যাংকিং','SME banking'),'corporate':('কর্পোরেট ও বাণিজ্যিক সেবা','corporate and commercial services'),'loans':('ঋণ সেবা','loans'),'cards':('কার্ড সেবা','cards'),'digital':('ডিজিটাল ব্যাংকিং','digital banking')}
def group_line(d,name,bn):
    found=d.get('service_groups')
    if not found:return None
    words=[GROUPS[k][0 if bn else 1] for k in found['values']['value'].split(',') if k in GROUPS]
    return ((f'{name} প্রধানত এই সেবাগুলো দেয়: ' if bn else f'{name} mainly offers ')+', '.join(words)+('।' if bn else '.'),[found['fact_id']])

def interim_line(d,bn):
    """Figures for part of a year always carry their period; annual figures stay as they are."""
    profit,change,npl=(d.get('interim_'+k) for k in ('net_profit','profit_change','npl'))
    if not (profit and change and npl):return None
    end=date.fromisoformat(profit['values']['as_of']);v=lambda f:f['values']['value']
    text=f"{end.year} সালের প্রথম {end.month} মাসে সমন্বিত নিট মুনাফা {v(change)}% বেড়ে {int(v(profit)):,} কোটি টাকা, খেলাপি ঋণের হার {v(npl)}%।" if bn else f"For the first {end.month} months of {end.year}, consolidated net profit rose {v(change)}% to {int(v(profit)):,} crore taka, and bad loans were {v(npl)}%."
    return (text,[profit['fact_id'],change['fact_id'],npl['fact_id']])

def prepare(db,text,c,banks,forced=None,resolved=None):
    r=resolved or resolve(text,c,banks)
    if forced:r=replace(r,intent=forced,direct_protection=forced=='insurance')
    if r.intent=='compare' and r.product is None and len(r.compare_bank_ids)<2:r=replace(r,product='fdr')
    # A deposit comparison defaults to one year, not the shortest published term.
    if r.intent=='compare' and r.tenor is None and r.product in {'fdr','dps'}:r=replace(r,tenor=12)
    if r.bank_id is not None and not any(b['id']==r.bank_id for b in banks):r=replace(r,bank_id=None)
    c=c.model_copy(update={'institution_id':r.bank_id,'product':r.product,'tenor':r.tenor,'basis':r.basis,'network':r.network,'tier':r.tier})
    ids=list(dict.fromkeys(([r.bank_id] if r.bank_id else [])+r.compare_bank_ids))
    packs=[]
    for id in ids:
        p=fact_pack(db,id,None,None,r.basis)
        p['facts']=[f for f in p['facts'] if f['kind']!='service']+service_facts(db,id,None,None,r.basis,include_all=True)
        p['facts'].extend(term_facts(text));packs.append(p)
    if not packs:packs=[{'bank':None,'facts':term_facts(text),'status':None}]
    comparisons=comparison_facts(db,r.bank_id,r.product or 'fdr',r.tenor,r.basis,r.compare_bank_ids,r.network,r.tier) if r.intent=='compare' and r.product else []
    if comparisons and r.tenor is None:
        reference=comparisons[0]['values'].get('comparison_term')
        if reference:c=c.model_copy(update={'tenor':reference});r=replace(r,tenor=reference)
    registry,facts=build_registry(packs,comparisons,c.language,r.direct_protection)
    if r.requested_metric and r.intent=='bank_figures':
        requested=next((f for f in facts.values() if f['institution_id']==r.bank_id and f['kind']=='figure' and f['values'].get('metric')==r.requested_metric),None)
        bn=c.language=='bn';status=bank_status(facts,r.bank_id)
        if not requested:registry.update(answers.metric_gap(r.requested_metric,r.bank_id,bn))
        elif r.requested_metric=='net_profit':registry.update(answers.profit_tokens(db,requested,facts,r.bank_id,bn))
        elif r.requested_metric=='npl_ratio':
            registry.update(answers.loan_tokens(db,requested,facts,r.bank_id,bn,status))
            registry.update(interim_token(facts,r.bank_id,bn))
        elif r.requested_metric=='rating':registry.update(answers.rating_tokens(requested,facts,r.bank_id,bn,status))
        else:
            registry['asked:figure']=registry['value:'+requested['fact_id']]
            if 'f:'+requested['fact_id'] in registry:registry['asked:meaning']=registry['f:'+requested['fact_id']]
    if r.requested_field=='founded_year':registry.update(founding_tokens(details(facts,r.bank_id),r.bank_id,c.language=='bn'))
    if r.requested_field:
        profiles=[f for f in facts.values() if f['kind']=='profile' and f['institution_id']==r.bank_id]
        for f in profiles:
            if f['values']['field']!=r.requested_field:
                registry.pop('f:'+f['fact_id'],None);registry.pop('value:'+f['fact_id'],None)
        if not any(f['values']['field']==r.requested_field for f in profiles):
            gap=next((f for f in facts.values() if f['kind']=='coverage' and f['institution_id']==r.bank_id),None)
            if gap:registry['gap:profile']=registry['f:'+gap['fact_id']]
    offers=[f for f in facts.values() if f['kind']=='service' and f['institution_id']==r.bank_id and f['values']['product_type']==r.product]
    if r.intent=='service_detail' and r.product=='card' and r.tier and r.bank_id:
        note=card_waiver(db,r.bank_id,r.network,r.tier)
        if note:
            facts[note['fact_id']]=note
            registry['note:waiver']=FactToken(note['text_bn' if c.language=='bn' else 'text_en'],(note['fact_id'],),r.bank_id,'service_note')
    notes=manual_notes(db,r.bank_id,r.product) if r.product and not offers and r.bank_id else []
    if notes:
        facts.update((n['fact_id'],n) for n in notes)
        registry.update(note_tokens(notes,r.product,r.bank_id,c.language=='bn'))
    if r.product and not offers and r.bank_id and not notes and not any(f['kind']=='inventory' and f['institution_id']==r.bank_id for f in facts.values()):
        label=PRODUCT_LABEL.get(r.product,('এই সেবা','this service'))
        word=('মুনাফার হার','profit rate') if r.basis=='islamic' else ('সুদের হার','rate')
        registry['gap:product']=FactToken(f'{label[0]}ের {word[0]} আমাদের কাছে এখনো নেই, তাই অনুমান করে কিছু বলছি না' if c.language=='bn' else f'{label[1]} {word[1]} is not in our collection yet, so I will not guess',(),r.bank_id,'gap')
    elif r.product and not offers and r.bank_id and not notes:
        proof=next((f for f in facts.values() if f['kind']=='inventory' and f['institution_id']==r.bank_id),None)
        if proof:
            from ilma_api.human_tokens import PRODUCTS as LABEL
            label=LABEL.get(r.product,('এই সেবা','this service'))
            phrase=f'{label[0]}ের প্রকাশিত তথ্য এখনো আমাদের কাছে নেই' if c.language=='bn' else f'published {label[1]} information is not yet in our collection'
            fid='coverage:product:'+str(r.bank_id)+':'+r.product
            facts[fid]={'fact_id':fid,'institution_id':r.bank_id,'kind':'coverage','text_bn':phrase if c.language=='bn' else 'এই সেবার তথ্য আমাদের সংগ্রহে নেই','text_en':phrase if c.language=='en' else 'This service is absent from the imported collection','values':{'product_type':r.product},'source':{**proof['source'],'quote':'Derived coverage of imported product rows, not a claim that the bank does not offer this service'}}
            registry['gap:product']=FactToken(phrase,(fid,),r.bank_id,'gap')
    if r.intent=='service_detail' and r.product=='card' and r.fee=='late_fee':registry['meta:late']=FactToken('')
    if r.intent=='compare' and r.product is None and len(r.compare_bank_ids)>=2:
        bn=c.language=='bn'
        for index,bank in enumerate(r.compare_bank_ids):
            name=registry.get('bank:'+str(bank))
            status=next((f for f in facts.values() if f['kind']=='status' and f.get('institution_id')==bank),None)
            if not name or not status:continue
            code=bank_status(facts,bank)
            condition={'strong':('অবস্থা ভালো','is in good condition'),'watch':('কিছু সতর্কতার লক্ষণ আছে','has some warning signs'),'high':('ঝুঁকি বেশি','is high risk'),'no_data':('অবস্থা যাচাইয়ের তথ্য কম','has insufficient information for an assessment')}.get(code,('অবস্থা যাচাইয়ের তথ্য কম','has insufficient information for an assessment'))
            text=f'{name.text}ের {condition[0]}।' if bn else f'{name.text} {condition[1]}.'
            ids=[status['fact_id']]
            loans=answers.figure(facts,bank,'npl_ratio')
            if loans:
                value=answers.percent(loans['values']['value']);year=loans['values']['period_end'][:4]
                text+=(f' {year} সালের হিসাবে খেলাপি ঋণ {value}%।' if bn else f' Its bad loans were {value}% in {year}.')
                ids.append(loans['fact_id'])
            registry['cmp:'+str(index)]=FactToken(text,tuple(ids),bank,'comparison')
    if r.intent=='compare' and not r.term_asked and not r.correction and r.product in {'fdr','dps'} and len(r.compare_bank_ids)==2:
        pair=[]
        for id in r.compare_bank_ids:
            rows=service_facts(db,id,r.product,None,r.basis,include_all=True)
            if rows and 'bank:'+str(id) in registry:pair.append((registry['bank:'+str(id)].text,rows))
        if len(pair)==2:
            whose=(lambda name:polish(name+'ের ',{},True)) if c.language=='bn' else (lambda name:name+"'s ")
            registry.update(answers.compare_tokens(pair[0],pair[1],PRODUCT_LABEL[r.product],whose,[bank_status(facts,id) for id in r.compare_bank_ids],c.language=='bn'))
    if r.intent=='compare' and r.product:
        # Name each compared bank that lacks the product; the others keep their rows.
        from ilma_api.human_tokens import PRODUCTS as LABEL
        label=LABEL.get(r.product,('এই সেবা','this service'))
        present={f['institution_id'] for f in comparisons}
        for bank_id in ids:
            if bank_id in present or 'bank:'+str(bank_id) not in registry:continue
            phrase=f'{label[0]}ের প্রকাশিত তথ্য এখনো আমাদের কাছে নেই' if c.language=='bn' else f'published {label[1]} information is not yet in our collection'
            ranges=[n for n in manual_notes(db,bank_id,r.product) if n['values']['attribute']=='rate_range']
            if ranges:
                # A stored range is said beside the other bank's rate, not "no data".
                facts.update((n['fact_id'],n) for n in ranges)
                registry['gap:compare:'+str(bank_id)]=note_tokens(ranges,r.product,bank_id,c.language=='bn')['note:product']
                if r.tenor:
                    # A term rate beside a range of terms is not like for like: say so.
                    from ilma_api.human_tokens import term
                    when=term({},c.language=='bn',r.tenor);low,high=ranges[0]['values']['value_text'].split('-')
                    text=f'{label[0]}ের {when} মেয়াদের হার আমাদের কাছে নেই; মেয়াদভেদে সুদ {low}% থেকে {high}%' if c.language=='bn' else f'has no {when.replace(" ","-")} {label[1]} rate in our data; across terms it publishes {low}% to {high}%'
                    registry['gap:compare:'+str(bank_id)]=FactToken(text,registry['gap:compare:'+str(bank_id)].fact_ids,bank_id,'service_note')
                registry['meta:range']=FactToken('')
                continue
            fid='coverage:compare:'+str(bank_id)+':'+r.product
            facts[fid]={'fact_id':fid,'institution_id':bank_id,'kind':'coverage','text_bn':phrase if c.language=='bn' else label[0]+'ের তথ্য আমাদের কাছে নেই','text_en':phrase if c.language=='en' else 'Published '+label[1]+' information is not in our collection','values':{'product_type':r.product},'source':{'source_title':'ILMA collection coverage','source_url':'','quote':''}}
            registry['gap:compare:'+str(bank_id)]=FactToken(phrase,(fid,),bank_id,'gap')
    if r.tenor is not None and r.product in {'fdr','dps'} and offers and not any(not f['values'].get('nearest') and matches(f['values'],r.tenor) for f in offers):
        from ilma_api.human_tokens import term
        when=term({},c.language=='bn',r.tenor)
        phrase=f'{when} মেয়াদের এই সেবার তথ্য আমাদের কাছে নেই' if c.language=='bn' else f'We have no published quote for this service over {when}'
        fid='coverage:term:'+str(r.bank_id)+':'+str(r.product)+':'+str(r.tenor)
        facts[fid]={'fact_id':fid,'institution_id':r.bank_id,'kind':'coverage','text_bn':phrase if c.language=='bn' else 'চাওয়া মেয়াদের তথ্য আমাদের সংগ্রহে নেই','text_en':phrase if c.language=='en' else 'The requested term is absent from our imported collection','values':{'product_type':r.product,'asked_tenor':r.tenor},'source':{'kind':'computed','source_url':offers[0]['source']['source_url'],'source_title':'Published term coverage','quote':'Derived coverage of imported product terms, not a statement that the bank does not offer the product','inputs':[f['source'] for f in offers]}}
        registry['gap:term']=FactToken(phrase,(fid,),r.bank_id,'gap')
    return r,c,packs,comparisons,registry,facts

# Joins a bank name to a clause that does not start with a verb, after all checks.
EN_VERB=re.compile(r"(?:is|has|have|was|shows|currently|holds|reported|does|offers|gives|pays)\b")
def polish(sentence,registry,bn):
    if bn:
        # After a vowel sign the endings are র/য়: "ব্যাংক এশিয়ার", "ব্যাংক এশিয়ায়".
        sentence=re.sub(r'([\u09be-\u09cc])ের(?=[\s,।.?]|$)',r'\1র',sentence)
        sentence=re.sub(r'([\u09be-\u09cc])ে(?=[\s,।.?]|$)',r'\1য়',sentence)
    for token in registry.values():
        if token.kind!='bank' or not sentence.startswith(token.text+' '):continue
        name=token.text;rest=sentence[len(name)+1:]
        if bn:
            if rest.startswith('একই ব্যাংকের '):return polish(name+'ে '+rest[len('একই ব্যাংকের '):],{},bn)
            if rest.startswith('প্রকাশিত সেবার ধরন '):return polish(name+'ের প্রকাশিত সেবার ধরন: '+rest[len('প্রকাশিত সেবার ধরন '):],{},bn)
            if re.match(r'(?:এই|প্রকাশিত)\s|\S+ের\s',rest):return polish(name+'ের '+rest,{},bn)
        else:
            if rest.startswith(name+' '):rest=rest[len(name)+1:]
            if rest.startswith('The '):return name+"'s "+rest[4:]
            if rest.startswith('published '):return name+"'s "+rest
            if rest.startswith(('Net ','Bad ','Credit ')):return name+"'s "+rest[0].lower()+rest[1:]
            if rest[:1].isupper() and not EN_VERB.match(rest.lower()):return name+"'s "+rest
        return sentence
    return sentence

def bank_status(facts,bank_id):
    for f in facts.values():
        if f.get('kind')=='status' and f.get('institution_id')==bank_id:
            return f.get('status',{}).get('code') or f.get('values',{}).get('status','no_data')
    return 'no_data'

def introduction(db,c,registry,facts,dated=False):
    """First answer about a strong bank: name, founding year if quoted, and one confirmed award."""
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    if not name or bank_status(facts,c.institution_id)!='strong':return [],{}
    founded=next((f for f in facts.values() if f.get('kind')=='profile' and f.get('institution_id')==c.institution_id and f['values'].get('field')=='founded_year'),None)
    from ilma_api.awards import intro_award,phrase,fact,DISCLAIMER
    try:found=intro_award(db,c.institution_id)
    except Exception:found=None  # The awards tables may not be loaded yet.
    # A dated result is the news in that answer, so the founding year opens it.
    if found and not dated:
        award,awarder,sources=found;item=fact(award,awarder,sources,c.language)
        return [(phrase(award,awarder,c.language,name.text),[item['fact_id']]),(('তবে ' if bn else '')+DISCLAIMER[0 if bn else 1],[])],{item['fact_id']:item}
    if not founded:return [],{}
    year=str(founded['values']['value'])
    text=f"{name.text} যাত্রা শুরু করে {year.translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯'))} সালে।" if bn else f"{name.text} was established in {year}."
    return [(text,[founded['fact_id']])],{}

def award_answer(db,c,registry,facts):
    from ilma_api.awards import rows,phrase,fact,HIGH_RISK,DISCLAIMER,leading_first,medal_line
    from ilma_api.report_card import get_institution_report_card
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    label=name.text if name else ''
    # Awards the awarder itself confirms come first; news reports only fill an empty list.
    try:found=leading_first(rows(db,c.institution_id,('awarder_confirmed',)) or rows(db,c.institution_id))[:3]
    except Exception:found=[]
    lines=[];items=[]
    for index,(award,awarder,sources) in enumerate(found):
        item=fact(award,awarder,sources,c.language);items.append(item)
        lines.append((phrase(award,awarder,c.language,label if index==0 else None),[item['fact_id']]))
    merged=medal_line(found,label,bn)
    if merged:lines=[(merged,[f for _,ids in lines for f in ids])]
    if not lines:lines.append((polish(label+'ের ',{},True)+'যাচাই করা কোনো পুরস্কারের তথ্য আমাদের কাছে নেই।' if bn else f"We have no verified award information for {label}.",[]))
    status=((get_institution_report_card(db,c.institution_id) or {}).get('status') or {}).get('code')
    if status=='high' and found:lines.append((HIGH_RISK[0 if bn else 1],[]))
    elif found:
        lines.append((('তবে ' if bn else '')+DISCLAIMER[0 if bn else 1],[]))
        loans=answers.figure(facts,c.institution_id,'npl_ratio')
        if loans and loans['values']['value']>=answers.LOW_LOANS:lines.append(((f"ব্যাংকটির খেলাপি ঋণ {answers.percent(loans['values']['value'])}%।" if bn else f"Its bad loans are {answers.percent(loans['values']['value'])}%."),[loans['fact_id']]))
    return lines,items

RATE_LINE=re.compile(r'^(?P<head>.*?)(?P<product>(?<!\S)(?!থেকে)\S+ে) (?P<term>(?:[০-৯\d., ]+ (?:থেকে|বা) )?[০-৯\d.]+ (?:বছর|মাস)) মেয়াদে (?P<label>সুদ|আনুমানিক মুনাফা) (?P<rate>[০-৯\d.]+%)।$')
def merge_rates(lines,facts,banks=()):
    """Say the product once: "ডিপিএসে ১ বছরে সুদ ৭%, ৩ বছরে ৭.৫%।"; a term's meaning is named."""
    from ilma_api.human_tokens import PRODUCTS as LABEL
    output=[]
    for sentence,ids in lines:
        found=RATE_LINE.match(sentence)
        previous=output[-1] if output else None
        # Only one plain product per sentence: the earlier head is just a bank name, and terms differ.
        plain=lambda head:head=='' or any(head==polish(b+'ের ',{},True) for b in banks)
        if found and previous and previous[2] and plain(previous[2]['head']) and previous[2]['product']==found['product'] and previous[2]['label']==found['label'] and not found['head'] and found['term'] not in previous[2]['terms']:
            text=previous[0].rstrip('।')+f", {found['term']}ে {found['rate']}।"
            output[-1]=(text,previous[1]+[i for i in ids if i not in previous[1]],{**previous[2],'terms':previous[2]['terms']+[found['term']]})
            continue
        if found:sentence=f"{found['head']}{found['product']} {found['term']}ে {found['label']} {found['rate']}।"
        general=bool(ids) and all(facts.get(i,{}).get('kind')=='term' for i in ids)
        if general and output:
            alias=ids[0].split(':',1)[-1]
            word=LABEL.get(alias,(None,))[0]
            if word and not sentence.startswith(word):sentence=f'{word} মানে {sentence}'
        output.append((sentence,list(ids),{**found.groupdict(),'terms':[found['term']]} if found else None))
    return [(s,ids) for s,ids,_ in output]

COUNTS={2:('দু','two'),3:('তিন','three'),4:('চার','four')}
ASKS_FIGURE=re.compile(r'সুদ|হার|রেট|মুনাফা|ফি(?=[\s,।?]|$)|কত|\bkoto\b|rates?\b|interest|profit|\bfees?\b|charges?\b',re.I)
ASKS_OPINION=re.compile(r'ভালো|ভাল(?=[\s,।?]|$)|লাভজনক|\bgood\b|\bworth\b|\bbetter\b|suitable|\boption\b',re.I)
def service_lines(text,lines,c,r,registry,facts):
    """Open a product answer as asked: what it is, how its rates vary, or that the choice is the user's."""
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    rows=[facts[i] for _,ids in lines for i in ids if facts.get(i,{}).get('kind')=='service']
    if not name or not rows:return lines
    # An opinion question gets the terms people compare, not the one-month rate.
    if ASKS_OPINION.search(text) and r.product=='fdr' and any((f['values'].get('selected_tenor') or 0)>=3 for f in rows):rows=[f for f in rows if (f['values'].get('selected_tenor') or 12)>=3]
    if r.product=='savings':return answers.savings_lines(rows,polish(name.text+'ের ',{},True) if bn else name.text+"'s ",bn,lambda v:product_name(v,bn),r.follow)
    terms=[row for row in lines if row[1] and all(facts.get(i,{}).get('kind')=='term' for i in row[1])]
    lines=[row for row in lines if row not in terms]
    whose=polish(name.text+'ের ',{},True) if bn else name.text+"'s "
    v=rows[0]['values'];card=r.product=='card';label=PRODUCT_LABEL.get(r.product,('সেবা','service'))
    deposit=r.product in {'fdr','dps'}
    amounts=sorted({f['values']['rate'] for f in rows if f['values'].get('rate') is not None})
    lead=[];frame=[];closing=[];late='meta:late' in registry
    if card and len(rows)>1 and not late and not getattr(r,'tier',None) and not getattr(r,'network',None) and not ASKS_FIGURE.search(text) and not ASKS_OPINION.search(text):
        # "Tell me about X's cards" names the cards first; fees are one choice away.
        return [card_overview(rows,whose,name.text,bn)]
    opinion=bool(ASKS_OPINION.search(text))
    if not opinion and deposit and not r.tenor and not r.follow and not ASKS_FIGURE.search(text):
        word=next((facts[i] for row in terms for i in row[1]),None) or next((f for f in facts.values() if f.get('kind')=='term' and f['fact_id'].split(':',1)[-1].casefold() in {label[1].casefold(),label[0]}),None)
        if word:
            meaning=word['text_bn' if bn else 'text_en'].rstrip('।.')
            many=len({product_name(f['values'],True) for f in rows})  # Bangla names are the scheme key in both languages
            if many in COUNTS:
                # Two to four schemes: say how many (a longer count is usually terms stored as products), then what the word means after the rates.
                short=re.sub(r'জমানোর স্কিম$','জমানো',meaning) if bn else re.sub(r'^A scheme for ','',meaning)
                counted=COUNTS[many]
                lead.append((f'{whose}{counted[0]}টি {label[0]} আছে।' if bn else f"{name.text} has {counted[1]} {label[1]} schemes.",[]))
                closing=[((f'{label[0]} মানে {short}।' if bn else f'{label[1]} means {short[:1].lower()+short[1:]}.'),[word['fact_id']])]
            else:lead.append(((f'{label[0]} মানে {meaning}।' if bn else f'{label[1]} means {meaning[:1].lower()+meaning[1:]}.'),[word['fact_id']]))
    if not lead and not opinion and not late and not r.follow and not r.tenor and len(rows)>1 and len(amounts)>1 and (deposit or card):
        schemes=len({product_name(f['values'],True) for f in rows})>1
        profit=v.get('basis')=='islamic'
        if card:frame=[(f'{whose}কার্ডের বার্ষিক ফি কার্ডের ধরন অনুযায়ী আলাদা।' if bn else f'{whose}annual fees vary by card.',[])]
        elif schemes:
            low,high=number_text(amounts[0]),number_text(amounts[-1])
            frame=[(f"{whose}{label[0]}ের {'আনুমানিক মুনাফা' if profit else 'সুদ'} মেয়াদ ও স্কিমভেদে {low}% থেকে {high}%।" if bn else f"{whose}{label[1]} {'profit rates' if profit else 'rates'} run from {low}% to {high}% by scheme and term.",[f['fact_id'] for f in rows])]
        else:frame=[(f"{whose}{label[0]}ের {'আনুমানিক মুনাফা' if profit else 'সুদ'} মেয়াদের ওপর নির্ভর করে।" if bn else f"{whose}{label[1]} {'profit rates' if profit else 'rates'} depend on the term.",[])]
    others=[row for row in lines if not any(facts.get(i,{}).get('kind')=='service' for i in row[1])]
    if card and len(rows)>1:lines=[fee_list(rows,whose,bn,late),*others]
    elif deposit and len(rows)>1 and len(amounts)==1 and not r.tenor and not any(f['values'].get('dated') for f in rows):lines=[one_rate(rows,whose,bn),*others]
    elif deposit and len(rows)>1 and not r.tenor and not any(f['values'].get('dated') for f in rows):lines=[*grouped_rates(rows,name.text,whose,bn,r.product,bool(lead) and not terms_first(lead)),*others]
    if len(rows)>1 and r.tenor:lines=standard_named(lines,facts,bn)
    conditions=[re.search(r'(\d+)% VAT',f['source'].get('condition') or '') for f in rows]
    if card and all(conditions):lines=[*lines,(f'এর সঙ্গে {conditions[0][1]}% ভ্যাট যোগ হতে পারে।' if bn else f'{conditions[0][1]}% VAT may apply.',[rows[0]['fact_id']])]
    # The framing sentence says no more than the list, so the list keeps the room.
    said=' '.join(s for s,_ in [*lead,*frame,*(merge_rates(lines,facts,[name.text]) if bn else lines)])
    if len(pronounce(said+' '+next_steps('service_detail',c,0)[0],c.language).split())>LIST_WORDS:frame=[]
    if frame and card and len(rows)>1:
        head=lines[0][0];cut=head.index(': ')+2
        lines=[((head[cut:] if bn else 'These include '+head[cut:]),lines[0][1]),*lines[1:]]
    tail=[(('ভালো না খারাপ, সেই সিদ্ধান্ত আপনার। চাইলে অন্য ব্যাংকের হারের সাথে মিলিয়ে দেখতে পারেন।' if bn else "Whether it is good or not is your decision. You can compare it with other banks' rates if you like."),[])] if opinion else []
    return lead+frame+lines+closing+tail

def terms_first(lead):
    return ' মানে ' in lead[0][0] or ' means ' in lead[0][0]

def grouped_rates(rows,name,whose,bn,kind,lead=False):
    """One sentence per product with terms in order; two named schemes share a sentence."""
    labels={}
    for f in rows:
        label=answers.scheme_name(f['values'],bn)
        if not bn:
            # Group as the Bangla answer does: terms of one scheme are one group, a plain FDR/DPS has no name.
            key=product_name(f['values'],True)
            label='' if key==PRODUCT_LABEL[kind][0] else re.sub(r'\bFixed Deposit\b','FDR',re.sub(r'\s*\d+(?:\s*&\s*\d+)?\s*(?:months?|years?|days?)(?:\s*\(\d+\s*days\))?$','',label,flags=re.I)).strip()
        labels.setdefault(label,[]).append(f)
    plain=PRODUCT_LABEL[kind][1];out=[]
    if len(labels)==2 and all(len(v)==1 for v in labels.values()) and '' not in labels:
        (a,x),(b,y)=labels.items();ids=[x[0]['fact_id'],y[0]['fact_id']];rate=lambda f:answers.rate_list([f],bn)
        if bn:
            said=re.sub(r'(\S+%)$',r'সুদ \1',rate(x[0]))
            return [(f"{'' if lead else whose}{a}ে {said}, আর {b}ে {rate(y[0])}।",ids)]
        one=lambda l,f:f"{'The ' if lead else whose if l==a else 'its '}{l} pays {rate(f)}"
        return [(f'{one(a,x[0])}, and {"the " if lead else ""}{one(b,y[0]).removeprefix("The ")}.',ids)]
    if not bn and len(labels)>=2 and any(len(v)>1 for v in labels.values()):
        # English numbers are long when spoken: give each scheme's range so no scheme drops to a "hear more" page.
        parts=[]
        for label,items in labels.items():
            values=sorted({f['values']['rate'] for f in items});low,high=number_text(values[0]),number_text(values[-1])
            pays=f'{low}%' if low==high else f'{low}% to {high}%'
            parts.append(f"{'its standard '+plain if not label else 'its '+label} pays {pays}")
        return [(f"{whose if not lead else ''}{parts[0][4:] if not lead else 'The '+parts[0][4:]}"+''.join(', and '+p for p in parts[1:])+', depending on the term.',[f['fact_id'] for items in labels.values() for f in items])]
    for index,(label,items) in enumerate(labels.items()):
        ids=[f['fact_id'] for f in items];said=answers.rate_list(items,bn)
        if bn:text=f'{whose if not index else ""}{label}ে {said}।'
        else:
            generic=not label
            text=f"{name if not index else 'It'} pays {said} on {('an '+plain) if generic and plain=='FDR' else ('a '+plain) if generic else 'its '+label}."
        out.append((text,ids))
    return out

def card_overview(rows,whose,name,bn):
    names=list(dict.fromkeys(product_name(f['values'],True).removesuffix(' কার্ড') if bn else ' '.join(dict.fromkeys(x for x in (f['values'].get('network'),f['values'].get('tier')) if x)) for f in rows))
    shown=names[:6];joined=(', '.join(shown[:-1])+(' ও ' if bn else ' and ')+shown[-1]) if len(shown)>1 else shown[0]
    if bn:text=f"{whose}কার্ডের মধ্যে আছে {joined}{' সহ আরও কয়েকটি' if len(names)>6 else ''}। আপনি কি এগুলোর বার্ষিক ফি জানতে চান, নাকি অন্য কিছু?"
    else:text=f"{name}'s cards include {joined}{', among others' if len(names)>6 else ''}. Would you like their annual fees, or something else?"
    return (text,[f['fact_id'] for f in rows])

def fee_list(rows,whose,bn,late=False):
    """Card fees as one list. Late fees group equal amounts by tier, annual fees name each card."""
    if late:
        fees={}
        for f in rows:fees.setdefault(number_text(f['values']['rate']),[]).append(f['values'].get('tier') or '')
        tier=lambda t:pronounce_tier(t,bn)
        if bn:
            parts=[(' আর '.join(tier(t) for t in tiers))+f'ে {fee} টাকা' for fee,tiers in fees.items()]
            text=f"{whose}ক্রেডিট কার্ডে লেট পেমেন্ট ফি "+', '.join(parts)
        else:
            parts=[f"{fee} taka on "+' and '.join(tiers) for fee,tiers in fees.items()]
            text=f"{whose}late payment charge is "+(', '.join(parts[:-1])+', and '+parts[-1] if len(parts)>1 else parts[0])
        return (text+('।' if bn else '.'),[f['fact_id'] for f in rows])
    names=[product_name(f['values'],True).removesuffix(' কার্ড') if bn else ' '.join(dict.fromkeys(x for x in (f['values'].get('network'),f['values'].get('tier')) if x)) for f in rows]
    unit='টাকা' if bn else 'taka'
    text=(f"{whose}ক্রেডিট কার্ডে বার্ষিক ফি: " if bn else f"{whose}annual card fees: ")+', '.join(f"{name} {number_text(f['values']['rate'])} {unit}" for name,f in zip(names,rows))
    return (text+('।' if bn else '.'),[f['fact_id'] for f in rows])

def pronounce_tier(tier,bn):
    return product_name({'product_type':'card','tier':tier,'product':''},True).removesuffix(' কার্ড') if bn else tier

def one_rate(rows,whose,bn):
    """Several products at one rate read as one sentence with the rate once."""
    rate=number_text(rows[0]['values']['rate']);ids=[f['fact_id'] for f in rows]
    terms={term_text(f['values'],bn) for f in rows}
    if bn and len(rows)==2 and len(terms)==1:
        names=[product_name(f['values'],True) for f in rows]
        return (f"{whose}{names[0]} আর {names[1]}, দুটিতেই {next(iter(terms))}ে সুদ {rate}%। আমাদের কাছে এই দুটি ডিপিএসের তথ্যই আছে।",ids)
    if bn:
        parts=[f"{product_name(f['values'],True)}ে {term_text(f['values'],True)}" for f in rows]
        return (f"{whose}{', '.join(parts)} মেয়াদে সুদ {rate}%।",ids)
    parts=[f"{product_name(f['values'],False)} for {term_text(f['values'],False)}" for f in rows]
    return (f"{whose[:-3] if whose.endswith(chr(39)+'s ') else whose} pays {rate}% on its {', '.join(parts)}.",ids)

def standard_named(lines,facts,bn):
    """Beside a named product, an unnamed row at the same term is the bank's standard one."""
    if bn:return [(re.sub(r'^(.*?)(এফডিআরে )',lambda m:m[1]+'সাধারণ '+m[2],s,count=1) if 'ভ্যালু' not in s and s.count('এফডিআরে') else s,ids) for s,ids in lines]
    return [(s.replace(' on a ',' on a standard ',1),ids) for s,ids in lines]

def date_once(lines):
    """Say a shared rate-sheet date once, on the last sentence that uses it."""
    pattern=re.compile(r', ((?:\S+ ){2}\S+-এর তালিকা অনুযায়ী|schedule dated [^.]+)(?=[।.]$)')
    found=[pattern.search(s) for s,_ in lines];output=[]
    for index,(sentence,ids) in enumerate(lines):
        later=next((m for m in found[index+1:] if m),None)
        if found[index] and later and later[1]==found[index][1]:sentence=pattern.sub('',sentence)
        output.append((sentence,ids))
    return output

def matches(v,months):
    return months in v['tenor_options'] if v.get('tenor_options') else v.get('tenor_min_months') is not None and v['tenor_min_months']<=months<=v['tenor_max_months']

SPECIAL=re.compile(r'women|child|senior|premium',re.I)
def deposit_order(f):
    """Shortest term first; at one term, the general product before special ones and higher rates."""
    v=f['values'];start=v.get('selected_tenor') or v.get('tenor_min_months') or v.get('tenor_months') or 999
    return (start,bool(SPECIAL.search(v.get('product',''))),-(v.get('rate') or 0))

def recommended(intent,c,registry,facts,key):
    current=[f for f in facts.values() if f.get('institution_id')==c.institution_id]
    fid=lambda f:'f:'+f['fact_id']
    available=lambda items:[fid(f) for f in items if fid(f) in registry]
    if intent in {'bank_overview','bank_condition'}:
        status=available([f for f in current if f['kind']=='status'])[:1]
        safety=[f for f in current if f.get('values',{}).get('metric') in {'crar','npl_ratio','rating'} and f['kind']!='peer']
        safety.sort(key=lambda f:({'crar':0,'npl_ratio':1,'rating':2}[f['values']['metric']]))
        weak=[f for f in current if f['kind']=='peer' and material(f) and f['values'].get('worse')]
        profile=[f for f in current if f['kind']=='profile' and f['values']['field'] in {'founded_year','branches'}]
        capital=available([f for f in safety if f['values']['metric']=='crar'])[:1]
        # Loan quality is always said: nothing may push it out of an overview.
        loans=available([f for f in safety if f['values']['metric']=='npl_ratio'])[:1]
        weak=[f for f in weak if f['values'].get('metric')!='npl_ratio'] if loans else weak
        # A material capital/rating weakness is itself a safety reason. Lead with
        # it rather than paging it away behind a positive ratio.
        if weak and weak[0]['values'].get('metric') in {'crar','npl_ratio','rating'}:
            return status+loans+available(weak)[:1]
        return status+list(dict.fromkeys((capital or available(safety)[:1])+loans))+(available(weak)[:1] or (available(profile)[variant(key,c,max(1,len(profile))):][:1] if not loans else []))
    if intent=='bank_history':return available([f for f in current if f['kind']=='history'])
    if intent=='bank_profile' and 'asked:founded' in registry:return ['asked:founded']+(['asked:founder'] if 'asked:founder' in registry else [])
    if intent=='bank_profile':return ['gap:profile'] if 'gap:profile' in registry else available([f for f in current if f['kind']=='profile'])[:3]
    if intent in {'bank_figures','bank_reasons'}:
        if intent=='bank_figures' and 'asked:figure' in registry:return [name for name in ('asked:figure','asked:previous','asked:interim','asked:by','asked:risk','asked:capital','asked:meaning','asked:change','asked:guess') if name in registry]
        values=[f for f in current if f['kind']=='figure' and f['fact_id'] not in c.spoken_fact_ids]
        if intent=='bank_figures':return ['value:'+f['fact_id'] for f in values][:3]
        return available(values)[:3]
    if intent=='service_detail':
        if 'note:product' in registry:return [name for name in ('note:product','note:norate') if name in registry]
        if 'gap:product' in registry:return ['gap:product']
        offers=[f for f in current if f['kind']=='service' and f['values']['product_type']==c.product]
        matching=[f for f in offers if c.tenor is None or matches(f['values'],c.tenor)]
        selected=matching or offers
        if c.product=='card':
            selected=[f for f in selected if f['values']['attribute']==('late_fee' if 'meta:late' in registry else 'annual_fee') and (not c.network or f['values']['network']==c.network) and (not c.tier or f['values']['tier']==c.tier)]
            # Staff, co-brand and flexi variants stay on the card list, not in the answer.
            selected=[f for f in selected if f['values'].get('variant')=='main'] or selected
            return available(selected)[:6]+(['note:waiver'] if 'note:waiver' in registry else [])
        if c.product in {'fdr','dps','savings'}:selected=sorted(selected,key=deposit_order)
        return (['gap:term'] if 'gap:term' in registry else [])+available(selected)[:8]
    if intent=='compare':
        if 'cmp:0' in registry:return [name for name in registry if name.startswith('cmp:')]
        if 'gap:term' in registry:return ['gap:term']+recommended('service_detail',c,registry,facts,key)[1:3]
        keys=['row:'+str(i)+'.offer' for i in range(4) if 'row:'+str(i)+'.offer' in registry]+[name for name in registry if name.startswith('gap:compare:')]
        # The first bank the question named (the anchor) is answered first.
        order=[c.institution_id] if c.institution_id else []
        return sorted(keys,key=lambda name:order.index(registry[name].bank_id) if registry[name].bank_id in order else len(order))
    if intent=='insurance':return available([f for f in current or list(facts.values()) if f['kind']=='insurance'])[:1]
    if intent=='services_list':return available([f for f in current if f['kind']=='inventory'])[:1]
    if intent=='explain_term':return available([f for f in facts.values() if f['kind']=='term'])[:1]
    return []


def fallback_lines(intent,c,registry,facts,key):
    choices=recommended(intent,c,registry,facts,key);lines=[]
    for token in choices:
        if token.startswith('f:'):
            forms=[name for name in registry if re.match(r'v\d+:',name) and name.split(':',1)[-1]==token[2:]]
            if forms:token=forms[variant(key,c,len(forms))]
        item=registry[token];bank='bank:'+str(item.bank_id)
        prefix='⟨'+bank+'⟩'+('ের ' if c.language=='bn' and item.kind in {'status','service','figure','service_note','gap'} else ' ') if bank in registry and item.kind!='comparison' and (not lines or intent in {'compare'}) else ''
        lines.append(prefix+'⟨'+token+'⟩'+('।' if c.language=='bn' else '.'))
    return lines


def packet(r,c,memory,registry,facts,key):
    ids=list(facts);short={fid:'t'+str(i) for i,fid in enumerate(ids)}
    def encode_key(value):
        for prefix in ('f:','value:'):
            if value.startswith(prefix):return prefix+short[value[len(prefix):]]
        if re.match(r'^v\d+:',value):
            prefix,fid=value.split(':',1)
            return prefix+':'+short[fid]
        return value
    decoded_keys={encode_key(name):name for name in registry}
    entries=[]
    wanted=set(recommended(r.intent or 'bank_overview',c,registry,facts,key))
    for name,item in registry.items():
        if name.startswith('value:') and r.intent!='bank_figures':continue
        f=facts.get(name[2:]) if name.startswith('f:') else None
        if f and f['kind']=='service' and r.product and f['values']['product_type']!=r.product:continue
        entries.append({'token':'⟨'+encode_key(name)+'⟩','meaning':item.text,'spoken_words':len(pronounce(item.text,c.language).split()),'used':[short[id] for id in item.fact_ids],'recommended':name in wanted})
    payload={'language':c.language,'words':r.text,'intent_hint':r.intent,'slots':{'bank':r.bank_id,'product':r.product,'term':r.tenor,'network':r.network,'tier':r.tier,'correction':r.correction},'direct_protection':r.direct_protection,'memory':memory.get('last_turns',[])[-4:],'spoken':[short[fid] for fid in c.spoken_fact_ids if fid in short],'tokens':entries}
    choices=[]
    for name,item in registry.items():
        if name.startswith('bank:') or name.startswith('row:') and not name.endswith('.offer'):continue
        if name.startswith('value:') and r.intent!='bank_figures':continue
        f=facts.get(name[2:]) if name.startswith('f:') else None
        if f and f['kind']=='service' and r.product and f['values']['product_type']!=r.product:continue
        bank='bank:'+str(item.bank_id)
        if name.startswith('row:'):
            prefix='⟨'+name.replace('.offer','.bank')+'⟩'+('ের ' if c.language=='bn' else ' ')
        else:prefix='⟨'+bank+'⟩'+('ের ' if c.language=='bn' and item.kind in {'status','service','figure'} else ' ') if bank in registry else ''
        choices.append(prefix+'⟨'+encode_key(name)+'⟩'+('।' if c.language=='bn' else '.'))
        if not name.startswith('row:'):choices.append('⟨'+encode_key(name)+'⟩'+('।' if c.language=='bn' else '.'))
    if r.intent in {'compare','service_detail','bank_profile','explain_term','bank_figures'}:
        preferred=recommended(r.intent,c,registry,facts,key)
        preferred_tokens={'⟨'+encode_key(name)+'⟩' for name in preferred}
        choices=[line for line in choices if any(token in line for token in preferred_tokens)]
    payload['line_choices']=choices or ['আচ্ছা।' if c.language=='bn' else 'Understood.']
    payload['fact_ids']=list(short.values())
    payload['required_intro_facts']=list(dict.fromkeys(short[fid] for name in wanted if registry[name].kind in {'status','peer','figure'} for fid in registry[name].fact_ids)) if r.intent in {'bank_overview','bank_condition'} else []
    payload['fact_revision']=hashlib.sha256(json.dumps(facts,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
    payload['question_choices']=list(dict.fromkeys([next_steps(intent,c,key)[0] for intent in STATE]+['']))
    def decode(value):
        reverse={v:k for k,v in short.items()}
        return TOKEN.sub(lambda m:'⟨'+decoded_keys.get(m[1],m[1])+'⟩',value),reverse
    return payload,decode


LIST_WORDS=60
def paginate(lines,question,language,split=False):
    # A list of a bank's products may use the full checked reply length.
    limit=LIST_WORDS if split else 45
    budget=limit-len(pronounce(question,language).split());selected=[];pending=[]
    # A page that will continue ends with the two-word "hear more" question instead.
    if split and len(pronounce(' '.join(t for t,_ in lines),language).split())>budget:budget=limit-2
    for text,ids in lines:
        if not pending and len(pronounce(' '.join(t for t,_ in selected)+' '+text,language).split())<=budget:selected.append((text,ids))
        elif not pending and split and selected and ', ' in text:
            # A long list of rates may break between two terms, never inside one.
            clauses=re.split(r', (?=[^,]*(?:বছরে|মাসে|টাকা|taka))',text.rstrip('।.'));first=[];said=' '.join(t for t,_ in selected)
            while clauses and len(pronounce(said+' '+', '.join(first+[clauses[0]]),language).split())<=budget:first.append(clauses.pop(0))
            end='।' if language=='bn' else '.'
            if first:selected.append((', '.join(first)+end,ids))
            if clauses:pending.append((', '.join(clauses)+end,ids))
        else:pending.append((text,ids))
    if not selected and pending:
        text,ids=pending.pop(0)
        clauses=re.split(r'[,;]\s*',text)
        first=[]
        while clauses and len(pronounce(' '.join(first+[clauses[0]]),language).split())<=budget:first.append(clauses.pop(0))
        if first:selected=[(', '.join(first).rstrip('।.!?')+('।' if language=='bn' else '.'),ids)]
        else:selected=[(('বিস্তারিত তথ্য কার্ডে আছে।' if language=='bn' else 'The detailed information is on the card.'),ids)]
        if clauses:pending.insert(0,(', '.join(clauses),ids))
    return selected,pending


async def run(text,context,banks,db,candidates=(),choice=None,watch_identity=None,client=None,device_hash=None,on_sentence=None):
    from ilma_api.human_agent import controls,render,finish,exact_choice,repeat_turn,guess
    from ilma_api.voice_agent import Conversation
    from ilma_api.voice_pipeline import consume_question
    started=time.monotonic();trace=[dict(stage='ASR',model='none',ms=0,status='transcript_received')]
    initial=context.conversation or Conversation(institution_id=context.bank_id,language=context.ui_lang)
    id,memory=await call(db,lambda owned:load(owned,initial.conversation_token))
    c=Conversation.model_validate(memory.get('conversation') or initial.model_dump()).model_copy(update={'language':context.ui_lang})
    if is_banglish(text):c=c.model_copy(update={'language':'bn'})
    if memory.get('protocol')!=2:
        memory={k:v for k,v in memory.items() if k not in {'last_result','pending_reply','pending_facts','last_next'}}
        memory['last_turns']=[]
    memory['protocol']=2
    memory.pop('_reviewed_context',None)
    safe=redact_user(text);selected=exact_choice(safe,c,memory,choice)
    confirmed_pair=memory.pop('clarify_pair',None) if selected=='confirm_bank' else None
    rejected_pair=memory.pop('clarify_pair',None) if selected=='reject_bank' else None
    if selected not in {'repeat','confirm_bank','reject_bank'}:memory.pop('clarify_pair',None)
    if rejected_pair:
        result=render(controls('unclear',c,'ঠিক আছে।' if c.language=='bn' else 'All right.','দুটি ব্যাংকের নাম আবার বলবেন?' if c.language=='bn' else 'Could you say both bank names again?',['listen','ask_bank']),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if memory.get('pending_reply') and re.fullmatch(r'হ্যাঁ|জি|yes|yeah',safe.strip(' .!?।'),re.I):selected='more'
    if selected=='yes' and memory.get('pending_reply'):selected='more'
    # "হ্যাঁ" answers a "did you mean" question with the bank it offered first.
    if memory.get('clarify_candidates') and not selected and re.fullmatch(r'হ্যাঁ|জি|yes|yeah|ok',safe.strip(' .!?।'),re.I):selected='bank_1'
    if selected=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
    if selected=='more' and memory.get('pending_reply'):
        from ilma_api.human_checker import sentences
        pending=memory['pending_reply'];rows=list(zip(sentences(pending['reply']),pending['sentence_fact_ids']))
        head,tail=paginate(rows,pending['next_question'],c.language)
        question,buttons=next_steps(pending['intent'],c,id,more=bool(tail))
        a=controls(pending['intent'],c,' '.join(s for s,_ in head),question,buttons)
        a=a.model_copy(update={'used_fact_ids':list(dict.fromkeys(f for _,row in head for f in row)),'sentence_fact_ids':[row for _,row in head]})
        facts=memory.get('pending_facts',[])
        result=render(a,c,facts,trace,'code')
        continuation={**pending,'reply':' '.join(s for s,_ in tail),'sentence_fact_ids':[row for _,row in tail]} if tail else None
        if continuation:result['_all_facts']=facts
        return await finish(result,safe,id,memory,db,started,continuation)
    if c.turn>=19 or selected in {'stop','end'}:
        a=controls('stop',c,'আবার জানতে চাইলে মাইক চাপুন।' if c.language=='bn' else 'Tap the microphone whenever you have another question.')
        result=render(a,c,[],trace,'code');result['action']={'type':'end' if selected=='end' or c.turn>=19 else 'stop'}
        return await finish(result,safe,id,memory,db,started)
    # The 15-second cap (usually room noise keeping the mic open) still leaves a whole question when a bank or topic was heard.
    heard_whole=bool(context.audio_truncated) and (lambda q:bool(q.bank_id or q.product or q.intent in {'compare','insurance','advice_request','best_bank'}))(resolve(safe,Conversation(language=c.language),banks))
    if context.audio_truncated and not heard_whole:
        a=controls('unclear',c,'শেষ অংশটা শুনতে পাইনি।' if c.language=='bn' else 'I may have missed the ending.','প্রশ্নটি ছোট করে আবার বলবেন?' if c.language=='bn' else 'Could you ask a shorter question?',['listen','ask_bank'])
        result=render(a,c,[],trace,'code');result['audio_truncated']=True
        return await finish(result,safe,id,memory,db,started)
    forced={'detail':'bank_reasons','figures':'bank_figures','history':'bank_history','services':'services_list','compare':'compare','insurance':'insurance'}.get(selected)
    if selected in {'account_fees','debit'}:
        c=c.model_copy(update={'product':'account_fee','tenor':None,'network':None,'tier':None});forced='service_detail'
        memory['account_view']=selected
    if selected in {'savings','fdr','dps','card','home_loan'}:
        memory.pop('account_view',None)
        c=c.model_copy(update={'product':selected,'tenor':None if selected!=c.product else c.tenor,'network':c.network if selected=='card' else None,'tier':c.tier if selected=='card' else None});forced='service_detail'
    if selected and selected.startswith('bank_'):
        peers=memory.get('clarify_candidates') or c.compare_bank_ids;index=int(selected[-1])-1
        if index<len(peers):c=c.model_copy(update={'institution_id':peers[index],'product':None,'tenor':None,'network':None,'tier':None});forced='bank_overview'
    if selected=='ask_bank':c=c.model_copy(update={'institution_id':None,'product':None,'tenor':None,'network':None,'tier':None});forced='unclear'
    if selected=='listen':forced='unclear'
    resolve_started=time.monotonic()
    resolved=resolve(safe,c,banks)
    if memory.get('account_scope') and resolved.product in {'savings','account_fee'} and resolved.requested_field!='debit' and re.search(r'ফি(?=$|[\s।?!,]|র(?:\s|$))|চার্জ|\bfees?\b|\bcharges?\b',safe,re.I):resolved=replace(resolved,product='account_fee',intent='service_detail',requested_field='account_fees',account_overview=False)
    if selected in {'account_fees','debit'}:resolved=replace(resolved,product='account_fee',intent='service_detail',requested_field=selected,account_overview=False)
    elif selected=='savings':resolved=replace(resolved,product='savings',intent='service_detail',tenor=None,account_overview=False)
    elif resolved.product=='account_fee' and not resolved.account_overview and memory.get('account_view')=='debit' and not re.search(r'অ্যাকাউন্ট|একাউন্ট|হিসাব|\baccount|রক্ষণাবেক্ষণ|এসএমএস|maintenance|sms',safe,re.I):resolved=replace(resolved,requested_field='debit')
    if confirmed_pair:
        resolved=replace(resolved,bank_id=confirmed_pair['ids'][0],compare_bank_ids=confirmed_pair['ids'],product=confirmed_pair['product'],tenor=confirmed_pair['tenor'],intent='compare',confirm_ids=[],confirm_pair=False)
        forced='compare'
    trace.append(dict(stage='RESOLVER',model='code',ms=round((time.monotonic()-resolve_started)*1000),status='ok'))
    facts_started=time.monotonic();conversation_bank_before=c.institution_id
    r,c,packs,comparisons,registry,facts=await call(db,lambda owned:prepare(owned,safe,c,banks,forced,resolved))
    from ilma_api.reviewed_sources import context as reviewed_context
    # Saved-answer keys are hashes made with the frozen filter (redact_for_key), so hash the words as said; only the hash is kept.
    heard=context.raw_text or text
    memory['_reviewed_context']=await call(db,lambda owned:reviewed_context(owned,heard,r,facts,c.language,conversation_bank_before))
    trace.append(dict(stage='FACTS',model='database',ms=round((time.monotonic()-facts_started)*1000),status='ok'))
    if r.intent=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
    blocked=None if selected else answers.refusal(text,c.language=='bn',any(b['confidence']>=.9 for b in r.candidates))
    if blocked:
        memory.pop('clarify_candidates',None)
        result=render(controls('out_of_scope',c,blocked[0],blocked[1],['ask_bank','end'] if blocked[1] else []),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    from ilma_api.other_banks import find_other_bank,is_central_bank
    if re.search(r'^\s*(?:what(?:’s|\'s| is| are)\s+(?:an?\s+)?islamic bank(?:s|ing)?|(?:ইসলামী|ইসলামি|ইসলামিক) ব্যাংকিং (?:কী|কি))[\s?।.!]*$',safe,re.I):
        line=('ইসলামী ব্যাংক সুদের বদলে মুনাফা ভাগাভাগির নিয়মে চলে, তাই আমানতের হার আগে থেকে নিশ্চিত থাকে না। কোন ব্যাংকের তথ্য শুনবেন?' if c.language=='bn' else 'An Islamic bank works on profit sharing instead of interest, so its deposit returns are not fixed in advance. Which bank would you like to hear about?')
        c=c.model_copy(update={'institution_id':None,'product':None,'compare_bank_ids':[]})
        result=render(controls('unclear',c,line,*next_steps('unclear',c,id)),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if is_central_bank(safe) and not any(b['confidence']>=.9 for b in r.candidates):
        line=('বাংলাদেশ ব্যাংক দেশের কেন্দ্রীয় ব্যাংক। এটি অন্য ব্যাংকগুলো তদারকি করে, সাধারণ মানুষের কাছ থেকে আমানত নেয় না।' if c.language=='bn' else 'Bangladesh Bank is the central bank. It supervises the other banks and does not take deposits from the public.')
        result=render(controls('unclear',c,line,*next_steps('unclear',c,id)),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    unknown=find_other_bank(safe)
    if unknown:
        # Forget the bank this turn resolved to, so "what is the FDR rate?" next cannot land on it.
        c=c.model_copy(update={'institution_id':None,'product':None,'compare_bank_ids':[]})
        result=render(controls('unclear',c,'এই ব্যাংকের তথ্য এখনো যোগ হয়নি।' if c.language=='bn' else 'Information for this bank has not been added yet.',*next_steps('unclear',c,id)),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if r.confirm_pair:
        memory.pop('clarify_candidates',None);memory.pop('pending_reply',None);memory.pop('pending_facts',None)
        memory['clarify_pair']={'ids':r.confirm_ids,'product':r.product,'tenor':r.tenor}
        names=[next(b['name_bn' if c.language=='bn' else 'name_en'] for b in banks if b['id']==id) for id in r.confirm_ids]
        question=('আপনি '+ ' এবং '.join(names)+'—দুটি ব্যাংকের তথ্য চান, ঠিক বুঝেছি?' if c.language=='bn' else 'You want information about both '+' and '.join(names)+', is that right?')
        c=c.model_copy(update={'misses':0})
        result=render(controls('unclear',c,question),c,[],trace,'code')
        result['expects_reply']=True
        result['next']={'question':question,'affirmative_action':'confirm_bank','negative_action':'reject_bank','options':[{'value':'confirm_bank','label':'হ্যাঁ' if c.language=='bn' else 'Yes'},{'value':'reject_bank','label':'না' if c.language=='bn' else 'No'}]}
        return await finish(result,safe,id,memory,db,started)
    if r.confirm_ids:
        memory['clarify_candidates']=r.confirm_ids
        options=[{'value':'bank_'+str(i+1),'label':next(b['name_bn' if c.language=='bn' else 'name_en'] for b in banks if b['id']==value)} for i,value in enumerate(r.confirm_ids)]
        question=(' নাকি '.join(o['label'] for o in options)+' বলছেন?' if c.language=='bn' else 'Did you mean '+' or '.join(o['label'] for o in options)+'?')
        # One close bank is a yes-or-no question, not a list of one.
        if len(options)==1:options=[{'value':'bank_1','label':'হ্যাঁ' if c.language=='bn' else 'Yes'},{'value':'ask_bank','label':'না' if c.language=='bn' else 'No'}]
        result=render(controls('unclear',c,question),c,[],trace,'code');result['next']={'question':question,'options':options}
        return await finish(result,safe,id,memory,db,started)
    if r.bank_id is None and (selected=='ask_bank' or r.intent in {'bank_overview','bank_condition','bank_reasons','bank_figures','bank_profile','bank_history','bank_awards','services_list','service_detail'}):
        question='কোন ব্যাংকের কথা জানতে চান?' if c.language=='bn' else 'Which bank would you like to know about?'
        result=render(controls('unclear',c,'',question,['listen','end']),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if r.account_overview:
        memory['account_scope']=True
        memory.pop('pending_reply',None);memory.pop('pending_facts',None);memory.pop('account_view',None)
        c=c.model_copy(update={'misses':0})
        bank=registry.get('bank:'+str(c.institution_id));name=bank.text if bank else ''
        question=('আপনি সঞ্চয়ী হিসাবের সুদ জানতে চান, নাকি ফি ও চার্জ বা ডেবিট কার্ডের তথ্য?' if c.language=='bn' else 'Would you like savings interest, account fees and charges, or debit-card information?')
        result=render(controls('services_list',c,'',question),c,[],trace,'code')
        from ilma_api.human_contract import LABELS
        result['next']={'question':question,'options':[{'value':value,'label':LABELS[value][0 if c.language=='bn' else 1]} for value in ['savings','account_fees','debit']]}
        result['topic']=(name+' · ' if name else '')+('হিসাবের তথ্য' if c.language=='bn' else 'Account information')
        return await finish(result,safe,id,memory,db,started)
    if r.product=='account_fee' and r.intent=='service_detail':
        memory['account_scope']=True;memory['account_view']='debit' if r.requested_field=='debit' else 'account_fees'
        from ilma_api.account_voice import answer as account_answer
        body,account_facts=await call(db,lambda owned:account_answer(owned,c.institution_id,r.requested_field=='debit',c.language))
        a=controls('service_detail',c,body).model_copy(update={'used_fact_ids':[f['fact_id'] for f in account_facts]})
        result=render(a,c,account_facts,trace,'code')
        bank=registry.get('bank:'+str(c.institution_id));name=bank.text if bank else ''
        result['topic']=(name+' · ' if name else '')+(('ডেবিট কার্ড' if r.requested_field=='debit' else 'ফি ও চার্জ') if c.language=='bn' else ('Debit card' if r.requested_field=='debit' else 'Fees and charges'))
        return await finish(result,safe,id,memory,db,started)
    if r.intent=='bank_awards' and not selected:
        # Awards are answered by code from sourced rows; the model never names them.
        lines,award_facts=await call(db,lambda owned:award_answer(owned,c,registry,facts))
        question,buttons=next_steps('bank_awards',c,id)
        question=answers.closing('bank_awards',safe,bank_status(facts,c.institution_id),c.language=='bn') or question
        if any(facts.get(i,{}).get('kind')=='figure' for _,ids in lines for i in ids):question=''
        a=controls('bank_awards',c,' '.join(t for t,_ in lines),question,buttons).model_copy(update={'used_fact_ids':[f for _,ids in lines for f in ids],'sentence_fact_ids':[ids for _,ids in lines]})
        result=render(a,c,[*award_facts,*[f for f in facts.values() if any(f['fact_id'] in ids for _,ids in lines)]],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    # Persist code-resolved context before a paid wait, so interrupting a new
    # bank request cannot restore the previous bank on the next question.
    previous_bank=memory.get('conversation',{}).get('institution_id',initial.institution_id)
    if previous_bank!=c.institution_id:
        memory.pop('last_result',None);memory.pop('pending_reply',None);memory.pop('pending_facts',None)
    memory['conversation']=c.model_dump()
    await call(db,lambda owned:save(owned,id,memory))
    if on_sentence is not None:
        await on_sentence({'_event':'resolved_context','conversation':{**c.model_dump(),'conversation_token':token(id)}})
    # Exact reviewed questions use their fact-bound saved answer without a wording request.
    from ilma_api.reviewed_answers import apply as apply_reviewed
    probe=apply_reviewed({'language':c.language,'next':{},'conversation':{}},safe,memory.get('_reviewed_context'),dict(memory))
    if probe.get('reviewed_audio_url'):
        if not selected:await call(db,lambda owned:consume_question(owned,watch_identity or device_hash or 'human-anonymous'))
        result=render(controls(r.intent or 'smalltalk',c,''),c,[],trace,'code')
        trace.append(dict(stage='CHECK',model='code',ms=0,status='ok',reason='reviewed_source_bound_answer'))
        return await finish(result,safe,id,memory,db,started)
    model=None;fallback_reason=None;repaired=[]
    # Every sentence of these answers is a stored value, so code writes them: each
    # rephrasing of a question then gets the same facts in the same order.
    code_owned=r.intent=='advice_request' or r.intent=='explain_term' and 'term:interest_profit_difference' in facts or bool(r.product) and (forced or r.intent)=='service_detail' or (forced or r.intent)=='bank_figures' and 'asked:figure' in registry or (forced or r.intent)=='bank_profile' and 'asked:founded' in registry or (forced or r.intent) in {'bank_overview','bank_condition'} and not r.requested_metric or (forced or r.intent)=='bank_history' and any(f['kind']=='history' and f['institution_id']==c.institution_id for f in facts.values()) or (forced or r.intent)=='compare' and 'cmp:0' in registry or (forced or r.intent)=='compare' and bool(r.product) and any(name.startswith('gap:compare:') for name in registry)
    # Written by code or by the model, an answered question counts the same.
    if not selected and code_owned:await call(db,lambda owned:consume_question(owned,watch_identity or device_hash or 'human-anonymous'))
    if not selected and not code_owned:
        payload,decode=packet(r,c,memory,registry,facts,id)
        if r.intent in {'bank_overview','bank_condition'} and not r.correction:
            from ilma_api.human_variants import fingerprint,choose
            cache_key=fingerprint(payload,registry)
            model=await call(db,lambda owned:choose(owned,cache_key,memory,payload,decode,registry))
            if model:trace.append(dict(stage='CACHE',model='offline_spark',ms=0,status='hit',reason=cache_key[:12]))
        deadline=time.monotonic()+settings.HUMAN_MODEL_TIMEOUT_SECONDS
        preview=[]
        async def checked_line(value,header):
            if on_sentence is None:return
            resolved_intent=forced or r.intent or header.intent
            if resolved_intent in {'smalltalk','unclear','stop','out_of_scope','advice_request','best_bank','repeat'}:return
            value,reverse=decode(value)
            try:sentence,ids=fill(value,registry,[reverse.get(fid,fid) for fid in header.used],insurance=r.direct_protection)
            except ValueError:return
            if len(pronounce(' '.join(preview+[sentence])+next_steps(resolved_intent,c,id)[0],c.language).split())>45:return
            if not sentence.endswith(('।','.','?')):sentence+=('।' if c.language=='bn' else '.')
            preview.append(sentence)
            partial=controls(resolved_intent,c,' '.join(preview),*next_steps(resolved_intent,c,id)).model_copy(update={'used_fact_ids':list(dict.fromkeys([*([fid for row in getattr(checked_line,'ids',[]) for fid in row]),*ids])),'sentence_fact_ids':[*getattr(checked_line,'ids',[]),ids]})
            checked_line.ids=[*getattr(checked_line,'ids',[]),ids]
            snapshot=render(partial,c,[{**f,'text_bn':card_text(f,'bn'),'text_en':card_text(f,'en')} for f in facts.values()],trace,'code')
            memory['last_result']={k:v for k,v in snapshot.items() if k not in {'trace','memory_turn'}}
            await call(db,lambda owned:save(owned,id,memory))
            await on_sentence({'text':sentence.translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')) if c.language=='bn' else sentence,'fact_ids':ids,'append':len(preview)>1,'language':c.language})
        if model is None:
            await call(db,lambda owned:consume_question(owned,watch_identity or device_hash or 'human-anonymous'))
            if context.speak and on_sentence is not None:
                from ilma_api.voice_acknowledgements import cached
                acknowledgement=await cached(c.language,memory)
                if acknowledgement:await on_sentence({'_event':'acknowledgement',**acknowledgement})
            model=await generate(payload,trace,client,deadline=deadline,on_line=checked_line)
            first_failure='schema' if model.error=='schema' else None
            if not model.error and model.lines and model.header:
                try:
                    first,reverse=decode(model.lines[0])
                    fill(first,registry,[reverse.get(fid,fid) for fid in model.header.used],insurance=r.direct_protection)
                except ValueError as error:first_failure=str(error)
            # One repair only for an invalid header or first sentence, using
            # the original deadline. Later sentence errors stay local.
            if first_failure and not preview and deadline-time.monotonic()>.2:
                model=await generate({**payload,'repair_reason':first_failure},trace,client,deadline=deadline,on_line=checked_line)
                trace[-1]['full_retry']=True
        partial_intent=forced or r.intent or (model.header.intent if model.header else None)
        if model.error and model.header and model.lines and partial_intent not in {'unclear','smalltalk','advice_request','best_bank','stop','out_of_scope','repeat'}:
            try:
                first,reverse=decode(model.lines[0])
                fill(first,registry,[reverse.get(fid,fid) for fid in model.header.used],insurance=r.direct_protection)
            except ValueError:pass
            else:
                # A checked prefix remains useful if the provider stalls after
                # it. Do not replace already streamed facts with a fallback.
                trace.append(dict(stage='STREAM',model='code',ms=0,status='partial',reason=model.error))
                model.error=None
        if model.error:fallback_reason=model.error
    intent=forced or r.intent or (model.header.intent if model and model.header else guess(safe))
    if intent=='correction':intent=c.last_intent if c.last_intent not in {None,'correction','repeat','stop','unclear'} else 'bank_overview'
    if intent=='insurance' and not r.direct_protection:intent='bank_condition'
    c=c.model_copy(update={'last_intent':intent})
    bn=c.language=='bn';question,buttons=next_steps(intent,c,id);lines=[]
    if not question and intent in {'compare','service_detail'} and any(name.startswith('gap:') for name in registry):
        # A missing figure is never the end of the answer: offer the next step.
        question='অন্য কোনো ব্যাংকের তথ্য শুনবেন?' if bn else 'Would you like to hear about another bank?'
    controls_map={
      'advice_request':('কোথায় টাকা রাখবেন সেটা আপনার সিদ্ধান্ত, আমি বিনিয়োগের পরামর্শ দিই না। তবে ব্যাংকের অবস্থা আর সুদের হার পাশাপাশি বুঝিয়ে দিতে পারি।' if re.search(r'বিনিয়োগ',safe) else 'কোন ব্যাংকে টাকা রাখবেন সেটা আপনার সিদ্ধান্ত, আমি পরামর্শ দিই না। তবে ব্যাংকের অবস্থা আর সুদ পাশাপাশি বোঝাতে পারি।','That decision is yours; I do not give investment advice. I can explain bank conditions and rates side by side.'),
      'best_bank':('কোন ব্যাংক বেছে নেবেন তা আপনার সিদ্ধান্ত। আমি প্রকাশিত তথ্য পাশাপাশি বুঝিয়ে বলতে পারি।','Choosing a bank is your decision. I can explain the published information side by side.'),
      'out_of_scope':('আমি ব্যাংকের তথ্য নিয়ে সাহায্য করতে পারি।','I can help with bank information.'),
      'unclear':('প্রশ্নটা একটু অন্যভাবে বলবেন?' if model and not model.error else 'এখন উত্তর সাজাতে সমস্যা হচ্ছে।','Could you ask that another way?' if model and not model.error else 'I am having trouble preparing that answer right now.'),
      'smalltalk':('আপনাকেও ধন্যবাদ। আবার জানতে চাইলে মাইক চাপুন।' if re.search(r'ধন্যবাদ|thank',safe,re.I) else 'আমি ইলমা। ব্যাংকের তথ্য জানতে সাহায্য করব।','Thank you. Tap the microphone whenever you have another question.' if re.search(r'ধন্যবাদ|thank',safe,re.I) else 'Hello, I am Ilma. I can help with bank information.'),
      'stop':('পড়া থামালাম।','I have stopped speaking.')}
    if intent in controls_map:
        lines=[(controls_map[intent][0 if bn else 1],[])]
        if intent=='advice_request' and bn and not re.search(r'বিনিয়োগ',safe):question=''
        if intent=='smalltalk' and re.search(r'ধন্যবাদ|thank',safe,re.I):question=''
        if intent=='stop':question=''
    else:
        raw_lines=[]
        if model and not model.error:
            _,reverse=decode('');used=[reverse.get(fid,fid) for fid in model.header.used]
            for index,line in enumerate(model.lines):
                line,_=decode(line)
                try:
                    rendered,ids=fill(line,registry,used,insurance=r.direct_protection)
                    if not rendered.endswith(('।','.','?')):rendered+=('।' if bn else '.')
                    if intent in {'bank_overview','bank_condition'} and len(re.findall(r'[0-9০-৯]+(?:[.,][0-9০-৯]+)*',' '.join(s for s,_ in lines)+' '+rendered))>1:raise ValueError('first_answer_numbers')
                    lines.append((rendered,ids))
                except ValueError as error:
                    repaired.append(str(error))
                    if str(error)=='first_answer_numbers':continue
                    tokens=[key for key in TOKEN.findall(line) if key in registry]
                    replacement=' '.join((registry['bank:'+str(registry[key].bank_id)].text+('ের ' if bn else ' ') if 'bank:'+str(registry[key].bank_id) in registry and intent=='compare' else '')+registry[key].text for key in tokens if registry[key].fact_ids)
                    ids=list(dict.fromkeys(fid for key in tokens for fid in registry[key].fact_ids))
                    if replacement and not BANNED.search(replacement) and (r.direct_protection or not PROTECTION_WORDS.search(replacement)):
                        lines.append((replacement.rstrip('।.?')+('।' if bn else '.'),ids))
                    elif index==0:fallback_reason='first_sentence_'+str(error)
        if fallback_reason:lines=[]
        if not lines:
            raw_lines=fallback_lines(intent,c,registry,facts,id)
            for line in raw_lines:
                keys=TOKEN.findall(line);used=list(dict.fromkeys(fid for key in keys for fid in registry[key].fact_ids))
                try:rendered,ids=fill(line,registry,used,insurance=r.direct_protection);lines.append((rendered,ids))
                except ValueError:continue
            if not selected and not code_owned:fallback_reason=fallback_reason or 'empty_reply'
        if not lines:
            lines=[(('এই তথ্য এখনো আমাদের কাছে নেই।' if bn else 'We do not have that information yet.'),[])]
    if intent in {'bank_overview','bank_condition'}:
        # A rate-sheet difference cannot displace the condition and its reason.
        required=recommended(intent,c,registry,facts,id)
        must=[key for key in required if registry[key].kind in {'status','peer'} or any(facts[fid].get('values',{}).get('metric') in {'crar','npl_ratio','rating'} for fid in registry[key].fact_ids)]
        seen={fid for _,ids in lines for fid in ids}
        for key in must:
            item=registry[key]
            if not set(item.fact_ids)<=seen:
                bank=registry.get('bank:'+str(c.institution_id));prefix=bank.text+('ের ' if bn else ' ') if bank and item.kind=='status' else ''
                lines.insert(0,(prefix+item.text+('।' if bn else '.'),list(item.fact_ids)))
        priority={fid:i for i,key in enumerate(must) for fid in registry[key].fact_ids}
        lines.sort(key=lambda row:min((priority[fid] for fid in row[1] if fid in priority),default=99))
        numeric_count=0;plain=[]
        for sentence,ids in lines:
            count=len(re.findall(r'[0-9০-৯]+(?:[.,][0-9০-৯]+)*',sentence))
            if numeric_count+count<=1:plain.append((sentence,ids));numeric_count+=count
        lines=plain
        # Add useful sourced context, not padding, when token expansion leaves
        # an introduction too short. Exact amounts remain on the source cards.
        extra=[key for key,item in registry.items() if key.startswith('f:') and item.bank_id==c.institution_id and (item.kind in {'profile','inventory'} or any(facts[fid].get('values',{}).get('metric') in {'crar','npl_ratio','rating'} for fid in item.fact_ids))]
        for key in extra:
            if len(pronounce(' '.join(s for s,_ in lines)+' '+question,c.language).split())>=35:break
            item=registry[key]
            if set(item.fact_ids)&{fid for _,ids in lines for fid in ids}:continue
            sentence=item.text.rstrip('।.?')+('।' if bn else '.')
            count=len(re.findall(r'[0-9০-৯]+(?:[.,][0-9০-৯]+)*',sentence))
            if numeric_count+count>1 or BANNED.search(sentence):continue
            if len(pronounce(' '.join(s for s,_ in lines)+' '+sentence+' '+question,c.language).split())<=45:
                lines.append((sentence,list(item.fact_ids)));numeric_count+=count
    # A coverage note answers only a question that asked for that detail.
    if intent in {'bank_overview','bank_condition','bank_reasons','bank_figures','bank_history'} and len(lines)>1:
        lines=[(s,ids) for s,ids in lines if not (ids and all(facts.get(fid,{}).get('kind')=='coverage' for fid in ids))] or lines
    if intent in {'bank_overview','bank_condition'} and c.institution_id and registry.get('bank:'+str(c.institution_id)):
        name=registry['bank:'+str(c.institution_id)].text;whose=polish(name+'ের ',{},True) if bn else name+"'s "
        status=bank_status(facts,c.institution_id);intro=[]
        # The opening is for general questions; "মূলধন কেমন?" answers the metric directly.
        if not r.requested_metric and c.institution_id not in memory.get('introduced_banks',[]):
            intro,extra=await call(db,lambda owned:introduction(owned,c,registry,facts,bool(interim_line(details(facts,c.institution_id),bn))))
            facts.update(extra)
            memory['introduced_banks']=[*memory.get('introduced_banks',[]),c.institution_id][-20:]
        award=any(facts.get(i,{}).get('kind')=='award' for _,ids in intro for i in ids)
        interim=interim_line(details(facts,c.institution_id),bn)
        lines=answers.overview_lines(name,whose,status,facts,c.institution_id,bn,intro,award,interim)
        if status=='no_data' and re.search(r'নিরাপদ|\bsafe\b',safe,re.I):
            lines=[((f'{name} নিরাপদ কি না তা বলতে পারছি না, কারণ এর অবস্থা যাচাই করার মতো নিরীক্ষিত তথ্য আমাদের কাছে নেই।' if bn else f'{name}: I cannot say whether it is safe, because we have no audited information to assess its condition.'),[])]
    if intent=='bank_history' and code_owned:
        name=registry['bank:'+str(c.institution_id)].text
        lines=answers.history_lines(name,polish(name+'ের ',{},True) if bn else name+"'s ",[f for f in facts.values() if f['kind']=='history' and f['institution_id']==c.institution_id],bn)
    if intent=='insurance' and bank_status(facts,c.institution_id)=='high':
        loans=answers.figure(facts,c.institution_id,'npl_ratio')
        if loans:lines.append(((f"মনে রাখবেন, এই ব্যাংকের ঝুঁকি বেশি। খেলাপি ঋণ {answers.percent(loans['values']['value'])}%, {answers.on(loans['values']['period_end'],True)}-এর হিসাবে।" if bn else f"Remember, this bank is high risk. Bad loans were {answers.percent(loans['values']['value'])}% as of {answers.on(loans['values']['period_end'],False)}."),[loans['fact_id']]))
    # Never narrate old protection, raw incident headlines or unbounded paragraphs.
    if not r.direct_protection:lines=[(s,ids) for s,ids in lines if not PROTECTION_WORDS.search(s)]
    lines=[(polish(re.sub(r'([।.?])\1+',r'\1',s),registry,bn),ids) for s,ids in lines]
    if intent=='service_detail':
        lines=service_lines(safe,lines,c,r,registry,facts)
        if ASKS_OPINION.search(safe) and r.product in {'fdr','dps'}:question='শুনবেন?' if bn else 'Shall I?'
    if intent=='services_list' and registry.get('bank:'+str(c.institution_id)):
        groups=group_line(details(facts,c.institution_id),registry['bank:'+str(c.institution_id)].text,bn)
        if groups:lines=[groups]
    if intent!='compare' and len(lines)>1:
        name=registry.get('bank:'+str(c.institution_id))
        if name:
            # Lead with the bank: a general term's meaning follows the bank's own facts.
            if intent not in {'explain_term','service_detail'}:
                general=lambda row:bool(row[1]) and all(facts.get(fid,{}).get('kind')=='term' for fid in row[1])
                lines=[row for row in lines if not general(row)]+[row for row in lines if general(row)]
            # Say the bank name once, in the first sentence that carries it.
            named=False
            for i,(sentence,ids) in enumerate(lines):
                # After "<bank>কে … বলেছে।" or "<bank> যাত্রা শুরু করে …" the next sentence says "ব্যাংকটির".
                if bn and i==1 and lines[0][0].startswith((name.text+'কে ',name.text+' যাত্রা শুরু করে ')) and sentence.startswith(polish(name.text+'ের ',{},bn)):
                    lines[i]=('ব্যাংকটির '+sentence[len(polish(name.text+'ের ',{},bn)):],ids);named=True;continue
                for prefix in (polish(name.text+'ের ',{},bn),name.text+"'s ",name.text+' '):
                    if sentence.startswith(prefix):
                        if named:
                            sentence=sentence[len(prefix):]
                            # "Eastern Bank is …" said twice becomes "It is …", not "Is …".
                            if not bn and prefix==name.text+' ' and EN_VERB.match(sentence.lower()):sentence='It '+sentence
                        named=True;break
                # An English clause that starts with a verb needs a subject.
                if not bn and EN_VERB.match(sentence):sentence=('It ' if named else name.text+' ')+sentence;named=True
                if bn and sentence.startswith('প্রতিষ্ঠিত হয়'):sentence='ব্যাংকটি '+sentence
                if i and not bn and sentence:sentence=sentence[0].upper()+sentence[1:]
                lines[i]=(sentence,ids)
    if bn:lines=merge_rates(lines,facts,[t.text for t in registry.values() if t.kind=='bank'])
    if intent=='service_detail':lines=date_once(lines)
    award_open=any(facts.get(i,{}).get('kind')=='award' for _,ids in lines for i in ids)
    closing=answers.closing(intent,safe,bank_status(facts,c.institution_id),bn,award_open,'cmp:0' in registry,not c.institution_id)
    if closing is not None:question=closing
    if 'meta:range' in registry:question=''
    if getattr(r,'missing_second',False) and intent=='compare' and lines:
        # The second bank's name was lost in speech: say so, show this bank against others, ask for the name.
        lines=[(('অন্য ব্যাংকের নামটা বুঝতে পারিনি।' if bn else "I missed the other bank's name."),[]),*lines]
        question='কোন ব্যাংকের সাথে মিলিয়ে দেখবেন?' if bn else 'Which bank should I compare it with?'
    chosen,pending=paginate(lines,question,c.language,split=intent in {'service_detail','bank_figures','bank_overview','bank_condition','bank_history','insurance'} or 'cmp:0' in registry)
    if pending:question,buttons=next_steps(intent,c,id,more=True)
    if pending and getattr(r,'missing_second',False) and intent=='compare':question='কোন ব্যাংকের সাথে মিলিয়ে দেখবেন?' if bn else 'Which bank should I compare it with?'
    used=list(dict.fromkeys(fid for _,ids in chosen for fid in ids))
    a=controls(intent,c,' '.join(s for s,_ in chosen),question,buttons).model_copy(update={'used_fact_ids':used,'sentence_fact_ids':[ids for _,ids in chosen]})
    if intent=='unclear' and model and not model.error:c=c.model_copy(update={'misses':min(2,c.misses+1)})
    elif model is None or not model.error:c=c.model_copy(update={'misses':0})
    trace.append(dict(stage='CHECK',model='code',ms=0,status='repaired' if repaired else 'ok',reason=','.join(repaired) if repaired else 'fact_tokens',sentence_repairs=len(repaired)))
    if fallback_reason:trace.append(dict(stage='FALLBACK',model='template',ms=0,status='used',reason=fallback_reason))
    used_facts=[{**f,'text_bn':card_text(f,'bn'),'text_en':card_text(f,'en')} for f in facts.values()]
    result=render(a,c,used_facts,trace,'template' if fallback_reason else 'code')
    result['protocol']=2;result['sentence_repairs']=len(repaired)
    if intent=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
    tail=None
    if pending:
        tail={'reply':' '.join(s for s,_ in pending),'sentence_fact_ids':[ids for _,ids in pending],'next_question':next_steps(intent,c,id)[0],'buttons':next_steps(intent,c,id)[1],'intent':intent}
        result['_all_facts']=used_facts
    def audit(owned):
        turn_id=uuid.uuid4().hex
        for step in trace:
            if step['stage'] in {'PLAN','FALLBACK','CHECK'}:
                usage=model.usage if model and step['stage']=='PLAN' else {}
                owned.add(AppModelCall(turn_id=turn_id,stage=step['stage'],model=step['model'],latency_ms=step['ms'],status=step['status'],input_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens'),failure_reason=(step.get('reason') or '')[:255] if step['status'] not in {'ok','skipped'} else None))
        owned.flush()
    await call(db,audit)
    return await finish(result,safe,id,memory,db,started,tail)
