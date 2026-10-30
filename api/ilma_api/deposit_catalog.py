"""Published deposit catalog; borrower-independent metadata and fixed examples."""
import csv,math,re
from pathlib import Path
from ilma_api.loan_catalog import fresh,percentage,RISK
from ilma_api.service_terms import parse_terms
from ilma_api.db import ServiceOffer,InsuranceRule
ROOT=Path(__file__).resolve().parents[2]
AUDIENCES={'all':('সবার জন্য','Everyone'),'women':('নারীদের জন্য','Women'),'senior':('প্রবীণদের জন্য','Seniors'),'student_child':('শিক্ষার্থী ও শিশু','Students and children'),'nrb':('প্রবাসীদের জন্য','Non-residents')}
TYPES={'fdr','dps','savings'}
def audience(row,slug):
    for r in csv.DictReader((ROOT/'seed/deposit_audience.csv').open()):
        if r['bank'].lower()==slug.lower() and r['product'].casefold() in row.product.casefold():return r['audience']
    return 'all'
def kind(row):return 'fdr' if 'double benefit' in row.product.lower() else row.product_type
def scheme(row):return bool(re.search(r'millionaire|double benefit|lakhopati|kotipoti',row.product,re.I))
def family(product):
    return re.sub(r'\s+',' ',re.sub(r'\b\d+(?:\s*(?:&|and|to|or|[-–,])\s*\d+)*\s*(?:months?|years?)(?:\s*\(\d+\s*days?\))?','',product,flags=re.I)).strip()
def term_list(row):
    info=parse_terms(row.product,row.condition,row.tenor_months)
    if info['tenor_options']:return info['tenor_options']
    lo,hi=info['tenor_min_months'],info['tenor_max_months']
    if lo is not None and hi is not None:
        step=12 if lo%12==0 and hi%12==0 else 1
        return list(range(lo,hi+1,step))
    match=re.search(r'\bYear\s+(\d+)\b',row.condition,re.I)
    return [int(match[1])*12] if match else []
def amount_value(text):
    match=re.search(r'(\d[\d,]*(?:\.\d+)?)\s*(crore|cr\b|lac|lakh|million|k\b)?',text,re.I)
    return float(match[1].replace(',',''))*{'crore':1e7,'cr':1e7,'lac':1e5,'lakh':1e5,'million':1e6,'k':1000}.get((match[2] or '').lower(),1) if match else None
def slabs(text):
    # Restrict parsing to the printed amount expression; age and tenure are not balances.
    t=re.sub(r'\b(?:BDT|Tk\.?)\s*','',text,flags=re.I).strip()
    result=dict(amount_min=None,amount_max=None,amount_min_inclusive=True,amount_max_inclusive=False,slab_known=False)
    if re.search(r'any\s+(?:amount|balance)',t,re.I):return {**result,'slab_known':True}
    m=re.search(r'(?:amount\s+)?(?:less than|below|under|<)\s*(\d[\d,.]*\s*(?:crore|cr\b|lac|lakh|million|k\b)?)',t,re.I)
    if m:result.update(amount_max=amount_value(m[1]),slab_known=True)
    m=re.search(r'(\d[\d,.]*\s*(?:crore|cr\b|lac|lakh|million|k\b)?)\s*(?:and above|&\s*above)',t,re.I)
    if m:result.update(amount_min=amount_value(m[1]),slab_known=True)
    m=re.search(r'(\d[\d,.]*\s*(?:crore|cr\b|lac|lakh|million|k\b)?)\s*(?:-|–|to)\s*(?:<|below|less than)?\s*(\d[\d,.]*\s*(?:crore|cr\b|lac|lakh|million|k\b)?)',t,re.I)
    if m:result.update(amount_min=amount_value(m[1]),amount_max=amount_value(m[2]),amount_max_inclusive=not bool(re.search(r'<|below|less than',m[0],re.I)),slab_known=True)
    m=re.search(r'(\d[\d,]*(?:\.\d+)?)\s*<\s*(\d[\d,]*(?:\.\d+)?)',t)
    if m:result.update(amount_min=amount_value(m[1]),amount_max=amount_value(m[2]),slab_known=True)
    m=re.search(r'minimum balance\s*(\d[\d,.]*)',t,re.I)
    if m:result.update(amount_min=amount_value(m[1]),slab_known=True)
    return result
def in_slab(row,amount):
    return (row['amount_min'] is None or amount>=row['amount_min']) and (row['amount_max'] is None or amount<row['amount_max'] or row['amount_max_inclusive'] and amount==row['amount_max'])
