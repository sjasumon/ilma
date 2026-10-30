"""Read-only bank/service views. Hidden offers never cross the API boundary."""
from datetime import date
from ilma_api.service_terms import terms
from ilma_api.card_catalog import card_key,display,condition,numeric
from pathlib import Path
import csv
import json
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Literal
from sqlalchemy.orm import Session
from ilma_api.db import Institution, Fact, Rating, Event, ServiceOffer, InsuranceRule, AppWatchItem
from ilma_api.report_card import get_institution_report_card

DEMO_CODES = {row['code'].lower() for row in csv.DictReader((Path(__file__).resolve().parents[2]/'seed/bank_names.csv').open(encoding='utf-8'))}


def demo_banks(db,include_incident_banks=False):
    codes=DEMO_CODES|({'nbl','islamibank'} if include_incident_banks else set())
    return db.query(Institution).filter(Institution.slug.in_(codes)).all()


def bank_view(db, bank):
    card = get_institution_report_card(db,bank.id)
    return dict(id=bank.id,slug=bank.slug,name_bn=bank.name_bn,name_en=bank.name_en,status=card['status'],aliases=[row.alias for row in bank.aliases])


def source_view(source, quote='', checked_by=None):
    return dict(source_url=source.url,source_title=source.title,published_at=source.published_at,
                page=source.page,quote=quote,checked=(checked_by or source.checked_by).casefold()=='sumon')


def offer_view(row, today=None):
    today = today or date.today()
    result = {**{column.name:getattr(row,column.name) for column in ServiceOffer.__table__.columns
        if column.name not in {'hidden','hidden_reason','checked_by'}},
        'value_num':float(row.value_num) if row.value_num is not None else None,
        'tenor_min_months':terms(row)['tenor_min_months'],
        'tenor_max_months':terms(row)['tenor_max_months'],
        'tenor_options':terms(row)['tenor_options'],
        'stale':row.stale or (today-row.doc_date).days>365,
        'checked':row.checked_by.casefold()=='sumon', 'source_title':row.column_header if row.product_type=='card' and row.column_header else row.product,
        'group_key':f'{row.institution_id}:{row.product}:{row.column_header if row.product_type=="card" else ""}:{row.network or ""}:{row.tier or ""}:{row.tenor_months or ""}:{row.basis}'}

    if row.product_type=='card':
        result.update(display(row),condition_bn=condition(row),condition_en=condition(row,language='en'))
        result['group_key']=card_key(row)
        number=numeric(row)
        if number is not None:result['value_num']=float(number)
    if row.product_type in {'home_loan','auto_loan','personal_loan','loan_against_fdr'}:
        from ilma_api.loan_catalog import decorate
        result=decorate(row,result)
    return result

CARD_ATTRIBUTES=('annual_fee','renewal_fee','fee_waiver_rule','interest_rate','late_fee','cash_advance_fee','foreign_currency_markup','supplementary_card_fee','card_replacement_fee','lounge_access')
CARD_COMPARE={'annual_fee','interest_rate','late_fee','cash_advance_fee','foreign_currency_markup','renewal_fee'}

def card_facts(rows):
    result={key:None for key in CARD_ATTRIBUTES}
    for row in sorted(rows,key=lambda r:(r.stale or (date.today()-r.doc_date).days>365,-r.doc_date.toordinal(),r.offer_id)):
        if row.attribute in result and result[row.attribute] is None:
            view=offer_view(row);view['condition_bn']=condition(row,renewal=any(r.attribute=='renewal_fee' for r in rows));view['condition_en']=condition(row,renewal=any(r.attribute=='renewal_fee' for r in rows),language='en')
            result[row.attribute]=view
    return result

