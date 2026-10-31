"""Source-bound everyday-account facts and local-calculation metadata."""
import re
from ilma_api.db import ServiceOffer
from ilma_api.loan_catalog import fresh,percentage,RISK
from ilma_api.deposit_catalog import rates as savings_rates,slabs,in_slab,AUDIENCES
ITEMS=('savings','debit','other')
OTHER=('closing_fee','atm_other_bank_fee','sms_alert_fee','cheque_book_fee','minimum_balance')

def debit_variant(product):
    if re.search(r'prepaid',product,re.I):return 'excluded'
    if re.fullmatch(r'VISA Debit Card|EBL Classic Debit Card|Nexus-EMV Debit Card \(Local\)',product,re.I):return 'main'
    return 'variant'
def balance_slab(text):
    t=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',text)
    t=re.sub(r'(?i)(Above|Below|Balance)(?=(?:Tk|BDT|\d))',r'\1 ',t)
    result=slabs(t)
    m=re.search(r'up\s*to\s*(?:BDT|Tk\.?)?\s*([\d,]+(?:\.\d+)?)',t,re.I)
    if m:result.update(amount_max=float(m[1].replace(',','')),amount_max_inclusive=True,slab_known=True)
    m=re.search(r'above\s*(?:BDT|Tk\.?)?\s*([\d,]+(?:\.\d+)?)\s*(lac|lakh|crore)?',t,re.I)
    if m and not re.search(r'\bto\b',t,re.I):result.update(amount_min=float(m[1].replace(',',''))*{'lac':1e5,'lakh':1e5,'crore':1e7}.get((m[2] or '').lower(),1),amount_min_inclusive=False,slab_known=True)
    m=re.search(r'above\s*(?:BDT|Tk\.?)?\s*([\d,]+(?:\.\d+)?)\s*to\s*(?:BDT|Tk\.?)?\s*([\d,]+(?:\.\d+)?)',t,re.I)
    if m:result.update(amount_min=float(m[1].replace(',','')),amount_max=float(m[2].replace(',','')),amount_min_inclusive=False,amount_max_inclusive=True,slab_known=True)
    return dict(balance_min=result['amount_min'],balance_max=result['amount_max'],balance_min_inclusive=result['amount_min_inclusive'],balance_max_inclusive=result['amount_max_inclusive'],balance_slab_known=result['slab_known'])
def contains(row,amount):
    low,high=row['balance_min'],row['balance_max']
    return row['balance_slab_known'] and (low is None or amount>low or row['balance_min_inclusive'] and amount==low) and (high is None or amount<high or row['balance_max_inclusive'] and amount==high)
def fee_view(row):
    from ilma_api.bank_services import offer_view
    result=offer_view(row);result['value_num']=percentage(row)
    if result['value_num'] is None and row.value_text=='0' and re.search(r'\bfree\b',row.quote,re.I):result['value_num']=0
    text=row.condition+' '+row.quote
    result.update(balance_slab(row.condition),vat_percent=15 if re.search(r'15\s*%\s*VAT',text,re.I) else None,vat_included=bool(re.search(r'VAT\s*included',text,re.I)),periods_per_year=2 if row.attribute=='maintenance_fee_half_yearly' or row.attribute=='sms_alert_fee' and re.search(r'half[ -]?year',text,re.I) else 1,account_audience='all',is_debit=bool(re.search(r'debit|prepaid',row.product,re.I)))
    result['rate_is_maximum']=bool(re.search(r'\b(?:up\s*to|upto|maximum)\s*(?:Tk\.?|BDT)?\s*\d',row.quote,re.I))
    if result['is_debit']:result['variant']=debit_variant(row.product)
    return result

def yearly(row):
    return row['value_num']*row['periods_per_year']*(100+(row['vat_percent'] or 0))/100 if not row['vat_included'] else row['value_num']*row['periods_per_year']
def interest_row(bank,balance,audience='all'):
    rows=[r for r in bank['interest_slabs'] if r['audience']==audience]
    priority=min((r.get('display_priority',0) for r in rows),default=0)
    chosen=[r for r in rows if r.get('display_priority',0)==priority and r['slab_known'] and in_slab(r,balance) and not r.get('rate_is_maximum')]
    return sorted(chosen,key=lambda r:(r['product'],r['offer_id']))[0] if chosen else None

def calculate(bank,balance,card=True,sms=True,audience='all'):
    rate=interest_row(bank,balance,audience);interest=balance*rate['value_num']/100 if rate else None
    maintenance=next((f for f in bank['maintenance_slabs'] if f['account_audience']==audience and contains(f,balance)),None)
    debit=bank['debit_main'];alert=bank['sms']
    included=[maintenance]+([debit] if card else [])+([alert] if sms else [])
    known=[r for r in included if r];cost=sum(yearly(r) for r in known)
    complete=all(r is not None for r in included)
    return dict(balance=balance,interest=interest,rate=rate,maintenance=maintenance,debit=debit if card else None,sms=alert if sms else None,known_cost=cost,cost=cost if complete else None,net=interest-cost if complete and interest is not None else None)

def banks(db):
    from ilma_api.bank_services import demo_banks,bank_view
    from ilma_api.report_card import status_inputs
    bank_list=demo_banks(db);inputs=status_inputs(db,bank_list)
    out=[]
    for bank in bank_list:
        fees=[fee_view(r) for r in db.query(ServiceOffer).filter_by(institution_id=bank.id,category='account_fee',hidden=False).all() if fresh(r) and 'quote_unreadable' not in r.condition]
        fees=[r for r in fees if r['value_num'] is not None]
        interest=[r for r in savings_rates(db,bank) if r['product_type']=='savings' and r['audience']!='check']
        if not fees and not interest:continue
        b=bank_view(db,bank,inputs=inputs);code=b['status']['code'];b['status'].update(label_bn=RISK[code][0],label_en=RISK[code][1])
        cards=[r for r in fees if r['is_debit'] and r['attribute']=='annual_fee']
        main=next((r for r in cards if r['variant']=='main'),None)
        replacement=next((r for r in fees if main and r['product']==main['product'] and r['attribute']=='card_replacement_fee'),None)
        b.update(interest_slabs=interest,maintenance_slabs=[r for r in fees if r['attribute']=='maintenance_fee_half_yearly'],debit_main=main,debit_replacement=replacement,debit_variants=[r for r in cards if r['variant']=='variant'],debit_excluded=[r for r in cards if r['variant']=='excluded'],sms=next((r for r in fees if r['attribute']=='sms_alert_fee'),None),other=[r for r in fees if r['attribute'] in OTHER],all_fees=fees)
        out.append(b)
    return out

def catalog(db,item='savings',audience='all'):
    result=dict(choice=dict(product_type='account_fee',item=item,audience=audience),banks=banks(db),defaults=dict(balance=100000,card=True,sms=True))
    from ilma_api.account_readout import readouts
    result['readouts']=readouts(result)
    from ilma_api.deposit_catalog import catalog as deposit_catalog
    from ilma_api.deposit_readout import PLANS
    bank_views={b['id']:{k:b[k] for k in ('id','slug','name_bn','name_en','status','aliases')} for b in result['banks']}
    deposits=deposit_catalog(db,'savings',readout_plans=[p for p in PLANS if p[0]=='savings'],bank_views=bank_views)
    result['deposit_readouts']={k:v for k,v in deposits['readouts'].items() if k.startswith('savings-')}
    return result