def view(row,slug):
    from ilma_api.bank_services import offer_view
    result=offer_view(row);p=kind(row);result.update(product_type=p,audience=audience(row,slug),variant='scheme' if scheme(row) else row.variant,family=family(row.product),tenor_list_months=term_list(row),**slabs(row.condition if p!='dps' else 'any amount'))
    result['value_num']=percentage(row)
    result['rate_is_maximum']=bool(re.search(r'(?:up\s*to|maximum)\s*\d+(?:\.\d+)?\s*%',row.condition+' '+row.quote,re.I))
    result['display_priority']=0 if (p=='savings' and re.search(r'^(?:Savings (?:Bank Deposit )?Account|General Savings Account|Regular Savings Account|Regular/TARA Savings Products|Prime Savings Account|Savings Account \(General\))$',row.product,re.I)) else 1 if p=='savings' else 0
    if p=='dps':result.update(min_monthly_installment=None,installment_multiple=None)
    return result
def rates(db,bank):
    from ilma_api.bank_services import offer_view
    raw=db.query(ServiceOffer).filter_by(institution_id=bank.id,category='deposit',hidden=False).all();out=[]
    minimums=[r for r in raw if r.attribute=='min_monthly_installment' and fresh(r)]
    for row in raw:
        if not fresh(row) or row.attribute not in {'rate','rate_min','rate_max'}:continue
        r=view(row,bank.slug)
        if r['value_num'] is None:continue
        if r['product_type']=='dps':
            for minimum in minimums:
                if family(minimum.product)==family(row.product) or minimum.product in row.product:
                    if percentage(minimum) is not None:r['min_monthly_installment']=percentage(minimum)
                    elif re.fullmatch(r'\d+',minimum.value_text) and minimum.value_text in minimum.quote:r['min_monthly_installment']=int(minimum.value_text)
                    r['installment_multiple']=r['min_monthly_installment'] if 'multiple' in minimum.condition.lower() else None
                    r['minimum_source']=offer_view(minimum)
        out.append(r)
    return out
def select(rows,product,months,who,amount):
    choices=[r for r in rows if r['product_type']==product and r['audience']==who and (product=='savings' or months in r['tenor_list_months']) and in_slab(r,amount) and (product!='savings' or r['slab_known'])]
    choices.sort(key=lambda r:(r.get('display_priority',0),r['variant']=='scheme','extra value' in r['product'].lower(),'insurance backed' in r['product'].lower(),r['product'],r['offer_id']))
    return choices

def fv(monthly,rate,months):
    i=rate/1200
    return monthly*months if not i else monthly*math.expm1(months*math.log1p(i))/i*(1+i)
def catalog(db,product='fdr',who='all',months=None,basis='conventional'):
    from ilma_api.bank_services import bank_view,demo_banks,source_view
    months=months or (36 if product=='dps' else 12);banks=[];all_banks=[]
    for bank in demo_banks(db):
        all_facts=[r for r in rates(db,bank) if r['basis']==basis]
        facts=[r for r in all_facts if r['product_type']==product and r['audience']==who]
        if not all_facts:continue
        b=bank_view(db,bank);code=b['status']['code'];b['status'].update(label_bn=RISK[code][0],label_en=RISK[code][1]);from ilma_api.bank_services import offer_view
        account_fees=[offer_view(r) for r in db.query(ServiceOffer).filter_by(institution_id=bank.id,category='account_fee',hidden=False).all() if fresh(r)]
        all_banks.append({**b,'rates':all_facts,'account_fees':account_fees});chosen=select(facts,product,months,who,5000 if product=='dps' else 100000)
        b.update(rates=facts,offer=next((r for r in chosen if r['variant']!='scheme'),None),alternatives=[r for r in chosen if r['variant']=='scheme' or 'extra value' in r['product'].lower()],other_tenors=facts,state='published');
        if facts:banks.append(b)
    rule=db.get(InsuranceRule,'bank');insurance=None
    if rule and rule.covered and rule.source and rule.limit_bdt:
        insurance=dict(limit_bdt=rule.limit_bdt,text_bn=rule.text_bn,text_en=rule.text_en,**source_view(rule.source))
    result=dict(catalog_banks=all_banks,choice=dict(product_type=product,audience=who,basis=basis,tenor_months=months),rows=banks,insurance=insurance,sort='higher_rate_first',defaults=dict(amount=5000 if product=='dps' else 100000,months=months))
    from ilma_api.deposit_readout import readouts
    result['readouts']=readouts(result)
    return result