def compare_cards(db,network,tier,primary='annual_fee',basis='conventional'):
    if primary not in CARD_COMPARE:raise HTTPException(422,'Unsupported card comparison fact')
    all_rows=db.query(ServiceOffer).filter_by(product_type='card',basis=basis).all()
    if network:all_rows=[r for r in all_rows if r.network==network]
    if tier:all_rows=[r for r in all_rows if r.tier==tier]
    output=[]
    for bank in demo_banks(db):
        groups={}
        for row in all_rows:
            if row.institution_id==bank.id and not row.hidden and row.variant!='excluded':groups.setdefault(card_key(row),[]).append(row)
        candidates=[]
        for key,rows in groups.items():
            facts=card_facts(rows);annual=facts.get('annual_fee')
            if annual is None:continue
            chosen=facts.get(primary)
            candidates.append({'key':key,'annual':annual,'chosen':chosen,'facts':facts})
        candidates.sort(key=lambda c:(c['annual']['card_printed_name']!='',c['annual']['stale'],c['annual']['card_key']))
        item=bank_view(db,bank)
        if candidates:
            selected=candidates[0];offer=selected['chosen']
            item.update(state='published',offer=offer,facts=selected['facts'],card=selected['annual'],renewal_offer=selected['facts'].get('renewal_fee'),range_max=None,alternatives=[{**c['annual'],'facts':c['facts']} for c in candidates[1:]])
        else:item.update(state='checking' if any(r.hidden and r.institution_id==bank.id for r in all_rows) else 'missing',facts={key:None for key in CARD_ATTRIBUTES},alternatives=[])
        output.append(item)
    def sort(row):
        offer=row.get('offer');value=offer.get('value_num') if offer else None
        # Percentage-only cash charges cannot be ranked as if they were taka.
        if primary=='cash_advance_fee' and offer and offer['unit']!='bdt':value=None
        return (not bool(offer),bool(offer and offer['stale']),value is None,value if value is not None else float('inf'),row['name_bn'])
    output.sort(key=sort)
    result = {'choice':dict(product_type='card',network=network,tier=tier,attribute=primary,compare_by=primary,basis=basis,tenor_months=None),'rows':output,'sort':'lower_cost_first','insurance':None}
    result['unit_note_bn']='টাকার অঙ্ক আগে; শতাংশের ফি আলাদা, সরাসরি তুলনীয় নয়।' if primary=='cash_advance_fee' else ''
    result['unit_note_en']='Taka amounts first; percentage charges are separate and not directly comparable.' if primary=='cash_advance_fee' else ''
    from ilma_api.service_clips import readout
    result['readout']=readout(result)
    from ilma_api.card_explanation import build as explain_card
    result['explanation']=explain_card(result)
    return result


