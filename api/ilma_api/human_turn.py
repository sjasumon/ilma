"""Resolved, single-call token turns with local sentence repair and sourced cards."""
import asyncio,copy,hashlib,json,re,time,uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
from ilma_api import settings
from ilma_api.database_tasks import call
from ilma_api.human_memory import load,redact_user,save,token
from ilma_api.human_resolver import resolve
from ilma_api.human_tokens import build_registry,fill,TOKEN,FactToken,card_text,material,BANNED,PROTECTION_WORDS,PRODUCTS as PRODUCT_LABEL,number as number_text,product as product_name,term as term_text,rating_words
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
        return ('এফডিআর বা ডিপিএসের সুদ শুনবেন?' if bn else 'Would you like FDR or DPS rates?'),['fdr','dps']
    if intent=='bank_reasons':return ('আর্থিক হিসাব, না আগের ঘটনা শুনবেন?' if bn else 'Would you like financial figures or past events?'),['figures','history']
    if intent=='service_detail':return ('অন্য ব্যাংকের সাথে মিলিয়ে দেখবেন, না অন্য সেবা শুনবেন?' if bn else 'Compare with other banks, or hear another service?'),['compare','services']
    if intent in {'unclear','out_of_scope'}:return ('আবার বলবেন, না অন্য ব্যাংক দেখবেন?' if bn else 'Ask again, or choose another bank?'),['listen','ask_bank']
    return ('ব্যাংকের সেবাগুলো শুনবেন, না অন্য ব্যাংক দেখবেন?' if bn else 'Would you like services or another bank?'),['services','ask_bank']


def rounded(value):
    return format(Decimal(str(value)).quantize(Decimal('1'),rounding=ROUND_HALF_UP),'f')

def profit_tokens(found,facts,bank,bn):
    """A direct profit question: the year, spoken in whole crore, and the change from the previous year."""
    v=found['values'];value=Decimal(str(v['value']));crore=abs(value)/10000000
    amount=rounded(crore) if crore>=100 else format(crore.normalize(),'f');year=v['period_end'][:4];loss=value<0
    text=f"নিট {'লোকসান' if loss else 'মুনাফা'} {year} সালে প্রায় {amount} কোটি টাকা" if bn else f"Net {'loss' if loss else 'profit'} in {year} was about {amount} crore taka"
    tokens={'asked:figure':FactToken(text,(found['fact_id'],),bank,'figure')}
    change=next((f for f in facts.values() if f['institution_id']==bank and f['kind']=='figure' and f['values'].get('metric')=='profit_change'),None)
    if change and not loss:
        amount=abs(Decimal(str(change['values']['value'])));up=change['values']['value']>=0
        text=f"আগের বছরের তুলনায় মুনাফা প্রায় {rounded(amount)}% {'বেড়েছে' if up else 'কমেছে'}" if bn else f"That is about {rounded(amount)}% {'more' if up else 'less'} than the previous year"
        tokens['asked:change']=FactToken(text,(change['fact_id'],),bank,'figure')
    return tokens

def details(facts,bank):
    return {f['values']['field']:f for f in facts.values() if f['kind']=='profile_detail' and f['institution_id']==bank}

