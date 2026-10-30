"""Small sourced fact packs and computed peer/service context. No model values."""
from datetime import date,timedelta
from decimal import Decimal,ROUND_HALF_UP
from collections import defaultdict
from types import SimpleNamespace
from statistics import median
import hashlib,json,re,threading,time,copy
from sqlalchemy import inspect
from ilma_api.db import Institution,Fact,Rating,ServiceOffer,BankProfile,BankIncident,InsuranceRule
from ilma_api.report_card import get_institution_report_card
from ilma_api.bank_services import demo_banks,offer_view,compare
from ilma_api.service_terms import matches_term,nearest_term,terms
from ilma_api.rules.reasons import format_date,format_number

_CACHE={};_LOCK=threading.Lock();TTL=60

def clear_cache():
    with _LOCK:_CACHE.clear()


def threshold_config():
    from pathlib import Path
    path=Path(__file__).with_name('rules')/'thresholds.json'
    key=('thresholds',path.stat().st_mtime_ns)
    with _LOCK:
        if key in _CACHE:return _CACHE[key][1]
    value=json.loads(path.read_text())
    with _LOCK:_CACHE[key]=(time.monotonic()+300,value)
    return value


def provenance(source,quote='',page=None):
    if not source:return {}
    return dict(source_id=source.source_id,source_url=source.url,source_title=source.title,page=page or source.page,
                quote=quote,published_at=str(source.published_at) if source.published_at else None,checked=source.checked_by.casefold()=='sumon')


def item(id,bank,kind,bn,en,source,**values):
    return dict(fact_id=id,institution_id=bank,kind=kind,text_bn=bn,text_en=en,source=source,values=values)


def term_facts(text):
    from ilma_api.voice_glossary import TERMS
    from ilma_api.voice_text import normalize_alias
    query=normalize_alias(text);rows=[]
    for aliases,bn,en,*_ in TERMS:
        if any(normalize_alias(alias) in query for alias in aliases):
            rows.append(item('term:'+aliases[0],None,'term',bn,en,dict(source_title='ILMA authored glossary',source_url='https://github.com/sjasumon/ilma/blob/feature/voice-agent/api/ilma_api/voice_glossary.py',quote=bn)))
    return rows[:3]


def latest_figures(db,id):
    rows=db.query(Fact).filter_by(institution_id=id).filter(Fact.period_end<=date.today()).order_by(Fact.period_end.desc(),Fact.fact_id).all()
    latest={}
    for row in rows:
        if row.metric not in latest:latest[row.metric]=row
    return latest