def compare(db, product_type='fdr', tenor_months=None, network=None, tier=None,
            attribute=None, basis='conventional',compare_by=None):
    if product_type in {'home_loan','auto_loan','personal_loan','loan_against_fdr'}:
        from ilma_api.loan_catalog import compare as compare_loans
        return compare_loans(db,product_type,basis)
    if product_type=='card':return compare_cards(db,network,tier,compare_by or attribute or 'annual_fee',basis)
    primary = attribute or ('rate' if product_type in {'fdr','dps','savings'} else 'annual_fee' if product_type=='card'
        else 'maintenance_fee_half_yearly' if product_type=='account_fee' else 'rate_min')
    query = db.query(ServiceOffer).filter_by(product_type=product_type,basis=basis)
    if product_type!='card':network=tier=None
    if network: query=query.filter_by(network=network)
    if tier: query=query.filter_by(tier=tier)
    from ilma_api.service_terms import matches_term
    all_rows = [row for row in query.all() if matches_term(row,tenor_months)]
    rows=[]
    for bank in demo_banks(db):
        candidates=[r for r in all_rows if r.institution_id==bank.id and r.attribute==primary]
        if not candidates and product_type.endswith('_loan'):
            candidates=[r for r in all_rows if r.institution_id==bank.id and r.attribute=='interest_rate']
        visible=[r for r in candidates if not r.hidden and (product_type!='card' or
            r.variant=='main' and r.value_num is not None and (primary not in {'annual_fee','renewal_fee'} or r.unit=='bdt'))]
        item=bank_view(db,bank)
        if visible:
            # Match a plain/general product before premium/targeted variants.
            # Keep all slabs available; do not silently pick the highest rate.
            def published_cost(row):
                if row.value_num is not None:return float(row.value_num)
                if row.value_text=='0' and re.search(r'\bfree\b',row.quote,re.I):return 0
                return float('inf')
            visible.sort(key=lambda r:(any(word in r.product.lower() for word in ('extra','plus','senior','women','million','kotipoti')),-r.doc_date.toordinal(),r.product,published_cost(r),r.condition,r.offer_id))
            selected=visible[0]
            variants=[r for r in candidates if not r.hidden and r.variant=='variant' and r.value_num is not None and r.unit==selected.unit] if product_type=='card' else visible[1:]
            item.update(state='published',offer=offer_view(selected),alternatives=[offer_view(r) for r in variants])
            group=[r for r in all_rows if not r.hidden and r.institution_id==bank.id and r.product==selected.product
                   and r.network==selected.network and r.tier==selected.tier and r.tenor_months==selected.tenor_months
                   and (product_type!='card' or r.column_header==selected.column_header)]
            renewal=next((r for r in group if r.attribute=='renewal_fee'),None)
            high=next((r for r in group if r.attribute=='rate_max'),None)
            item['renewal_offer']=offer_view(renewal) if renewal else None
            item['range_max']=offer_view(high) if high else None
        else:
            # The export converter slugs codes as code.lower() ('dutchbangl')
            # while legacy fixtures use hyphenated slugs ('dutch-bangla-bank');
            # match both spellings so the state is identical on either database.
            slug_key=bank.slug.replace('-','')
            item['state']='checking' if any(r.hidden for r in candidates) else 'not_published' if slug_key in {'dutchbangl','dutchbanglabank'} and product_type in {'fdr','dps','savings'} else 'missing'
        rows.append(item)
    descending=product_type in {'fdr','dps','savings'}
    def sorting_value(row):
        offer=row.get('offer',{})
        if offer.get('value_num') is not None:return offer['value_num']
        if offer.get('value_text')=='0' and re.search(r'\bfree\b',offer.get('quote',''),re.I):return 0
        return None
    rows.sort(key=lambda row:(row['state']!='published', sorting_value(row) is None,
        (-1 if descending else 1)*(sorting_value(row) or 0),row['name_bn']))
    rule=db.get(InsuranceRule,'bank') if product_type in {'fdr','dps','savings'} else None
    return dict(choice=dict(product_type=product_type,tenor_months=tenor_months,network=network,tier=tier,attribute=primary,basis=basis),
        rows=rows,sort='higher_rate_first' if descending else 'lower_cost_first',
        insurance=dict(text_bn=rule.text_bn,text_en=rule.text_en,**source_view(rule.source)) if rule and rule.source else None)