def npl_period_tokens(facts,bank,bn,asked):
    """Two periods exist only when an interim figure is stored; each is then named."""
    d=details(facts,bank);found=d.get('interim_npl')
    if not found:return {}
    year=next(f['values']['period_end'][:4] for f in facts.values() if asked.fact_ids and f['fact_id']==asked.fact_ids[0])
    end=date.fromisoformat(found['values']['as_of'])
    return {'asked:figure':FactToken(asked.text+(f', {year} সালের হিসাবে' if bn else f' for {year}'),asked.fact_ids,bank,'figure'),
     'asked:interim':FactToken(f"{end.year} সালের প্রথম {end.month} মাসে হার {found['values']['value']}%" if bn else f"For the first {end.month} months of {end.year}, it is {found['values']['value']}%",(found['fact_id'],),bank,'figure')}

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
    if r.intent=='compare' and r.product is None:r=replace(r,product='fdr')
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
    comparisons=comparison_facts(db,r.bank_id,r.product or 'fdr',r.tenor,r.basis,r.compare_bank_ids,r.network,r.tier) if r.intent=='compare' else []
    if comparisons and r.tenor is None:
        reference=comparisons[0]['values'].get('comparison_term')
        if reference:c=c.model_copy(update={'tenor':reference});r=replace(r,tenor=reference)
    registry,facts=build_registry(packs,comparisons,c.language,r.direct_protection)
    if r.requested_metric and r.intent=='bank_figures':
        requested=next((f for f in facts.values() if f['institution_id']==r.bank_id and f['kind']=='figure' and f['values'].get('metric')==r.requested_metric),None)
        if requested:
            registry['asked:figure']=registry['value:'+requested['fact_id']]
            if r.requested_metric=='net_profit':registry.update(profit_tokens(requested,facts,r.bank_id,c.language=='bn'))
            elif 'f:'+requested['fact_id'] in registry:registry['asked:meaning']=registry['f:'+requested['fact_id']]
    if r.requested_metric=='npl_ratio' and r.intent=='bank_figures' and 'asked:figure' in registry:registry.update(npl_period_tokens(facts,r.bank_id,c.language=='bn',registry['asked:figure']))
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
    if r.product and not offers and r.bank_id and not notes:
        proof=next((f for f in facts.values() if f['kind']=='inventory' and f['institution_id']==r.bank_id),None)
        if proof:
            from ilma_api.human_tokens import PRODUCTS as LABEL
            label=LABEL.get(r.product,('এই সেবা','this service'))
            phrase=f'{label[0]}ের প্রকাশিত তথ্য এখনো আমাদের কাছে নেই' if c.language=='bn' else f'published {label[1]} information is not yet in our collection'
            fid='coverage:product:'+str(r.bank_id)+':'+r.product
            facts[fid]={'fact_id':fid,'institution_id':r.bank_id,'kind':'coverage','text_bn':phrase if c.language=='bn' else 'এই সেবার তথ্য আমাদের সংগ্রহে নেই','text_en':phrase if c.language=='en' else 'This service is absent from the imported collection','values':{'product_type':r.product},'source':{**proof['source'],'quote':'Derived coverage of imported product rows, not a claim that the bank does not offer this service'}}
            registry['gap:product']=FactToken(phrase,(fid,),r.bank_id,'gap')
    if r.intent=='compare' and r.product:
        # Name each compared bank that lacks the product; the others keep their rows.
        from ilma_api.human_tokens import PRODUCTS as LABEL
        label=LABEL.get(r.product,('এই সেবা','this service'))
        present={f['institution_id'] for f in comparisons}
        for bank_id in ids:
            if bank_id in present or 'bank:'+str(bank_id) not in registry:continue
            phrase=f'{label[0]}ের প্রকাশিত তথ্য এখনো আমাদের কাছে নেই' if c.language=='bn' else f'published {label[1]} information is not yet in our collection'
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
            if rest.startswith('Net '):return name+"'s n"+rest[1:]
            if rest[:1].isupper() and not EN_VERB.match(rest.lower()):return name+"'s "+rest
        return sentence
    return sentence

def bank_status(facts,bank_id):
    for f in facts.values():
        if f.get('kind')=='status' and f.get('institution_id')==bank_id:
            return f.get('status',{}).get('code') or f.get('values',{}).get('status','no_data')
    return 'no_data'