def annual_profit_change(db,id):
    rows=db.query(Fact).filter_by(institution_id=id,metric='net_profit').filter(Fact.period_end<=date.today()).order_by(Fact.period_end.desc()).all()
    if not rows:return None
    current=rows[0]
    previous=next((r for r in rows[1:] if r.period_end.year==current.period_end.year-1 and r.basis==current.basis and r.unit==current.unit),None)
    if previous is None or previous.value<=0:return None
    change=((Decimal(str(current.value))/Decimal(str(previous.value))-1)*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    # An unknown basis may mix group and bank figures, so it needs one source or the
    # current figure's own quote stating this same change.
    if previous.basis in {None,'','unknown'} and previous.source_id!=current.source_id and not any(abs(Decimal(n)-abs(change))<=Decimal('.1') for n in re.findall(r'(\d+(?:\.\d+)?)\s*%',current.quote or '')):return None
    return item('profit-change:'+str(id)+':'+str(current.period_end.year),id,'figure',f'নিট মুনাফার বার্ষিক পরিবর্তন {change} শতাংশ',f'Annual net-profit change is {change} percent',dict(kind='computed',source_url=current.source.url,source_title='Annual profit change computed from published figures',quote='Computed from the cited current and previous annual profit figures',inputs=[provenance(f.source,f.quote) for f in (current,previous)]),metric='profit_change',value=float(change),current=float(current.value),previous=float(previous.value),period_end=str(current.period_end),previous_period_end=str(previous.period_end),basis=current.basis)


def peer_context(db):
    key=('peers',str(db.get_bind().url))
    if db.get_bind().dialect.name=='mysql':
        with _LOCK:
            cached=_CACHE.get(key)
            if cached and cached[0]>time.monotonic():return cached[1]
    peers=[]
    for bank in demo_banks(db,True):
        card=get_institution_report_card(db,bank.id) or {};figures=latest_figures(db,bank.id)
        peers.append(dict(id=bank.id,status=(card.get('status') or {}).get('code','no_data'),figures=figures,name_bn=bank.name_bn,name_en=bank.name_en))
    # Only serialize numbers/source evidence; never cache ORM instances across sessions.
    result={}
    for peer in peers:
        unusual=[]
        for metric,row in peer['figures'].items():
            if row.basis in {None,'','unknown'}:continue
            group=[other for other in peers if other['status']==peer['status'] and metric in other['figures'] and other['figures'][metric].period_end.year==row.period_end.year and other['figures'][metric].basis==row.basis]
            if len(group)<2 or metric not in {'crar','npl_ratio','net_profit'}:continue
            vals=[Decimal(str(p['figures'][metric].value)) for p in group];middle=Decimal(str(median(vals)));value=Decimal(str(row.value))
            rank=1+sum(v<value if metric=='npl_ratio' else v>value for v in vals)
            ids=[p['figures'][metric].fact_id for p in group];sources=[provenance(p['figures'][metric].source,p['figures'][metric].quote) for p in group]
            fid='peer:'+str(peer['id'])+':'+metric+':'+hashlib.sha256('|'.join(ids).encode()).hexdigest()[:10]
            percent=metric in {'crar','npl_ratio'};scale=100 if percent else 1/10000000
            current=float((value*Decimal(str(scale))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP));mid=float((middle*Decimal(str(scale))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
            bn_metric={'crar':'নিজস্ব মূলধন','npl_ratio':'খেলাপি ঋণ','net_profit':'নিট মুনাফা'}[metric]
            en_metric={'crar':'own capital','npl_ratio':'problem loans','net_profit':'net profit'}[metric]
            unit='%' if percent else ' কোটি টাকা';enunit=' percent' if percent else ' crore taka'
            worse=value>middle if metric=='npl_ratio' else value<middle
            unusual.append(item(fid,peer['id'],'peer',f'{bn_metric} {format_number(current,True)}{unit}, একই অবস্থার {len(group)} ব্যাংকের মধ্যমান {format_number(mid,True)}{unit}',f'{en_metric} is {current:g}{enunit}; median for {len(group)} banks with the same condition is {mid:g}{enunit}',
                dict(kind='computed',source_url=sources[0].get('source_url'),source_title='Computed peer comparison',quote='Computed from the cited published inputs',inputs=sources),status=peer["status"],metric=metric,value=current,median=mid,rank=rank,rank_high=1+sum(v>value for v in vals),rank_low=1+sum(v<value for v in vals),group_size=len(group),worse=worse,input_fact_ids=ids,period=str(row.period_end),basis=row.basis,unusual=float(abs(value-middle)/(abs(middle) or 1))))
        result[peer['id']]=unusual
    extras=additional_peer_context(db,peers)
    for peer in peers:
        result[peer['id']]=sorted(result[peer['id']]+extras.get(peer['id'],[]),key=lambda v:(not v['values']['worse'],-v['values']['unusual']))[:3]
    if db.get_bind().dialect.name=='mysql':
        with _LOCK:_CACHE[key]=(time.monotonic()+TTL,result)
    return result


def additional_peer_context(db,peers):
    """Only compare like periods, rating scales and deposit terms/bases."""
    from ilma_api.rules.ratings import normalize_rating,SCALE_INDEX,SCALE
    features={};today=date.today()
    for peer in peers:
        id=peer['id'];rows={}
        current=peer['figures'].get('net_profit')
        if current and current.basis not in {None,'','unknown'}:
            previous=db.query(Fact).filter_by(institution_id=id,metric='net_profit',basis=current.basis).filter(Fact.period_end<current.period_end).order_by(Fact.period_end.desc()).first()
            if previous and previous.period_end.year==current.period_end.year-1 and previous.value>0:
                growth=(Decimal(str(current.value))/Decimal(str(previous.value))-1)*100
                rows['profit_change']=dict(value=growth,lower=False,period=str(current.period_end.year),basis=current.basis,inputs=[current.fact_id,previous.fact_id],sources=[provenance(f.source,f.quote) for f in (current,previous)],label_bn='আগের বছরের তুলনায় মুনাফার পরিবর্তন',label_en='year-on-year profit change',unit='%',grade=None)
        rating=db.query(Rating).filter_by(institution_id=id).filter(Rating.rated_on<=today,Rating.valid_to>=today).order_by(Rating.rated_on.desc()).first()
        grade=normalize_rating(rating.long_term) if rating else None
        if grade:
            rows['rating']=dict(value=Decimal(SCALE_INDEX[grade]),lower=True,period='current',basis='normalized-national-scale',inputs=[rating.fact_id],sources=[provenance(rating.source,rating.quote)],label_bn='রেটিং',label_en='credit rating',unit='',grade=grade)
        for product in ('fdr','dps'):
            offers=service_facts(db,id,product,12,'conventional')
            offers=[f for f in offers if f['values']['unit']=='pct_year' and not f['values']['stale']]
            if offers:
                best=max(offers,key=lambda f:f['values']['rate'])
                rows[product+'_12_rate']=dict(value=Decimal(str(best['values']['rate'])),lower=False,period='published-12-month',basis='conventional',inputs=[best['fact_id']],sources=[best['source']],label_bn=('এক বছরের এফডিআর' if product=='fdr' else 'এক বছরের ডিপিএস')+'ে প্রকাশিত সর্বোচ্চ হার',label_en='highest published one-year '+product.upper()+' rate',unit='%',grade=None)
        # This counts the sourced collection only, never claims no events occurred.
        if inspect(db.get_bind()).has_table('bank_incident'):
            incidents=db.query(BankIncident).filter_by(institution_id=id).filter(BankIncident.first_reported_on>=today-timedelta(days=1096),BankIncident.first_reported_on<=today,BankIncident.status!='single_source').all()
            if incidents:
                evidence=[provenance(link.source,link.quote) for row in incidents for link in row.sources]
                rows['reported_incidents']=dict(value=Decimal(len(incidents)),lower=True,period='last-three-years',basis='sourced-collection-not-status',inputs=[r.incident_id for r in incidents],sources=evidence,label_bn='গত তিন বছরে সংগ্রহে থাকা ঘটনার খবর',label_en='reported incidents in the three-year collection',unit='',grade=None)
        features[id]=rows
    result=defaultdict(list)
    for peer in peers:
        for metric,entry in features[peer['id']].items():
            group=[(p,features[p['id']][metric]) for p in peers if p['status']==peer['status'] and metric in features[p['id']] and features[p['id']][metric]['period']==entry['period'] and features[p['id']][metric]['basis']==entry['basis']]
            if len(group)<2:continue
            values=[e['value'] for _,e in group];mid=Decimal(str(median(values)));value=entry['value'];lower=entry['lower']
            rank=1+sum(v<value if lower else v>value for v in values)
            sources=[s for _,e in group for s in e['sources']];ids=[f for _,e in group for f in e['inputs']]
            fid='peer:'+str(peer['id'])+':'+metric+':'+hashlib.sha256('|'.join(ids).encode()).hexdigest()[:10]
            rounded_value=value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP);rounded_mid=mid.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            display=entry['grade'] or f'{rounded_value:g}{entry["unit"]}'
            median_display=SCALE[int(mid)] if metric=='rating' and mid==int(mid) else f'{rounded_mid:g}{entry["unit"]}'
            result[peer['id']].append(item(fid,peer['id'],'peer',f'{entry["label_bn"]} {display}, একই অবস্থার ব্যাংকগুলোর মধ্যমান {median_display}',f'{entry["label_en"]} is {display}; same-condition peer median is {median_display}',dict(kind='computed',source_url=sources[0].get('source_url') if sources else None,source_title='Computed peer comparison',quote='Computed from cited published inputs',inputs=sources),status=peer["status"],metric=metric,value=float(rounded_value),median=float(rounded_mid),rank=rank,rank_high=1+sum(v>value for v in values),rank_low=1+sum(v<value for v in values),group_size=len(group),worse=value>mid if lower else value<mid,input_fact_ids=ids,period=entry['period'],basis=entry['basis'],unusual=float(abs(value-mid)/(abs(mid) or 1)),grade=entry['grade'],rank_direction='ascending' if lower else 'descending'))
    return result


def offer_item(row,bank,asked_term=None):
    info=terms(row);selected=nearest_term(row,asked_term);age=(date.today()-row.doc_date).days
    number=float(row.value_num) if row.value_num is not None else None
    en=f'{bank.name_en}: {row.product}; {number if number is not None else row.value_text} {row.unit}; {row.condition}; schedule {row.doc_date}'
    bn=f'{bank.name_bn}: {row.product}; {format_number(number,True) if number is not None else row.value_text} {row.unit}; {row.condition}; হারতালিকা {format_date(row.doc_date,True)}'
    entry=item(row.offer_id,bank.id,'service',bn,en,dict(source_url=row.source_url,source_title=row.product,page=row.page,quote=row.quote,published_at=str(row.doc_date),condition=row.condition),product=row.product,product_type=row.product_type,rate=number,unit=row.unit,basis=row.basis,tenor_months=row.tenor_months,selected_tenor=selected,variant=row.variant,asked_tenor=asked_term,nearest=asked_term is not None and not matches_term(row,asked_term),network=row.network,tier=row.tier,stale=bool(row.stale or age>365),dated=age>90,doc_date=str(row.doc_date),**info)
    entry['values']['attribute']=row.attribute
    entry.update(bank_name_bn=bank.name_bn,bank_name_en=bank.name_en)
    return entry


def service_facts(db,id,product=None,tenor=None,basis=None,network=None,tier=None,include_all=False):
    bank=db.get(Institution,id)
    if not bank:return []
    query=db.query(ServiceOffer).filter_by(institution_id=id,hidden=False).filter(ServiceOffer.variant!='excluded',ServiceOffer.doc_date<=date.today())
    if product:query=query.filter_by(product_type=product)
    if basis:query=query.filter_by(basis=basis)
    if product=='card':
        if network:query=query.filter_by(network=network)
        if tier:query=query.filter_by(tier=tier)
    rows=query.order_by(ServiceOffer.product_type,ServiceOffer.doc_date.desc(),ServiceOffer.product,ServiceOffer.offer_id).all()
    rows=[r for r in rows if r.value_num is not None and r.attribute in {'rate','interest_rate','annual_fee','rate_min','sms_alert_fee','maintenance_fee_half_yearly'}]
    if tenor is not None and product in {'fdr','dps'}:rows=[r for r in rows if matches_term(r,tenor)]
    if include_all:return [offer_item(r,bank,tenor) for r in rows]
    if product:return [offer_item(r,bank,tenor) for r in rows[:18]]
    grouped=defaultdict(list)
    for row in rows:grouped[row.product_type].append(row)
    highlights=[]
    priority=['fdr','dps','savings','card','home_loan','auto_loan','personal_loan','loan_against_fdr','account_fee']
    for category in sorted(grouped,key=lambda c:priority.index(c) if c in priority else 99):
        group=grouped[category]
        plain=[r for r in group if not any(w in r.product.lower() for w in ('women','child','senior','premium'))] or group
        if category in {'fdr','dps'}:plain=sorted(plain,key=lambda r:nearest_term(r,None) or 999)
        # All term rows are fetched for a product question. General context keeps
        # one sample per category, so fees cannot crowd out FDR/DPS/savings.
        highlights.append(offer_item(plain[0],bank))
    return highlights[:12]


def card_waiver(db,id,network,tier):
    """The published yearly-transaction waiver of the main card with this network and tier."""
    rows=db.query(ServiceOffer).filter_by(institution_id=id,hidden=False,product_type='card',tier=tier)
    rows=rows.filter_by(network=network) if network else rows
    main=next((r for r in rows if r.attribute=='annual_fee' and r.variant=='main'),None)
    rule=next((r for r in rows if main and r.attribute=='fee_waiver_rule' and r.product==main.product),None)
    found=re.search(r'(\d+)[ -](?:transactions?|times?)\b',rule.value_text or '') if rule else None
    if not found:return None
    return item(rule.offer_id,id,'service_note',f'বছরে {found[1]} বার লেনদেন করলে নবায়ন ফি দিতে হয় না',f'No renewal fee applies after {found[1]} transactions in a year',dict(source_url=rule.source_url,source_title=rule.product,page=rule.page,quote=rule.quote,published_at=str(rule.doc_date),condition=rule.condition))


def service_inventory(db,id):
    rows=db.query(ServiceOffer).filter_by(institution_id=id,hidden=False).filter(ServiceOffer.variant!='excluded',ServiceOffer.doc_date<=date.today()).all()
    if not rows:return None
    from ilma_api.answer_wording import PRODUCTS
    products=sorted({r.product_type for r in rows})
    networks=sorted({r.network for r in rows if r.product_type=='card' and r.network})
    tiers=sorted({r.tier for r in rows if r.product_type=='card' and r.tier})
    urls=sorted({r.source_url for r in rows if r.source_url})
    return item('inventory:'+str(id),id,'inventory','প্রকাশিত সেবার ধরন '+', '.join(PRODUCTS.get(p,(p,p))[0] for p in products),'Published product types include '+', '.join(PRODUCTS.get(p,(p,p))[1] for p in products),dict(kind='computed',source_url=urls[0],source_title='Published product inventory',quote='Derived from visible published product rows',inputs=[dict(source_url=u) for u in urls]),product_types=products,card_networks=networks,card_tiers=tiers)


def comparison_facts(db,anchor,product,tenor=None,basis='conventional',bank_ids=(),network=None,tier=None):
    ids=list(dict.fromkeys([anchor,*bank_ids])) if anchor else list(bank_ids)
    bank_rows=demo_banks(db,True);by_id={bank.id:bank for bank in bank_rows};selected=[]
    # Without a requested term, disclose the shortest available anchor term and
    # compare that term; do not rank a one-year quote against a ten-year quote.
    reference=tenor
    anchor_facts=service_facts(db,anchor,product,None,basis,network,tier) if anchor else []
    if product=='card':
        fees=[f for f in anchor_facts if f['values']['attribute']=='annual_fee' and f['values']['unit']=='bdt']
        if fees:
            network=network or fees[0]['values']['network'];tier=tier or fees[0]['values']['tier']
    if reference is None and product in {'fdr','dps'}:
        available=[f['values']['selected_tenor'] for f in anchor_facts if f['values']['selected_tenor']]
        reference=min(available) if available else None
    for bank in bank_rows:
        if bank_ids and bank.id not in ids:continue
        facts=service_facts(db,bank.id,product,reference,basis,network if product=='card' else None,tier if product=='card' else None)
        if product=='card':facts=[f for f in facts if f['values']['attribute']=='annual_fee' and f['values']['unit']=='bdt']
        if not facts and reference is not None:
            all_terms=service_facts(db,bank.id,product,None,basis,network,tier)
            # Different terms are alternatives, explicitly marked, never same-term ranks.
            def distance(f):
                row=SimpleNamespace(**f['values'],condition=f['source'].get('condition',''))
                selected=nearest_term(row,reference)
                f['values']['selected_tenor']=selected
                return abs((selected or 999)-reference)
            facts=sorted(all_terms,key=distance)[:1]
            for f in facts:f['values'].update(nearest=True,asked_tenor=reference)
        if not facts:continue
        plain=[f for f in facts if not any(w in f['values']['product'].lower() for w in ('women','child','senior','premium'))] or facts
        # Within the same bank, preserve the general-product selector, not a premium slab.
        chosen=plain[0];chosen['values']['comparison_term']=reference
        chosen['values']['term_assumed']=tenor is None and reference is not None
        card=get_institution_report_card(db,bank.id) or {};status=card.get('status') or {}
        chosen['values']['status']=status.get('code','no_data');chosen['values']['status_bn']=status.get('label_bn','অবস্থা যাচাই হয়নি');chosen['values']['status_en']=status.get('label_en','Condition unverified')
        selected.append(chosen)
    same=[f for f in selected if not f['values']['nearest']]
    same.sort(key=lambda f:-(f['values']['rate'] or 0) if product!='card' else f['values']['rate'] or 0)
    current=next((f for f in selected if f['institution_id']==anchor),None)
    others=[f for f in same if f['institution_id']!=anchor][:3]
    if not others:others=[f for f in selected if f['institution_id']!=anchor][:3]
    return ([current] if current else [])+others


def fact_pack(db,id,product=None,tenor=None,basis=None,network=None,tier=None):
    cacheable=db.get_bind().dialect.name=='mysql'
    key=('pack',str(db.get_bind().url),id,product,tenor,basis,network,tier)
    if cacheable:
        with _LOCK:
            cached=_CACHE.get(key)
            if cached and cached[0]>time.monotonic():return copy.deepcopy(cached[1])
    pack=build_fact_pack(db,id,product,tenor,basis,network,tier)
    if cacheable:
        with _LOCK:
            expired=[k for k,v in _CACHE.items() if v[0]<=time.monotonic()]
            for k in expired:_CACHE.pop(k,None)
            if len(_CACHE)>=256:_CACHE.pop(min(_CACHE,key=lambda k:_CACHE[k][0]),None)
            _CACHE[key]=(time.monotonic()+TTL,copy.deepcopy(pack))
    return pack


def build_fact_pack(db,id,product=None,tenor=None,basis=None,network=None,tier=None):
    from ilma_api.voice_agent import bank_summary,bank_figures,insurance
    bank=db.get(Institution,id) if id else None
    if not bank:return {'bank':None,'facts':[],'status':None}
    facts=[];card=get_institution_report_card(db,id) or {};status=card.get('status') or {'code':'no_data','label_bn':'অবস্থা যাচাই হয়নি','label_en':'Condition unverified'}
    for f in bank_summary(db,id)+bank_figures(db,id)+insurance(db,id):
        if any(old['fact_id']==f['fact_id'] for old in facts):continue
        kind='status' if f.get('status') else 'insurance' if f['fact_id'].startswith('insurance:') else 'figure'
        f={**f,'kind':kind,'values':{}}
        stored=db.get(Fact,f['fact_id']);rating=db.get(Rating,f['fact_id'])
        if stored and stored.period_end>date.today():continue
        if rating and rating.rated_on>date.today():continue
        if stored:
            f['values'].update(metric=stored.metric,value=float(stored.value),unit=stored.unit,period=stored.period,period_end=str(stored.period_end),basis=stored.basis)
            f['source']['quote']=stored.quote
        if rating:f['values'].update(metric='rating',grade=rating.long_term,agency=rating.agency,rated_on=str(rating.rated_on),expired=bool(rating.valid_to and rating.valid_to<date.today()),outlook=rating.outlook)
        if f['source'].get('kind')=='rules':
            inputs=card.get('reasons',[]);f['source']={**f['source'],'source_url':next((r.get('source_url') for r in inputs if r.get('source_url')),None),'inputs':inputs}
        if kind=='insurance':
            rule=db.get(InsuranceRule,bank.type)
            f['values'].update(limit=rule.limit_bdt if rule else None,conditional=True,per_person=True,per_bank=True)
            if rule:f['source']=provenance(rule.source,rule.text_en)
        facts.append(f)
    cfg=threshold_config();minimum=(Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer'])))*100
    for f in facts:
        if f['values'].get('metric')=='crar':f['values']['minimum_percent']=float(minimum)
    change=annual_profit_change(db,id)
    if change:facts.append(change)
    if inspect(db.get_bind()).has_table('bank_profile'):
        for row in db.query(BankProfile).filter_by(bank_id=id).filter(BankProfile.as_of<=date.today()).order_by(BankProfile.as_of.desc()):
            if not row.quote or not row.source_url:continue
            facts.append(item(row.fact_id,id,'profile',f'{row.field}: {row.value} ({row.as_of})',f'{row.field}: {row.value} ({row.as_of})',dict(source_url=row.source_url,source_title=bank.name_en+' Annual Report 2025',page=row.page,quote=row.quote),field=row.field,value=row.value,as_of=str(row.as_of)))
    fields={'founded_year','branches','sub_branches','atms','agent_outlets','customers','known_for'}
    missing=sorted(fields-{f['values']['field'] for f in facts if f['kind']=='profile'})
    if missing:
        key=hashlib.sha256('|'.join(missing).encode()).hexdigest()[:10]
        facts.append(item('coverage:profile:'+str(id)+':'+key,id,'coverage','আমাদের উদ্ধৃতিসহ প্রোফাইল সংগ্রহে কিছু ক্ষেত্রের তথ্য এখনো নেই','Some profile fields have no quotation in our imported collection',dict(kind='computed',source_title='Quoted-profile coverage',source_url='https://github.com/sjasumon/ilma/blob/feature/voice-agent/seed/bank_profile.csv',quote='Coverage of imported quotations, not a statement that the bank report omits these fields'),missing_fields=missing))
    if inspect(db.get_bind()).has_table('bank_incident'):
        incidents=db.query(BankIncident).filter_by(institution_id=id).filter(BankIncident.status!='single_source',BankIncident.first_reported_on<=date.today(),BankIncident.last_update_on<=date.today()).all()
        dated=[]
        for row in incidents:
            changes=sorted(row.changes,key=lambda c:c.changed_on)
            latest=changes[-1] if changes else None
            happened=latest.changed_on if latest and latest.status==row.status else row.last_update_on if row.status in {'convicted','acquitted','settled','case_withdrawn'} else row.started_on or row.first_reported_on
            links=sorted(row.sources,key=lambda l:l.source.published_at or date.min,reverse=True)
            if not links:continue
            source=provenance(links[0].source,links[0].quote)
            source['inputs']=[provenance(l.source,l.quote) for l in links]
            facts.append(item(row.incident_id,id,'history',row.title_bn,row.title_en,source,event_date=str(happened),first_reported_on=str(row.first_reported_on),status=row.status,official=row.official,status_effect=False))
        facts.sort(key=lambda f:f['values'].get('event_date',''),reverse=True)
    facts.extend(peer_context(db).get(id,[]));facts.extend(service_facts(db,id,product,tenor,basis,network,tier))
    inventory=service_inventory(db,id)
    if inventory:facts.append(inventory)
    return {'bank':dict(id=id,slug=bank.slug,name_bn=bank.name_bn,name_en=bank.name_en),'status':status,'facts':facts,'product':product,'missing_profile':not any(f['kind']=='profile' for f in facts)}


def compact_pack(pack,language='bn'):
    import re
    priorities={'status':0,'peer':1,'profile':2,'history':3,'figure':4,'insurance':5,'service':6}
    facts=sorted(pack['facts'],key=lambda f:(priorities.get(f['kind'],9),not f.get('values',{}).get('worse',False)))
    selected=[];counts=defaultdict(int);caps={'status':1,'peer':2,'profile':7,'history':3,'figure':5,'insurance':1,'service':10 if pack.get('product') else 3}
    for f in facts:
        if counts[f['kind']]>=caps.get(f['kind'],2):continue
        counts[f['kind']]+=1;selected.append(f)
    bank=dict(pack['bank']) if pack['bank'] else None
    if bank:
        bank['name_en']=re.sub(r'\s+PLC[.]?$','',bank['name_en'],flags=re.I)
        bank['name_bn']=re.sub(r'\s+পিএলসি[.]?$','',bank['name_bn'])
    def clean(text):return re.sub(r'\s*(?:\bPLC\b|পিএলসি)[.]?','',text,flags=re.I)
    return {'bank':bank,'status':pack.get('status'),'missing_profile':pack.get('missing_profile'),
        'overview_focus_fact_id':next((f['fact_id'] for f in selected if f['kind']=='peer' and f['values'].get('worse')),None),
        'available_counts':dict((kind,sum(f['kind']==kind for f in facts)) for kind in caps),
        'facts':[dict(id=f['fact_id'],kind=f['kind'],text=clean(f['text_bn' if language=='bn' else 'text_en']),values={k:v for k,v in f['values'].items() if v is not None and k not in {'first_reported_on','input_fact_ids','unusual'}},quote=(f['source'].get('quote') or '')[:160]) for f in selected]}