def make_router(get_db):
    router=APIRouter()
    def institution(db,id):
        row=db.get(Institution,id)
        if not row:raise HTTPException(404,'Institution not found')
        return row

    @router.get('/v1/institutions/{id}/figures')
    def figures(id:int,db:Session=Depends(get_db)):
        institution(db,id)
        rows=db.query(Fact).filter_by(institution_id=id).order_by(Fact.period_end.desc(),Fact.metric).all()
        threshold=json.loads((Path(__file__).parent/'rules/thresholds.json').read_text())['crar_min']
        return [dict(fact_id=r.fact_id,metric=r.metric,value=float(r.value),unit=r.unit,period=r.period,period_end=r.period_end,legal_min=threshold if r.metric=='crar' else None,
            basis=r.basis,checked_on=r.checked_on,**source_view(r.source,r.quote,r.checked_by)) for r in rows]

    def watch_identity(request):
        import hashlib,hmac
        from ilma_api import settings
        value=request.headers.get('x-ilma-device','')
        if not re.fullmatch('[a-zA-Z0-9_-]{20,80}',value):raise HTTPException(400,'Device identifier required')
        return hmac.new(settings.VOICE_LOG_SALT.encode(),('watch:'+value).encode(),hashlib.sha256).hexdigest()

    @router.get('/v1/institutions/{id}/watch')
    @router.post('/v1/institutions/{id}/watch')
    @router.delete('/v1/institutions/{id}/watch')
    def watch(id:int,request:Request,db:Session=Depends(get_db)):
        institution(db,id)
        identity=watch_identity(request)
        item=db.get(AppWatchItem,(identity,id))
        if request.method=='POST' and not item:
            from sqlalchemy.exc import IntegrityError
            db.add(AppWatchItem(device_hash=identity,institution_id=id))
            try:db.commit()
            except IntegrityError:
                db.rollback()
                if not db.get(AppWatchItem,(identity,id)):raise
            item=True
        if request.method=='DELETE' and item:
            db.delete(item);db.commit();item=None
        return JSONResponse(dict(watching=bool(item),notifications_available=False),headers={'Cache-Control':'no-store'})

    @router.get('/v1/institutions/{id}/ratings')
    def ratings(id:int,db:Session=Depends(get_db)):
        institution(db,id)
        from ilma_api.bank_screen import rating_meaning
        return [dict(**rating_meaning(r.agency,r.long_term),fact_id=r.fact_id,agency=r.agency,long_term=r.long_term,short_term=r.short_term,outlook=r.outlook,
            rated_on=r.rated_on,valid_to=r.valid_to,expired=bool(r.valid_to and r.valid_to<date.today()),
            **source_view(r.source,r.quote,r.checked_by)) for r in db.query(Rating).filter_by(institution_id=id).order_by(Rating.rated_on.desc())]

    @router.get('/v1/institutions/{id}/events')
    def events(id:int,page:int=Query(1,ge=1),db:Session=Depends(get_db)):
        institution(db,id)
        rows=db.query(Event).filter_by(institution_id=id,type='other',official=False).order_by(Event.event_date.desc()).offset((page-1)*20).limit(20).all()
        return [dict(event_id=r.event_id,title_bn=r.title_bn,title_en=r.title_en,date=r.event_date,status='reported',official=False,
                     sources=[source_view(s) for s in r.sources]) for r in rows]

    @router.get('/v1/institutions/{id}/history')
    def history(id:int,db:Session=Depends(get_db)):
        institution(db,id)
        from ilma_api.incidents import history as incident_history
        return incident_history(db,id)

    @router.get('/v1/services/audio-manifest')
    def audio_manifest():
        from ilma_api.service_clips import manifest
        return JSONResponse(manifest(),headers={'Cache-Control':'no-store'})

    @router.get('/v1/services/categories')
    def categories(db:Session=Depends(get_db)):
        rows=db.query(ServiceOffer).filter_by(hidden=False).filter(ServiceOffer.variant!='excluded').all()
        return [dict(category=category,product_types=sorted({r.product_type for r in rows if r.category==category}),
            tenors=sorted({r.tenor_months for r in rows if r.category==category and r.tenor_months}),
            networks=sorted({r.network for r in rows if r.category==category and r.network}),
            tiers=sorted({r.tier for r in rows if r.category==category and r.tier}),
            choices=sorted({(r.network or '',r.tier or '') for r in rows if r.category==category}),
            audiences=['all','women','senior','student_child','nrb'] if category=='deposit' else [],attributes=sorted({r.attribute for r in rows if r.category==category})) for category in ['deposit','card','loan','account_fee']]

    @router.get('/v1/services/accounts')
    def account_catalog(request:Request,item:str='savings',audience:str='all',product_type:Literal['account_fee']='account_fee',db:Session=Depends(get_db)):
        from ilma_api.account_catalog import catalog,ITEMS,AUDIENCES
        if set(request.query_params)-{'item','audience','product_type'}:raise HTTPException(422,'Balances stay on the device')
        if item not in ITEMS or audience not in AUDIENCES:raise HTTPException(422,'Unknown account choice')
        return catalog(db,item,audience)

    @router.get('/v1/services/deposits')
    def deposit_catalog(request:Request,product_type:str='fdr',audience:str='all',basis:str='conventional',db:Session=Depends(get_db)):
        from ilma_api.deposit_catalog import catalog,AUDIENCES,TYPES
        if set(request.query_params)-{'product_type','audience','basis'}:raise HTTPException(422,'Amounts and terms stay on the device')
        if product_type not in TYPES or audience not in AUDIENCES or basis not in {'conventional','islamic'}:raise HTTPException(422,'Unknown deposit choice')
        return catalog(db,product_type,audience,basis=basis)

    @router.get('/v1/services/compare')
    def comparison(request:Request,product_type:str='fdr',tenor_months:int|None=Query(None,ge=1,le=600),network:str|None=None,
                   tier:str|None=None,attribute:str|None=None,basis:str='conventional',compare_by:str|None=None,audience:str|None=None,item:str|None=None,db:Session=Depends(get_db)):
        if set(request.query_params)-{'product_type','tenor_months','network','tier','attribute','basis','compare_by','audience','item'}:raise HTTPException(422,'Unsupported query fields; calculator amounts stay on the device')
        if item is not None:
            from ilma_api.account_catalog import catalog,ITEMS,AUDIENCES
            if product_type!='account_fee' or item not in ITEMS or (audience or 'all') not in AUDIENCES:raise HTTPException(422,'Unknown account choice')
            return catalog(db,item,audience or 'all')
        if audience is not None:
            from ilma_api.deposit_catalog import catalog,AUDIENCES,TYPES
            if audience not in AUDIENCES or product_type not in TYPES or basis not in {'conventional','islamic'}:raise HTTPException(422,'Unknown deposit choice')
            return catalog(db,product_type,audience,tenor_months,basis)
        if product_type not in {'fdr','dps','savings','card','home_loan','auto_loan','personal_loan','loan_against_fdr','account_fee'}: raise HTTPException(422,'Unknown product type')
        if basis not in {'conventional','islamic'}:raise HTTPException(422,'Unknown basis')
        if product_type in {'fdr','dps'} and tenor_months is None:raise HTTPException(422,'Select one tenor')
        if product_type=='card' and (not network or not tier):raise HTTPException(422,'Select network and tier')
        if product_type in {'home_loan','auto_loan','personal_loan','loan_against_fdr'} and tenor_months is not None:raise HTTPException(422,'Loan terms stay on the device')
        return compare(db,product_type,tenor_months,network,tier,attribute,basis,compare_by)

    @router.get('/v1/institutions/{id}/services')
    def bank_services(id:int,db:Session=Depends(get_db)):
        bank=institution(db,id)
        rows=db.query(ServiceOffer).filter_by(institution_id=id,hidden=False).order_by(ServiceOffer.category,ServiceOffer.product,ServiceOffer.attribute).all()
        from ilma_api.loan_catalog import group,TYPES,scopes,fresh
        loan_rows=db.query(ServiceOffer).filter_by(institution_id=id,category='loan').all()
        loans=[item for kind in TYPES if (item:=group(db,bank,loan_rows,kind))]
        special={}
        for row in loan_rows:
            if not row.hidden and fresh(row) and scopes(row,bank.slug)==['none']:special.setdefault(row.product,offer_view(row))
        from ilma_api.deposit_catalog import rates as deposit_rates
        from ilma_api.account_catalog import banks as account_banks
        account=next((b for b in account_banks(db) if b['id']==id),None)
        return dict(account_catalog=account,deposit_rates=deposit_rates(db,bank),institution=bank_view(db,bank),offers=[offer_view(row) for row in rows],loan_products=loans,special_loans=list(special.values()))

    @router.get('/v1/services/offers/{offer_id}')
    def offer(offer_id:str,db:Session=Depends(get_db)):
        from ilma_api.loan_catalog import TYPES,recoverable,group as loan_group,view as loan_view,scopes
        from ilma_api.loan_catalog import fresh as fresh_account
        proxy=offer_id.startswith('loan-mid-')
        row=db.get(ServiceOffer,offer_id.removeprefix('loan-mid-'))
        if not row or (row.hidden and not (proxy and recoverable(row))):raise HTTPException(404,'Offer not available')
        if row.category=='account_fee':
            from ilma_api.account_catalog import catalog,fee_view
            result=catalog(db);bank=next((b for b in result['banks'] if b['id']==row.institution_id),None)
            if bank is None or not fresh_account(row):raise HTTPException(404,'Offer not available')
            selected=next((f for f in bank['all_fees'] if f['offer_id']==row.offer_id),None)
            if selected is None:raise HTTPException(404,'Offer not available')
            return dict(account_detail=True,selected=selected,bank=bank,readouts=result['readouts'])
        if row.category=='deposit':
            from ilma_api.deposit_catalog import rates,kind,family,audience
            available=rates(db,row.institution);items=[r for r in available if r['family']==family(row.product)]
            if not items:raise HTTPException(404,'Offer not available')
            from ilma_api.deposit_catalog import catalog
            insurance=catalog(db,kind(row),audience(row,row.institution.slug))['insurance']
            return dict(insurance=insurance,institution=bank_view(db,row.institution),product=row.product,offers=items,deposit_type=kind(row),audience=audience(row,row.institution.slug))
        if row.product_type in TYPES:
            sources=db.query(ServiceOffer).filter_by(institution_id=row.institution_id,category='loan',basis=row.basis).all()
            detail=loan_group(db,row.institution,sources,row.product_type,detail_product=row.product,allow_stale=row.stale)
            if detail:
                facts=[r for r in [detail['rate'],detail['rate_min'],detail['rate_max'],*detail['fees']] if r]
            else:facts=[loan_view(r) for r in sources if r.product==row.product and not r.hidden]
            return dict(institution=bank_view(db,row.institution),product=row.product,offers=facts,loan=detail,loan_type=row.product_type)
        group=db.query(ServiceOffer).filter_by(institution_id=row.institution_id,product=row.product,network=row.network,
                    tier=row.tier,tenor_months=row.tenor_months,basis=row.basis,hidden=False)
        if row.product_type=='card':
            group=db.query(ServiceOffer).filter_by(institution_id=row.institution_id,product_type='card',network=row.network,tier=row.tier,basis=row.basis,hidden=False)
            group=[item for item in group.all() if card_key(item)==card_key(row)]
        else:group=group.all()
        return dict(institution=bank_view(db,row.institution),product=row.product,offers=[{**offer_view(item),**({'condition_bn':condition(item,renewal=any(r.attribute=='renewal_fee' for r in group)),'condition_en':condition(item,renewal=any(r.attribute=='renewal_fee' for r in group),language='en')} if item.product_type=='card' else {})} for item in group])

    from pydantic import BaseModel, ConfigDict
    class ReadComparison(BaseModel):
        model_config=ConfigDict(extra='forbid')
        product_type:str
        tenor_months:int|None=None
        network:str|None=None
        tier:str|None=None
        attribute:str|None=None
        compare_by:str|None=None
        basis:Literal['conventional','islamic']='conventional'
        language:Literal['bn','en']='bn'
    @router.post('/v1/services/readout')
    async def comparison_readout(payload:ReadComparison,db:Session=Depends(get_db)):
        from ilma_api.database_tasks import call
        from ilma_api.service_clips import readout
        def saved(owned):
            result=compare(owned,**payload.model_dump(exclude={'language'}))
            if payload.product_type in {'home_loan','auto_loan','personal_loan','loan_against_fdr'}:
                if payload.tenor_months is not None:raise HTTPException(422,'Loan terms stay on the device')
                return result['readout'] if payload.language=='bn' else {'text':'','audio_url':None}
            return readout(result,payload.language)
        return await call(db,saved)
    return router