def introduction(db,c,registry,facts):
    """First answer about a strong bank: name, founding year if quoted, and one confirmed award."""
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    if not name or bank_status(facts,c.institution_id)!='strong':return [],{}
    founded=next((f for f in facts.values() if f.get('kind')=='profile' and f.get('institution_id')==c.institution_id and f['values'].get('field')=='founded_year'),None)
    from ilma_api.awards import intro_award,phrase,fact
    try:found=intro_award(db,c.institution_id)
    except Exception:found=None  # The awards tables may not be loaded yet.
    if not founded and not found:return [],{}
    ids=[founded['fact_id']] if founded else [];extra={}
    if found:
        award,awarder,sources=found;item=fact(award,awarder,sources,c.language);ids.append(item['fact_id']);extra[item['fact_id']]=item
    if not founded:return [(phrase(award,awarder,c.language,name.text),ids)],extra
    year=str(founded['values']['value'])
    if bn:
        text=f"{name.text} যাত্রা শুরু করে {year.translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯'))} সালে"
        text+=f", আর {phrase(award,awarder,'bn')}" if found else '।'
    else:
        text=f"{name.text} was established in {year}"
        text+=', and '+phrase(award,awarder,'en')[0].lower()+phrase(award,awarder,'en')[1:] if found else '.'
    return [(text,ids)],extra

def award_answer(db,c,registry):
    from ilma_api.awards import rows,phrase,fact,HIGH_RISK
    from ilma_api.report_card import get_institution_report_card
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    label=name.text if name else ''
    try:found=rows(db,c.institution_id)[:3]
    except Exception:found=[]
    lines=[];items=[]
    for index,(award,awarder,sources) in enumerate(found):
        item=fact(award,awarder,sources,c.language);items.append(item)
        lines.append((phrase(award,awarder,c.language,label if index==0 else None),[item['fact_id']]))
    if not lines:lines.append((polish(label+'ের ',{},True)+'যাচাই করা কোনো পুরস্কারের তথ্য আমাদের কাছে নেই।' if bn else f"We have no verified award information for {label}.",[]))
    status=((get_institution_report_card(db,c.institution_id) or {}).get('status') or {}).get('code')
    if status=='high' and found:lines.append((HIGH_RISK[0 if bn else 1],[]))
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

