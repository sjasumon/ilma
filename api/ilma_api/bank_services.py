"""Read-only bank/service views. Hidden offers never cross the API boundary."""
from datetime import date
from ilma_api.service_terms import terms
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
    return {**{column.name:getattr(row,column.name) for column in ServiceOffer.__table__.columns
        if column.name not in {'hidden','hidden_reason','checked_by'}},
        'value_num':float(row.value_num) if row.value_num is not None else None,
        'tenor_min_months':terms(row)['tenor_min_months'],
        'tenor_max_months':terms(row)['tenor_max_months'],
        'tenor_options':terms(row)['tenor_options'],
        'stale':row.stale or (today-row.doc_date).days>365,
        'checked':row.checked_by.casefold()=='sumon', 'source_title':row.column_header if row.product_type=='card' and row.column_header else row.product,
        'group_key':f'{row.institution_id}:{row.product}:{row.column_header if row.product_type=="card" else ""}:{row.network or ""}:{row.tier or ""}:{row.tenor_months or ""}:{row.basis}'}


def compare(db, product_type='fdr', tenor_months=None, network=None, tier=None,
            attribute=None, basis='conventional'):
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
        return [dict(fact_id=r.fact_id,agency=r.agency,long_term=r.long_term,short_term=r.short_term,outlook=r.outlook,
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

    @router.get('/v1/services/categories')
    def categories(db:Session=Depends(get_db)):
        rows=db.query(ServiceOffer).filter_by(hidden=False).filter(ServiceOffer.variant!='excluded').all()
        return [dict(category=category,product_types=sorted({r.product_type for r in rows if r.category==category}),
            tenors=sorted({r.tenor_months for r in rows if r.category==category and r.tenor_months}),
            networks=sorted({r.network for r in rows if r.category==category and r.network}),
            tiers=sorted({r.tier for r in rows if r.category==category and r.tier}),
            choices=sorted({(r.network or '',r.tier or '') for r in rows if r.category==category}),
            attributes=sorted({r.attribute for r in rows if r.category==category})) for category in ['deposit','card','loan','account_fee']]

    @router.get('/v1/services/compare')
    def comparison(request:Request,product_type:str='fdr',tenor_months:int|None=Query(None,ge=1,le=600),network:str|None=None,
                   tier:str|None=None,attribute:str|None=None,basis:str='conventional',db:Session=Depends(get_db)):
        if set(request.query_params)-{'product_type','tenor_months','network','tier','attribute','basis'}:raise HTTPException(422,'Unsupported query fields; calculator amounts stay on the device')
        if product_type not in {'fdr','dps','savings','card','home_loan','auto_loan','personal_loan','loan_against_fdr','account_fee'}: raise HTTPException(422,'Unknown product type')
        if basis not in {'conventional','islamic'}:raise HTTPException(422,'Unknown basis')
        if product_type in {'fdr','dps'} and tenor_months is None:raise HTTPException(422,'Select one tenor')
        if product_type=='card' and (not network or not tier):raise HTTPException(422,'Select network and tier')
        return compare(db,product_type,tenor_months,network,tier,attribute,basis)

    @router.get('/v1/institutions/{id}/services')
    def bank_services(id:int,db:Session=Depends(get_db)):
        bank=institution(db,id)
        rows=db.query(ServiceOffer).filter_by(institution_id=id,hidden=False).order_by(ServiceOffer.category,ServiceOffer.product,ServiceOffer.attribute).all()
        return dict(institution=bank_view(db,bank),offers=[offer_view(row) for row in rows])

    @router.get('/v1/services/offers/{offer_id}')
    def offer(offer_id:str,db:Session=Depends(get_db)):
        row=db.get(ServiceOffer,offer_id)
        if not row or row.hidden:raise HTTPException(404,'Offer not available')
        group=db.query(ServiceOffer).filter_by(institution_id=row.institution_id,product=row.product,network=row.network,
                    tier=row.tier,tenor_months=row.tenor_months,basis=row.basis,hidden=False)
        if row.product_type=='card':group=group.filter_by(column_header=row.column_header)
        group=group.all()
        return dict(institution=bank_view(db,row.institution),product=row.product,offers=[offer_view(item) for item in group])

    from pydantic import BaseModel, ConfigDict
    class ReadComparison(BaseModel):
        model_config=ConfigDict(extra='forbid')
        product_type:str
        tenor_months:int|None=None
        network:str|None=None
        tier:str|None=None
        attribute:str|None=None
        basis:Literal['conventional','islamic']='conventional'
        language:Literal['bn','en']='bn'
    @router.post('/v1/services/readout')
    async def comparison_readout(payload:ReadComparison,db:Session=Depends(get_db)):
        from ilma_api.database_tasks import call
        from ilma_api.audio_cache import register_speech
        paragraph=await call(db,lambda owned:comparison_narration(owned,compare(owned,**payload.model_dump(exclude={'language'})),payload.language))
        audio=await register_speech([paragraph],payload.language,short=True)
        if not audio:raise HTTPException(503,'Spoken playback unavailable')
        return {**audio,'text':paragraph}
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
                                  (r'debit card|ডেবিট','annual_fee'),(r'maintenance|রক্ষণাবেক্ষণ|account charge|অ্যাকাউন্টের খরচ','maintenance_fee_half_yearly')]:
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
    result=compare(db,**choice)
    rows=[bank for bank in result['rows'] if bank.get('offer')]
    if intent.institution_ids:rows=[bank for bank in rows if bank['id'] in intent.institution_ids]
    sources=[];lines=[]
    for bank in rows[:3]:
        row=bank['offer']
        display_value=format_number(row['value_num'],bn=language=='bn') if row['value_num'] is not None else row['value_text']
        warning=(' · ব্যাংকের অবস্থা যাচাই হয়নি' if language=='bn' else ' · Bank condition is unverified') if bank['status']['code']=='no_data' else ''
        lines.append(f"{bank['name_bn' if language=='bn' else 'name_en']}: {display_value}{'%' if row['unit']=='pct_year' else (' টাকা' if language=='bn' else ' BDT') if row['unit']=='bdt' else ''} ({format_date(row['doc_date'],bn=language=='bn')})"+(' · '+('পুরনো তথ্য' if language=='bn' else 'old data') if row['stale'] else '')+warning)
        sources.append(dict(fact_id=row['offer_id'],source_url=row['source_url'],source_title=row['product'],source_title_bn=bank['name_bn'],source_title_en=bank['name_en']+' · '+row['product'],page=row['page'],quote=row['quote']))
    from ilma_api.answer_wording import compose
    items=[{'fact_id':bank['offer']['offer_id'],'institution_id':bank['id']} for bank in rows[:2]]
    speech_text=compose(db,items,{'language':language,'institution_id':items[0]['institution_id'] if items else None},'','service_compare' if len(items)>1 else 'service_detail').speech
    warnings=[(('এই ব্যাংকের আর্থিক অবস্থা যাচাই হয়নি।' if language=='bn' else 'This bank’s financial condition is unverified.')) for bank in rows[:3] if bank['status']['code']=='no_data']
    return dict(type='service_answer',text=speech_text,speech_text=speech_text,card_text='; '.join(lines),bank_warnings=warnings,
                comparison=choice,sources=sources,calculator_amount=intent.amount_bdt,
                calculator_term=intent.period_months if product.endswith('_loan') else None)
