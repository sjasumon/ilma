"""Source-bound loan rates, fee scopes and fixed-example narration; no borrower data."""
import csv,hashlib,json,math,re
from datetime import date
from decimal import Decimal
from pathlib import Path
from ilma_api.card_catalog import field
from ilma_api.export_seed import quote_numbers
from ilma_api.db import ServiceOffer
ROOT=Path(__file__).resolve().parents[2]
TYPES=('home_loan','auto_loan','personal_loan','loan_against_fdr')
FEES={'processing_fee','early_settlement_fee','partial_payment_fee'}
DEFAULTS={'home_loan':(2000000,20),'auto_loan':(1000000,5),'personal_loan':(500000,3),'loan_against_fdr':(500000,1)}
LABELS={'home_loan':('গৃহঋণ','Home loan'),'auto_loan':('গাড়ির ঋণ','Auto loan'),'personal_loan':('ব্যক্তিগত ঋণ','Personal loan'),'loan_against_fdr':('এফডিআরের বিপরীতে ঋণ','Loan against FDR')}
RISK={'strong':('ঝুঁকি কম','Low risk'),'watch':('ঝুঁকি মাঝারি','Medium risk'),'high':('ঝুঁকি বেশি','High risk'),'no_data':('মূল্যায়ন করা হয়নি','Not rated')}

def percentage(row):
    value=field(row,'value_num',None)
    if value is None:
        match=re.fullmatch(r'(\d+(?:\.\d+)?)\s*%?',field(row,'value_text',field(row,'value','')).strip())
        if not match:return None
        value=Decimal(match[1])
    number=Decimal(str(value))
    return float(number) if number in quote_numbers(field(row,'quote')) else None

def mid_rate(row):
    match=re.search(r'mid[- ]rate\s*(\d+(?:\.\d+)?)\s*%?\s*(?:±|\+\s*/\s*-)\s*(\d+(?:\.\d+)?)\s*%',field(row,'quote'),re.I)
    if not match:return None
    return float(match[1]),float(match[2])

def fresh(row,today=None):return not field(row,'stale',False) and ((today or date.today())-field(row,'doc_date')).days<=365

def fee_meta(row):
    text=field(row,'condition');cap=re.search(r'(?:max(?:imum)?\.?|not\s+(?:exceed|exceeding))\s*(?:BDT|Tk\.?)\s*([\d,]+(?:\.\d+)?)',text,re.I)
    slab=re.search(r'(up\s*to|below|above)\s*(?:BDT|TK\.?)?\s*([\d,]+(?:\.\d+)?)\s*(lac|lakh|crore)?',text,re.I)
    bound=float(slab[2].replace(',',''))*({'lac':1e5,'lakh':1e5,'crore':1e7}.get((slab[3] or '').lower(),1)) if slab else None
    fee_range=re.search(r'(\d+(?:\.\d+)?)\s*%?\s*[-–]\s*(\d+(?:\.\d+)?)\s*%',text)
    bounds=(float(fee_range[1]),float(fee_range[2])) if fee_range else (None,None)
    return dict(fee_rate_min=bounds[0],fee_rate_max=bounds[1],is_maximum=bool(re.search(r'(?:up to|max(?:imum)?)\s*\d+(?:\.\d+)?\s*%',text,re.I)),unit='pct_once',cap_bdt=float(cap[1].replace(',','')) if cap else None,
        slab_min=bound if slab and slab[1].lower()=='above' else None,slab_max=bound if slab and slab[1].lower()!='above' else None,
        slab_min_inclusive=False,slab_max_inclusive=bool(slab and re.match(r'up\s*to',slab[1],re.I)),vat_percent=15 if re.search(r'15\s*%\s*VAT',text,re.I) else None)

def margin(row):
    text=field(row,'value_text')+' '+field(row,'condition')+' '+field(row,'quote')
    for rule in csv.DictReader((ROOT/'seed/condition_bn_map.csv').open()):
        if not rule['id'].startswith('loan_margin'):continue
        match=re.search(rule['pattern'],text,re.I)
        if not match:continue
        low=high=None
        if rule['id']=='loan_margin_range':low,high=float(match['low']),float(match['high'])
        elif rule['id']=='loan_margin_min':low=float(match['margin'])
        elif rule['id']=='loan_margin_max':high=float(match['margin'])
        else:
            high=float(match['margin']);low=None if re.search(r'maximum',text,re.I) else high
        if any(Decimal(str(v)) not in quote_numbers(field(row,'quote')) for v in [low,high] if v is not None):continue
        bn='এফডিআরের হারের চেয়ে '+(f'{low:g}–{high:g}% বেশি' if low is not None and high is not None and low!=high else f'{low:g}% বেশি' if low==high else f'কমপক্ষে {low:g}% বেশি' if high is None else f'সর্বোচ্চ {high:g}% বেশি')
        return dict(margin_min=low,margin_max=high,condition_bn=bn,condition_en='Above the FDR rate: '+(f'{low:g}–{high:g} percentage points' if low is not None and high is not None else f'at least {low:g} percentage points' if high is None else f'up to {high:g} percentage points'))
    return {}

def decorate(row,result):
    value=percentage(row)
    if value is not None:result['value_num']=value
    if row.attribute in FEES:
        result.update(fee_meta(row));result['condition_bn']='একবার প্রযোজ্য';result['condition_en']='One-time charge'
    if row.product_type=='loan_against_fdr':result.update(margin(row))
    result['loan_display_bn']=('পেশাজীবী ঋণ' if re.search(r'Loan for Professional',row.product,re.I) else 'ঠিকানা গৃহঋণ' if re.search(r'Thikana',row.product,re.I) else LABELS[row.product_type][0])+(' (ফ্ল্যাট কেনা)' if re.search(r'Flat Purchase',row.product,re.I) else '')
    return result