ASKS_FIGURE=re.compile(r'সুদ|হার|মুনাফা|ফি(?=[\s,।?]|$)|কত|rates?\b|interest|profit|\bfees?\b|charges?\b',re.I)
ASKS_OPINION=re.compile(r'ভালো|ভাল(?=[\s,।?]|$)|লাভজনক|\bgood\b|\bworth\b|\bbetter\b|suitable|\boption\b',re.I)
def service_lines(text,lines,c,r,registry,facts):
    """Open a product answer as asked: what it is, how its rates vary, or that the choice is the user's."""
    bn=c.language=='bn';name=registry.get('bank:'+str(c.institution_id))
    rows=[facts[i] for _,ids in lines for i in ids if facts.get(i,{}).get('kind')=='service']
    if not name or not rows:return lines
    terms=[row for row in lines if row[1] and all(facts.get(i,{}).get('kind')=='term' for i in row[1])]
    lines=[row for row in lines if row not in terms]
    whose=polish(name.text+'ের ',{},True) if bn else name.text+"'s "
    v=rows[0]['values'];card=r.product=='card';label=PRODUCT_LABEL.get(r.product,('সেবা','service'))
    deposit=r.product in {'fdr','dps'}
    amounts=sorted({f['values']['rate'] for f in rows if f['values'].get('rate') is not None})
    lead=[];frame=[]
    if ASKS_OPINION.search(text):
        lead.append((('এটি ভালো কি না সেটা আপনার সিদ্ধান্ত, আমি পরামর্শ দিই না।' if bn else 'That decision is yours; I do not give advice.'),[]))
    elif deposit and not r.tenor and not ASKS_FIGURE.search(text):
        word=next((facts[i] for row in terms for i in row[1]),None) or next((f for f in facts.values() if f.get('kind')=='term' and f['fact_id'].split(':',1)[-1].casefold() in {label[1].casefold(),label[0]}),None)
        if word:
            meaning=word['text_bn' if bn else 'text_en'].rstrip('।.')
            lead.append(((f'{label[0]} মানে {meaning}।' if bn else f'{label[1]} means {meaning[:1].lower()+meaning[1:]}.'),[word['fact_id']]))
    if not lead and not r.tenor and len(rows)>1 and len(amounts)>1 and (deposit or card):
        schemes=len({product_name(f['values'],bn) for f in rows})>1
        profit=v.get('basis')=='islamic'
        if card:frame=[(f'{whose}কার্ডের বার্ষিক ফি কার্ডের ধরন অনুযায়ী আলাদা।' if bn else f'{whose}annual fees vary by card.',[])]
        elif schemes:
            low,high=number_text(amounts[0]),number_text(amounts[-1])
            frame=[(f"{whose}{label[0]}ের {'আনুমানিক মুনাফা' if profit else 'সুদ'} মেয়াদ ও স্কিমভেদে {low}% থেকে {high}%।" if bn else f"{whose}{label[1]} {'profit rates' if profit else 'rates'} run from {low}% to {high}% by scheme and term.",[f['fact_id'] for f in rows])]
        else:frame=[(f"{whose}{label[0]}ের {'আনুমানিক মুনাফা' if profit else 'সুদ'} মেয়াদের ওপর নির্ভর করে।" if bn else f"{whose}{label[1]} {'profit rates' if profit else 'rates'} depend on the term.",[])]
    others=[row for row in lines if not any(facts.get(i,{}).get('kind')=='service' for i in row[1])]
    if card and len(rows)>1:lines=[fee_list(rows,whose,bn),*others]
    elif deposit and len(rows)>1 and len(amounts)==1 and not r.tenor and not any(f['values'].get('dated') for f in rows):lines=[one_rate(rows,whose,bn),*others]
    if len(rows)>1 and r.tenor:lines=standard_named(lines,facts,bn)
    conditions=[re.search(r'plus (\d+)% VAT',f['source'].get('condition') or '') for f in rows]
    if card and all(conditions):lines=[*lines,(f'এই ফির সঙ্গে {conditions[0][1]}% ভ্যাট প্রযোজ্য হতে পারে।' if bn else f'{conditions[0][1]}% VAT may apply to the fee.',[rows[0]['fact_id']])]
    # The framing sentence says no more than the list, so the list keeps the room.
    said=' '.join(s for s,_ in [*lead,*frame,*(merge_rates(lines,facts,[name.text]) if bn else lines)])
    if len(pronounce(said+' '+next_steps('service_detail',c,0)[0],c.language).split())>LIST_WORDS:frame=[]
    if frame and card and len(rows)>1:
        head=lines[0][0];cut=head.index(': ')+2
        lines=[((head[cut:] if bn else 'They are '+head[cut:]),lines[0][1]),*lines[1:]]
    return lead+frame+lines

def fee_list(rows,whose,bn):
    """Card fees as one list, so a bank's main cards fit one spoken answer."""
    names=[product_name(f['values'],True).removesuffix(' কার্ড') if bn else ' '.join(dict.fromkeys(x for x in (f['values'].get('network'),f['values'].get('tier')) if x)) for f in rows]
    unit='টাকা' if bn else 'taka'
    text=(f'{whose}কার্ডের বার্ষিক ফি: ' if bn else f'{whose}annual card fees: ')+', '.join(f"{name} {number_text(f['values']['rate'])} {unit}" for name,f in zip(names,rows))
    dates=sorted({f['values']['doc_date'] for f in rows})
    if all(f['values'].get('dated') for f in rows):
        when=[format_date(date.fromisoformat(d),bn) for d in dates[-2:]]
        text+=f", {' ও '.join(when)}-এর তালিকা অনুযায়ী" if bn else f", schedule dated {' and '.join(when)}"
    return (text+('।' if bn else '.'),[f['fact_id'] for f in rows])

def one_rate(rows,whose,bn):
    """Several products at one rate read as one sentence with the rate once."""
    rate=number_text(rows[0]['values']['rate'])
    if bn:
        parts=[f"{product_name(f['values'],True)}ে {term_text(f['values'],True)}" for f in rows]
        return (f"{whose}{', '.join(parts)} মেয়াদে সুদ {rate}%।",[f['fact_id'] for f in rows])
    parts=[f"{product_name(f['values'],False)} for {term_text(f['values'],False)}" for f in rows]
    return (f"{whose[:-3] if whose.endswith(chr(39)+'s ') else whose} pays {rate}% on its {', '.join(parts)}.",[f['fact_id'] for f in rows])

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