def comparison_narration(db,result,language):
    from ilma_api.answer_wording import compose
    items=[{'fact_id':row['offer']['offer_id'],'institution_id':row['id']} for row in result['rows'] if row.get('offer')][:2]
    return compose(db,items,{'language':language},'','service_compare').speech


def voice_service_result(question,intent,context,db,language):
    """Deterministic navigation/fact templates after intent; no invented offers."""
    text=question.lower()
    from ilma_api.rules.reasons import format_date, format_number
    product=intent.product
    account_attribute=intent.service_attribute
    if product is None:
        for pattern,attribute in [(r'\bsms\b|এসএমএস','sms_alert_fee'),(r'cheque|চেকবই','cheque_book_fee'),
                                  (r'debit card|ডেবিট','annual_fee'),(r'maintenance|রক্ষণাবেক্ষণ|account charge|অ্যাকাউন্ট|হিসাব|\baccount\b','maintenance_fee_half_yearly')]:
            if re.search(pattern,text):product='account_fee';account_attribute=attribute;break
    if not product:
        for pattern,key in [(r'against.*fdr|(?:fdr|এফডিআর).*বিপরীতে','loan_against_fdr'),(r'কার্ড|card','credit_card'),(r'এফডিআর|fdr|fixed deposit','fdr'),
                            (r'ডিপিএস|dps','dps'),(r'গৃহঋণ|home loan','home_loan')]:
            if re.search(pattern,text):product=key;break
    mapping={'credit_card':'card','car_loan':'auto_loan'}
    product=mapping.get(product,product)
    if product not in {'fdr','dps','savings','card','home_loan','auto_loan','personal_loan','loan_against_fdr','account_fee'}:return None
    if not (context.tab in {'services','bank'} or intent.intent in {'rates','service_compare'}):return None
    choice={'product_type':product,'basis':'islamic' if re.search(r'islamic|ইসলামী',text) else 'conventional'}
    if product=='account_fee' and account_attribute:choice['attribute']=account_attribute
    if product in {'fdr','dps'}:choice['tenor_months']=intent.period_months or 12
    if product=='card':
        if account_attribute:choice['attribute']=account_attribute
        elif re.search(r'interest|সুদের|সুদ',text):choice['attribute']='interest_rate'
        elif re.search(r'renewal|নবায়ন',text):choice['attribute']='renewal_fee'
        choice['network']='Mastercard' if 'mastercard' in text or 'মাস্টারকার্ড' in text else 'Amex' if 'amex' in text or 'আমেক্স' in text else 'Visa'
        choice['tier']=next((tier for pattern,tier in [(r'signature|সিগনেচার','Signature'),(r'platinum|প্লাটিনাম','Platinum'),(r'world|ওয়ার্ল্ড','World'),(r'infinite|ইনফিনিট','Infinite'),(r'classic|ক্লাসিক','Classic')] if re.search(pattern,text)),(intent.card_tier or 'Gold').title())
    if product=='account_fee':
        from ilma_api.account_catalog import catalog
        item='debit' if account_attribute=='annual_fee' else 'other' if account_attribute and account_attribute!='maintenance_fee_half_yearly' else 'savings'
        who=next((key for pattern,key in [(r'women|নারী|মহিলা','women'),(r'senior|প্রবীণ','senior'),(r'student|child|শিক্ষার্থী|শিশু','student_child'),(r'nrb|প্রবাসী','nrb')] if re.search(pattern,text)),'all')
        account=catalog(db,item,who);read=account['readouts'].get(item+'-'+(who if item=='savings' else 'all').replace('_','-'),{})
        speech=read.get('text','') if language=='bn' else 'Published account rates and fees are shown with their sources. The fixed example uses a BDT 100,000 balance; net is shown only when all selected costs are known.'
        sources=[]
        from ilma_api.account_catalog import calculate
        for bank in account['banks']:
            example=calculate(bank,100000,True,True,who)
            evidence=[example['rate'],example['maintenance'],example['debit'],example['sms']] if item=='savings' else [bank['debit_main'],bank['debit_replacement'],*bank['debit_variants']] if item=='debit' else bank['other']
            for row in [r for r in evidence if r]:
                sources.append(dict(fact_id=row['offer_id'],source_url=row['source_url'],source_title=row['product'],source_title_bn=bank['name_bn'],source_title_en=bank['name_en']+' · '+row['product'],page=row['page'],quote=row['quote']))
        choice.update(item=item,audience=who)
        return dict(type='service_answer',text=speech,speech_text=speech,card_text=speech,bank_warnings=[],comparison=choice,sources=sources,calculator_amount=intent.amount_bdt,calculator_term=None)
    if product in {'fdr','dps','savings'}:
        from ilma_api.deposit_catalog import catalog
        who=next((key for pattern,key in [(r'women|নারী|মহিলা','women'),(r'senior|প্রবীণ','senior'),(r'student|child|শিক্ষার্থী|শিশু','student_child'),(r'nrb|probashi|প্রবাসী','nrb')] if re.search(pattern,text)),'all')
        choice['audience']=who
        result=catalog(db,product,who,choice.get('tenor_months'),choice['basis'])
        result['rows'].sort(key=lambda b:-((b.get('offer') or {}).get('value_num') or 0))
    else:result=compare(db,**choice)
    rows=[bank for bank in result['rows'] if bank.get('offer')]
    if intent.institution_ids:rows=[bank for bank in rows if bank['id'] in intent.institution_ids]
    sources=[];lines=[]
    for bank in rows[:3]:
        row=bank['offer']
        display_value=format_number(row['value_num'],bn=language=='bn') if row['value_num'] is not None else row['value_text']
        warning=((' · মূল্যায়ন করা হয়নি' if product in {'fdr','dps','savings'} else ' · ব্যাংকের অবস্থা যাচাই হয়নি') if language=='bn' else ' · Bank condition is unverified') if bank['status']['code']=='no_data' else ''
        lines.append(f"{bank['name_bn' if language=='bn' else 'name_en']}: {display_value}{'%' if row['unit']=='pct_year' else (' টাকা' if language=='bn' else ' BDT') if row['unit']=='bdt' else ''} ({format_date(row['doc_date'],bn=language=='bn')})"+(' · '+('পুরনো তথ্য' if language=='bn' else 'old data') if row['stale'] else '')+warning)
        sources.append(dict(fact_id=row['offer_id'],source_url=row['source_url'],source_title=row['product'],source_title_bn=bank['name_bn'],source_title_en=bank['name_en']+' · '+row['product'],page=row['page'],quote=row['quote']))
    from ilma_api.answer_wording import compose
    items=[{'fact_id':bank['offer']['offer_id'],'institution_id':bank['id']} for bank in rows[:2]]
    speech_text=compose(db,items,{'language':language,'institution_id':items[0]['institution_id'] if items else None},'','service_compare' if len(items)>1 else 'service_detail').speech
    warnings=[((('এই ব্যাংক এখনো মূল্যায়ন করা হয়নি।' if product in {'fdr','dps','savings'} else 'এই ব্যাংকের আর্থিক অবস্থা যাচাই হয়নি।') if language=='bn' else 'This bank is not rated.')) for bank in rows[:3] if bank['status']['code']=='no_data']
    return dict(type='service_answer',text=speech_text,speech_text=speech_text,card_text='; '.join(lines),bank_warnings=warnings,
                comparison=choice,sources=sources,calculator_amount=intent.amount_bdt,
                calculator_term=intent.period_months if product.endswith('_loan') else None)