def view(row):
    from ilma_api.bank_services import offer_view
    return offer_view(row)

def scopes(row,slug):
    rules=[r for r in csv.DictReader((ROOT/'seed/loan_fee_scope.csv').open()) if r['bank'].casefold()==slug.casefold() and r['product'].casefold() in row.product.casefold()]
    return rules[0]['applies_to'].split('|') if rules else []

def recoverable(row):
    return bool(row.category=='loan' and row.hidden and 'numeric value is not printed' in row.hidden_reason and 'quote_unreadable' not in row.condition and mid_rate(row))

def group(db,bank,rows,product_type,*,detail_product=None,allow_stale=False,inputs=None):
    eligible=[r for r in rows if r.institution_id==bank.id and (not r.hidden or recoverable(r)) and (allow_stale or fresh(r))]
    rates=[r for r in eligible if r.product_type==product_type and r.attribute in {'interest_rate','rate_min','rate_max'} and (not detail_product or r.product==detail_product)]
    rates.sort(key=lambda r:(-r.doc_date.toordinal(),r.product,r.offer_id))
    if not rates:return None
    product=rates[0].product;rates=[r for r in rates if r.product==product]
    chosen={}
    for r in rates:
        if r.hidden and not recoverable(r):continue
        if not r.hidden and (percentage(r) is not None or margin(r)):chosen.setdefault(r.attribute,view(r))
    middle=next((r for r in rates if mid_rate(r)),None)
    if middle:
        mid,delta=mid_rate(middle);base=view(middle);base.update(offer_id=('loan-mid-'+middle.offer_id) if middle.hidden else middle.offer_id,attribute='interest_rate',value_num=mid,value_text=f'{mid:g}%',derived=False,condition_bn='প্রকাশিত মধ্যহার',condition_en='Published mid rate')
        chosen['interest_rate']=base
        for attr,value in [('rate_min',mid-delta),('rate_max',mid+delta)]:chosen[attr]={**base,'attribute':attr,'value_num':value,'value_text':f'{value:g}%','derived':True,'condition_bn':f'প্রকাশিত মধ্যহার {mid:g}% ± {delta:g}% থেকে হিসাব','condition_en':f'Calculated from published mid rate {mid:g}% ± {delta:g}%'}
    rate=chosen.get('interest_rate');low=chosen.get('rate_min');high=chosen.get('rate_max')
    if not any([rate,low,high]):return None
    from ilma_api.bank_services import bank_view
    result=bank_view(db,bank,inputs=inputs);code=result['status']['code'];result['status']={**result['status'],'label_bn':RISK[code][0],'label_en':RISK[code][1]}
    fees=[view(r) for r in eligible if not r.hidden and r.attribute in FEES and (product_type in scopes(r,bank.slug) or not scopes(r,bank.slug) and r.product==product) and percentage(r) is not None]
    result.update(product_type=product_type,product=product,rate=rate,rate_min=low,rate_max=high,fees=fees,offer=rate or low or high,alternatives=[],state='published',stale=bool((rate or low or high)['stale']),margin_min=(rate or {}).get('margin_min'),margin_max=(rate or {}).get('margin_max'),fdr_12m_rate=None)
    if product_type=='loan_against_fdr':
        from ilma_api.service_terms import matches_term
        deposits=db.query(ServiceOffer).filter_by(institution_id=bank.id,product_type='fdr',attribute='rate',basis='conventional',hidden=False).all()
        deposits=[r for r in deposits if fresh(r) and matches_term(r,12) and percentage(r) is not None]
        deposits.sort(key=lambda r:(any(w in r.product.lower() for w in ['plus','extra','senior','women']),-r.doc_date.toordinal(),r.product))
        if deposits:
            from ilma_api.bank_services import offer_view
            result['fdr_12m_rate']={**offer_view(deposits[0]),'value_num':percentage(deposits[0])}
    return result

def compare(db,product_type,basis='conventional'):
    from ilma_api.bank_services import demo_banks
    rows=db.query(ServiceOffer).filter_by(category='loan',basis=basis).all();out=[]
    from ilma_api.report_card import status_inputs
    banks=demo_banks(db);inputs=status_inputs(db,banks)
    for bank in banks:
        item=group(db,bank,rows,product_type,inputs=inputs)
        if item:out.append(item)
    out.sort(key=lambda b:(b['rate'] is None or b['rate']['value_num'] is None,(b['rate'] or {}).get('value_num') or 0,b['name_bn']))
    result=dict(choice=dict(product_type=product_type,basis=basis),rows=out,sort='lower_cost_first',insurance=None,defaults=dict(amount=DEFAULTS[product_type][0],years=DEFAULTS[product_type][1]))
    from ilma_api.loan_readout import readout
    result['readout']=readout(result)
    return result

def emi(amount,rate,months):
    if not math.isfinite(amount) or amount<=0 or rate<0 or months<=0:raise ValueError('Invalid loan example')
    r=rate/1200
    return amount/months if r==0 else amount*r/-math.expm1(-months*math.log1p(r))
def fee_amount(fee,amount):
    if fee.get('slab_min') is not None and amount<=fee['slab_min']:return None
    if fee.get('slab_max') is not None and (amount>fee['slab_max'] or amount==fee['slab_max'] and not fee.get('slab_max_inclusive')):return None
    value=amount*fee['value_num']/100
    return min(value,fee['cap_bdt']) if fee.get('cap_bdt') is not None else value