def fit_overview(lines,question,c,registry,facts,key):
    """Keep status, capital and loan quality in one answer: short clauses, then drop extras."""
    bn=c.language=='bn';fits=lambda rows:len(pronounce(' '.join(s for s,_ in rows)+' '+question,c.language).split())<=45
    if fits(lines):return lines
    def short(sentence,ids):
        found=[facts.get(i,{}) for i in ids]
        if len(found)!=1:return sentence
        f=found[0];v=f.get('values',{});good=bank_status(facts,c.institution_id)=='strong'
        name=registry.get('bank:'+str(c.institution_id));named=bool(name) and sentence.startswith(name.text)
        if f.get('kind')=='status' and good:return (polish(name.text+'ের ',{},True)+'অবস্থা ভালো।' if bn else name.text+' is in good condition.') if named else sentence
        if f.get('kind')=='figure' and v.get('metric')=='crar' and v['value']*100>=v.get('minimum_percent',12.5):return 'নিজের মূলধন ন্যূনতম চাহিদার ওপরে আছে।' if bn else 'Its own capital exceeds the minimum.'
        if f.get('kind')=='figure' and v.get('metric')=='npl_ratio' and v['value']<=.03:return 'দেওয়া ঋণের খুব সামান্য অংশ নিয়ে পরিশোধের সমস্যা হচ্ছে।' if bn else 'Only a small share of lending has repayment problems.'
        if f.get('kind')=='peer' and v.get('metric')=='rating':return (f"রেটিং সংস্থা ব্যাংকটিকে {rating_words(v['grade'])} দিয়েছে।" if bn else f"Its credit rating is {v['grade']}.")
        return sentence
    shortened=[];said=set()
    for s,ids in lines:
        # The model may word one fact twice; the short form would then repeat exactly.
        if ids and set(ids)<=said:continue
        said.update(ids);shortened.append((short(s,ids),ids))
    lines=shortened
    required=set(recommended(c.last_intent,c,registry,facts,key));keep={i for name in required for i in registry[name].fact_ids}
    # A dated result takes the place of the plain capital sentence when room is short.
    interim={i for _,ids in lines for i in ids if facts.get(i,{}).get('kind')=='profile_detail'}
    if interim:keep={i for i in keep if facts[i].get('values',{}).get('metric')!='crar'}|interim
    index=len(lines)-1
    while index>0 and not fits(lines):
        if not set(lines[index][1])&keep:lines.pop(index)
        index-=1
    return lines

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
        if intent=='bank_figures' and 'asked:figure' in registry:return [name for name in ('asked:figure','asked:interim','asked:meaning','asked:change') if name in registry]
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
            selected=[f for f in selected if f['values']['attribute']=='annual_fee' and (not c.network or f['values']['network']==c.network) and (not c.tier or f['values']['tier']==c.tier)]
            # Staff, co-brand and flexi variants stay on the card list, not in the answer.
            selected=[f for f in selected if f['values'].get('variant')=='main'] or selected
            return available(selected)[:6]+(['note:waiver'] if 'note:waiver' in registry else [])
        if c.product in {'fdr','dps'}:selected=sorted(selected,key=deposit_order)
        return (['gap:term'] if 'gap:term' in registry else [])+available(selected)[:8]
    if intent=='compare':
        if 'gap:term' in registry:return ['gap:term']+recommended('service_detail',c,registry,facts,key)[1:3]
        return ['row:'+str(i)+'.offer' for i in range(4) if 'row:'+str(i)+'.offer' in registry]+[name for name in registry if name.startswith('gap:compare:')]
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
        prefix='⟨'+bank+'⟩'+('ের ' if c.language=='bn' and item.kind in {'status','service','figure','service_note'} else ' ') if bank in registry and (not lines or intent in {'compare'}) else ''
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
    if memory.get('protocol')!=2:
        memory={k:v for k,v in memory.items() if k not in {'last_result','pending_reply','pending_facts','last_next'}}
        memory['last_turns']=[]
    memory['protocol']=2
    safe=redact_user(text);selected=exact_choice(safe,c,memory,choice)
    if memory.get('pending_reply') and re.fullmatch(r'হ্যাঁ|জি|yes|yeah',safe.strip(' .!?।'),re.I):selected='more'
    if selected=='yes' and memory.get('pending_reply'):selected='more'
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
    if context.audio_truncated:
        a=controls('unclear',c,'শেষ অংশটা শুনতে পাইনি।' if c.language=='bn' else 'I may have missed the ending.','প্রশ্নটি ছোট করে আবার বলবেন?' if c.language=='bn' else 'Could you ask a shorter question?',['listen','ask_bank'])
        result=render(a,c,[],trace,'code');result['audio_truncated']=True
        return await finish(result,safe,id,memory,db,started)
    forced={'detail':'bank_reasons','figures':'bank_figures','history':'bank_history','services':'services_list','compare':'compare','insurance':'insurance'}.get(selected)
    if selected in {'fdr','dps','card','home_loan'}:
        c=c.model_copy(update={'product':selected,'tenor':None if selected!=c.product else c.tenor,'network':c.network if selected=='card' else None,'tier':c.tier if selected=='card' else None});forced='service_detail'
    if selected and selected.startswith('bank_'):
        peers=memory.get('clarify_candidates') or c.compare_bank_ids;index=int(selected[-1])-1
        if index<len(peers):c=c.model_copy(update={'institution_id':peers[index],'product':None,'tenor':None,'network':None,'tier':None});forced='bank_overview'
    if selected=='ask_bank':c=c.model_copy(update={'institution_id':None,'product':None,'tenor':None,'network':None,'tier':None});forced='unclear'
    if selected=='listen':forced='unclear'
    resolve_started=time.monotonic()
    resolved=resolve(safe,c,banks)
    trace.append(dict(stage='RESOLVER',model='code',ms=round((time.monotonic()-resolve_started)*1000),status='ok'))
    facts_started=time.monotonic()
    r,c,packs,comparisons,registry,facts=await call(db,lambda owned:prepare(owned,safe,c,banks,forced,resolved))
    trace.append(dict(stage='FACTS',model='database',ms=round((time.monotonic()-facts_started)*1000),status='ok'))
    if r.intent=='repeat' and memory.get('last_result'):return await repeat_turn(c,id,memory,db,trace,started)
    from ilma_api.other_banks import find_other_bank
    unknown=find_other_bank(safe)
    if unknown:
        result=render(controls('unclear',c,'এই ব্যাংকের তথ্য এখনো যোগ হয়নি।' if c.language=='bn' else 'Information for this bank has not been added yet.',*next_steps('unclear',c,id)),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if r.confirm_ids:
        memory['clarify_candidates']=r.confirm_ids
        options=[{'value':'bank_'+str(i+1),'label':next(b['name_bn' if c.language=='bn' else 'name_en'] for b in banks if b['id']==value)} for i,value in enumerate(r.confirm_ids)]
        question=(' নাকি '.join(o['label'] for o in options)+' বলছেন?' if c.language=='bn' else 'Did you mean '+' or '.join(o['label'] for o in options)+'?')
        result=render(controls('unclear',c,question),c,[],trace,'code');result['next']={'question':question,'options':options}
        return await finish(result,safe,id,memory,db,started)
    if r.bank_id is None and (selected=='ask_bank' or r.intent in {'bank_overview','bank_condition','bank_reasons','bank_figures','bank_profile','bank_history','bank_awards','services_list','service_detail'}):
        question='কোন ব্যাংকের কথা জানতে চান?' if c.language=='bn' else 'Which bank would you like to know about?'
        result=render(controls('unclear',c,'',question,['listen','end']),c,[],trace,'code')
        return await finish(result,safe,id,memory,db,started)
    if r.intent=='bank_awards' and not selected:
        # Awards are answered by code from sourced rows; the model never names them.
        lines,award_facts=await call(db,lambda owned:award_answer(owned,c,registry))
        question,buttons=next_steps('bank_awards',c,id)
        a=controls('bank_awards',c,' '.join(t for t,_ in lines),question,buttons).model_copy(update={'used_fact_ids':[f for _,ids in lines for f in ids],'sentence_fact_ids':[ids for _,ids in lines]})
        result=render(a,c,award_facts,trace,'code')
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
    model=None;fallback_reason=None;repaired=[]
    # Every sentence of these answers is a stored value, so code writes them: each
    # rephrasing of a question then gets the same facts in the same order.
    code_owned=bool(r.product) and (forced or r.intent)=='service_detail' or (forced or r.intent)=='bank_figures' and 'asked:figure' in registry or (forced or r.intent)=='bank_profile' and 'asked:founded' in registry
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
    controls_map={
      'advice_request':('কোন ব্যাংকে টাকা রাখবেন সেটা আপনার সিদ্ধান্ত, আমি পরামর্শ দিই না। তবে ব্যাংকের অবস্থা আর সুদ পাশাপাশি বোঝাতে পারি।','That decision is yours; I do not give advice. I can explain bank conditions and rates side by side.'),
      'best_bank':('কোন ব্যাংক বেছে নেবেন তা আপনার সিদ্ধান্ত। আমি প্রকাশিত তথ্য পাশাপাশি বুঝিয়ে বলতে পারি।','Choosing a bank is your decision. I can explain the published information side by side.'),
      'out_of_scope':('আমি ব্যাংকের তথ্য নিয়ে সাহায্য করতে পারি।','I can help with bank information.'),
      'unclear':('প্রশ্নটা একটু অন্যভাবে বলবেন?' if model and not model.error else 'এখন উত্তর সাজাতে সমস্যা হচ্ছে।','Could you ask that another way?' if model and not model.error else 'I am having trouble preparing that answer right now.'),
      'smalltalk':('আপনাকেও ধন্যবাদ। আবার জানতে চাইলে মাইক চাপুন।' if re.search(r'ধন্যবাদ|thank',safe,re.I) else 'আমি ইলমা। ব্যাংকের তথ্য জানতে সাহায্য করব।','Thank you. Tap the microphone whenever you have another question.' if re.search(r'ধন্যবাদ|thank',safe,re.I) else 'Hello, I am Ilma. I can help with bank information.'),
      'stop':('পড়া থামালাম।','I have stopped speaking.')}
    if intent in controls_map:
        lines=[(controls_map[intent][0 if bn else 1],[])]
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
    # The opening is for general questions; "মূলধন কেমন?" answers the metric directly.
    if intent in {'bank_overview','bank_condition'} and not r.requested_metric and c.institution_id and c.institution_id not in memory.get('introduced_banks',[]):
        intro,extra=await call(db,lambda owned:introduction(owned,c,registry,facts))
        if intro:
            founded={fid for _,ids in intro for fid in ids}
            lines=intro+[(s,ids) for s,ids in lines if not set(ids)&founded]
            facts.update(extra)
        memory['introduced_banks']=[*memory.get('introduced_banks',[]),c.institution_id][-20:]
    if intent in {'bank_overview','bank_condition'}:
        interim=interim_line(details(facts,c.institution_id),bn)
        if interim:
            # The dated result is the news here, so it replaces a founding-year opening and follows the status.
            lines=[row for row in lines if not any(facts.get(i,{}).get('kind')=='profile' for i in row[1])]
            lines=[lines[0],interim,*lines[1:]]
        lines=fit_overview(lines,question,c,registry,facts,id)
    # Never narrate old protection, raw incident headlines or unbounded paragraphs.
    if not r.direct_protection:lines=[(s,ids) for s,ids in lines if not PROTECTION_WORDS.search(s)]
    lines=[(polish(re.sub(r'([।.?])\1+',r'\1',s),registry,bn),ids) for s,ids in lines]
    if intent=='service_detail':lines=service_lines(safe,lines,c,r,registry,facts)
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
    chosen,pending=paginate(lines,question,c.language,split=intent in {'service_detail','bank_figures'})
    if pending:question,buttons=next_steps(intent,c,id,more=True)
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
