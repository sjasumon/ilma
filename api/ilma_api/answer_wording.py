"""Connected, deterministic narration from retrieved facts. Never reads user prose.
Exact facts remain on the source card; only spoken ratios/profit are rounded.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
from ilma_api.db import Institution, Fact, Rating, ServiceOffer, InsuranceRule, BankIncident, Event
from ilma_api.rules.reasons import format_number

@dataclass
class Narration:
    speech: str
    fact_ids: list[str]
    insurance_bank_ids: list[int]


def clean(text):
    text=re.sub(r'\b(?:PLC|Ltd|Limited)\b\.?|পিএলসি|লিমিটেড','',text,flags=re.I)
    # Source titles remain exact on the card. Speech uses ordinary punctuation.
    text=re.sub(r'[:;()\[\]—–-]',' ',text)
    return ' '.join(text.split()).strip(' ,।.')


def bank_name(db,id,bn):
    bank=db.get(Institution,id) if id else None
    return clean(bank.name_bn if bn else bank.name_en) if bank else ('এই ব্যাংক' if bn else 'this bank')


def possessive(name,bn):
    if not bn:return name+'’s'
    return name+'র' if name.endswith(('ি','ী','া','ো','ে','ই','ও')) else name+'ের'


def rounded(value,bn):
    value=Decimal(str(value));absolute=abs(value)
    # Never turn a small nonzero ratio into an apparently exact zero.
    precision=Decimal(1).scaleb(min(-1,absolute.adjusted())) if 0<absolute<1 else Decimal('1')
    result=absolute.quantize(precision,rounding=ROUND_HALF_UP)
    text=format(result.normalize(),'f')
    return text.translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')) if bn else text


def year(row,bn):
    match=re.search(r'(?:19|20)\d{2}',row.period or '')
    value=match[0] if match else str(row.period_end.year)
    return format_number(int(value),bn=bn,group=False)


PRODUCTS={'fdr':('এফডিআর','FDR'),'dps':('ডিপিএস','DPS'),'savings':('সঞ্চয়ী হিসাব','savings account'),'card':('কার্ড','card'),'home_loan':('গৃহঋণ','home loan'),'auto_loan':('গাড়ির ঋণ','car loan'),'personal_loan':('ব্যক্তিগত ঋণ','personal loan'),'loan_against_fdr':('এফডিআরের বিপরীতে ঋণ','loan against FDR'),'account_fee':('হিসাবের ফি','account fee')}
FEES={'annual_fee':('বার্ষিক ফি','annual fee'),'renewal_fee':('নবায়ন ফি','renewal fee'),'late_fee':('দেরিতে পরিশোধের ফি','late payment fee'),'cash_advance_fee':('নগদ তোলার ফি','cash advance fee'),'rate':('হার','rate'),'interest_rate':('সুদের হার','interest rate')}


MAX_SPOKEN_WORDS=30
MAX_SPOKEN_MS=10000


def validate_spoken_answer(text,language='bn',duration_ms=None):
    from ilma_api.voice_numbers import pronounce
    if max(len(text.split()),len(pronounce(text,language).split()))>MAX_SPOKEN_WORDS:
        raise ValueError('Spoken answer exceeds 30 words')
    if len(re.findall(r'[।!?]|(?<![0-9০-৯])\.(?=\s|$)',text))>3:
        raise ValueError('Spoken answer exceeds two sentences plus question')
    if duration_ms is not None and duration_ms>MAX_SPOKEN_MS:
        raise ValueError('Spoken answer exceeds 10 seconds')


def spoken_bank_name(db,id,bn):
    bank=db.get(Institution,id) if id else None
    # These established brands are not the shortest/misheard ASR aliases.
    brands={'bankasia':('ব্যাংক এশিয়া','Bank Asia'),'bracbank':('ব্র্যাক','BRAC'),'citybank':('সিটি','City'),'dutchbangl':('ডাচ বাংলা','DBBL'),'ebl':('ইবিএল','EBL'),'islamibank':('ইসলামী ব্যাংক','Islami Bank'),'mtb':('এমটিবি','MTB'),'nbl':('ন্যাশনাল','National'),'nccbank':('এনসিসি','NCC'),'primebank':('প্রাইম','Prime'),'sbacbank':('এসবিএসি','SBAC')}
    return brands[bank.slug][0 if bn else 1] if bank and bank.slug in brands else bank_name(db,id,bn)


def spoken_percent(value,bn,negative=False):
    number=abs(Decimal(str(value)))
    precision=Decimal(1).scaleb(number.adjusted()) if 0<number<Decimal('.1') else Decimal('.1') if negative or 0<number<1 else Decimal('1')
    number=number.quantize(precision,rounding=ROUND_HALF_UP)
    if bn and number%1==Decimal('.5') and number>=3:
        return 'সাড়ে '+format_number(int(number),bn=True,group=False)+'%'
    text=format(number.normalize(),'f')
    return (text.translate(str.maketrans('0123456789','০১২৩৪৫৬৭৮৯')) if bn else text)+'%'


def brief_fact(db,item,bn,bank_id):
    key=item['fact_id'];row=db.get(Fact,key)
    if row and row.institution_id==bank_id:
        value=Decimal(row.value);when=year(row,bn)
        calculated=('হিসাবে ' if bn else 'Calculated ') if row.basis.endswith('_calculated') else ''
        if row.metric=='crar':
            cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
            total=(Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer'])))*100
            limit=spoken_percent(total,bn,negative=True);number=spoken_percent(value*100,bn,negative=value<0)
            if value<0:return calculated+(f'মূলধন মাইনাস {number}, অর্থাৎ ঘাটতি' if bn else f'capital is minus {number}, a shortfall')
            return calculated+(f'মূলধন প্রায় {number}, লাগে {limit}' if bn else f'capital’s about {number}, needs {limit}')
        if row.metric=='npl_ratio':
            number=rounded(value*100,bn)
            return calculated+(f'প্রতি ১০০ টাকা ঋণে প্রায় {number} টাকায় আদায়ের সমস্যা' if bn else f'about {number} in every 100 taka lent has repayment problems')
        if row.metric=='net_profit':
            number=rounded(value/10000000,bn)
            return (f'{when} সালে নিট '+('লোকসান' if value<0 else 'মুনাফা')+f' প্রায় {number} কোটি টাকা') if bn else f'{when} net '+('loss' if value<0 else 'profit')+f' was about {number} crore taka'
        if row.metric=='provision_shortfall':
            if value<=0:return 'ঋণক্ষতির জন্য রাখা টাকায় ঘাটতি নেই' if bn else 'no shortfall is reported in loan-loss reserves'
            number=rounded(value/10000000,bn)
            return f'ঋণক্ষতির জন্য রাখা টাকায় প্রায় {number} কোটি ঘাটতি' if bn else f'loan-loss reserves have a shortfall of about {number} crore taka'
    rating=db.get(Rating,key)
    if rating and rating.institution_id==bank_id:
        grade=clean(rating.long_term);agency=clean(rating.agency)
        # Long agency names stay on the source card, never cropped mid-name.
        if len(agency.split())>2:agency='সংস্থাটির' if bn else 'The agency’s'
        text=f'{agency} '+('তাদের সর্বোচ্চ ' if grade=='AAA' and not (rating.valid_to and rating.valid_to<date.today()) else '')+f'{grade} রেটিং দিয়েছে' if bn else f'{agency} rated it {grade}'
        if rating.valid_to and rating.valid_to<date.today():text+=', মেয়াদ শেষ' if bn else ', now expired'
        elif grade=='AAA' and not bn:text+=', its highest grade'
        if rating.outlook in {'negative','developing'}:text+=(', পূর্বাভাস '+('নেতিবাচক' if rating.outlook=='negative' else 'অনিশ্চিত')) if bn else ', outlook '+rating.outlook
        return text
    incident=db.get(BankIncident,key)
    event=db.get(Event,key) if not incident else None
    record=incident or event
    if record and record.institution_id==bank_id:
        title=clean(record.title_bn if bn else record.title_en)
        official=record.official
        date_value=(record.started_on or record.first_reported_on) if incident else record.event_date
        when=format_number(date_value.year,bn=bn,group=False)
        if len(title.split())>6 or len(title)>55:
            from ilma_api.incidents import TYPE_LABELS
            title=TYPE_LABELS.get(incident.kind,('ঘটনার নথি','an incident record'))[0 if bn else 1] if incident else ('ঘটনার নথি' if bn else 'an incident record')
        text=f'{when} সালে {title}' if bn else f'{when} records describe {title}'
        if incident and incident.status in {'acquitted','case_withdrawn','settled','convicted','charged','case_filed'}:
            from ilma_api.incidents import STATUS_LABELS
            text+=', '+STATUS_LABELS[incident.status][0 if bn else 1]
        if not official:text+=', সরকারিভাবে নিশ্চিত নয়' if bn else ', not officially confirmed'
        return text
    return clean(item['text_bn' if bn else 'text_en'])


def brief_insurance(db,bank_id,bn,short=False):
    bank=db.get(Institution,bank_id) if bank_id else None
    rule=db.get(InsuranceRule,bank.type if bank else 'bank')
    if not rule or not rule.source or not rule.covered or not rule.limit_bdt:
        return 'সুরক্ষার নির্ভরযোগ্য শর্ত এখনো নেই' if bn else 'Reliable protection terms are unavailable'
    if 'per depositor per member bank' not in rule.text_en or 'combining accounts' not in rule.text_en:
        return 'সুরক্ষার শর্ত কার্ডে দেখুন' if bn else 'See the protection terms on the card'
    limit=(format_number(rule.limit_bdt/100000,bn=bn,group=False)+(' লাখ' if bn else ' lakh')) if rule.limit_bdt%100000==0 else format_number(rule.limit_bdt,bn=bn,group=False)
    if short:return f'শর্ত মেনে জনে {limit} পর্যন্ত সুরক্ষা' if bn else f'Eligible deposits cap at {limit} per person'
    return (f'এক ব্যাংকে সব হিসাব মিলিয়ে সুরক্ষিত আমানতে জনপ্রতি সর্বোচ্চ {limit} টাকা সুরক্ষা' if bn else f'Eligible deposits cover up to {limit} taka per person per member bank, accounts combined')


def brief_offer(db,item,bn,comparison=False):
    row=db.get(ServiceOffer,item['fact_id'])
    if not row or row.institution_id!=item.get('institution_id') or row.hidden or row.variant=='excluded' or row.doc_date>date.today():return None
    name=spoken_bank_name(db,row.institution_id,bn)
    product=PRODUCTS.get(row.product_type,('সেবা','service'))[0 if bn else 1]
    term=('এক বছরের' if row.tenor_months==12 else format_number(row.tenor_months,bn=bn,group=False)+' মাসের') if bn and row.tenor_months else ('one-year' if row.tenor_months==12 else str(row.tenor_months)+'-month') if row.tenor_months else ''
    # Speech uses spaces, not compound punctuation; card retains full product names.
    term=term.replace('-',' ')
    number=format_number(row.value_num,bn=bn,group=False) if row.value_num is not None else None
    if number is None or row.unit not in {'pct_year','bdt'}:return 'এই সেবার শর্ত কার্ডে আছে' if bn else 'The service terms are on the card'
    label=('আনুমানিক মুনাফা' if row.basis=='islamic' else 'সুদ') if bn else ('provisional profit' if row.basis=='islamic' else 'interest')
    if row.unit=='pct_year':
        text=f'{possessive(name,bn)} {term} {product} {label} {number}%' if bn else f'{name} {term} {product} {label} is {number}%'
    else:
        fee=FEES.get(row.attribute,('ফি','fee'))[0 if bn else 1]
        text=f'{possessive(name,bn)} {product} {fee} {number} টাকা' if bn else f'{name} {product} {fee} is {number} taka'
    if row.stale or (date.today()-row.doc_date).days>365:text+=', পুরনো তথ্য' if bn else ', old information'
    return text



def brief_comparison(db,items,bn):
    rows=[db.get(ServiceOffer,item['fact_id']) for item in items[:2]]
    rows=[row for row,item in zip(rows,items) if row and row.institution_id==item.get('institution_id') and not row.hidden and row.variant!='excluded' and row.doc_date<=date.today() and row.value_num is not None]
    if len(rows)<2:return None
    fields=('product_type','tenor_months','attribute','unit','basis')
    if any(getattr(rows[0],key)!=getattr(rows[1],key) for key in fields):return None
    first,second=rows
    if first.unit not in {'pct_year','bdt'}:return 'তুলনার শর্ত কার্ডে আছে' if bn else 'Comparison terms are on the cards'
    product=PRODUCTS.get(first.product_type,('সেবা','service'))[0 if bn else 1]
    term=(('এক বছরের' if first.tenor_months==12 else format_number(first.tenor_months,bn=True,group=False)+' মাসের') if bn else ('one year' if first.tenor_months==12 else str(first.tenor_months)+' months')) if first.tenor_months else ''
    values=[format_number(r.value_num,bn=bn,group=False)+('%' if r.unit=='pct_year' else ' টাকা' if bn else ' taka') for r in rows]
    names=[spoken_bank_name(db,r.institution_id,bn) for r in rows]
    label=('আনুমানিক মুনাফা' if first.basis=='islamic' else 'সুদের হার') if first.unit=='pct_year' and bn else 'provisional profit' if first.basis=='islamic' else 'interest' if first.unit=='pct_year' else FEES.get(first.attribute,('ফি','fee'))[0 if bn else 1]
    text=f'{term} {product} {label} {names[0]} {values[0]}, {names[1]} {values[1]} জানিয়েছে' if bn else f'{term} {product} {label} quotes are {values[0]} at {names[0]} and {values[1]} at {names[1]}'
    if any(r.stale or (date.today()-r.doc_date).days>365 for r in rows):text+=', পুরনো তথ্য' if bn else ', old information'
    return text

def compose(db,facts,conversation,question,tool,action=None,repeat=False,replay_fact_ids=None):
    bn=conversation.get('language','bn')=='bn';language='bn' if bn else 'en';bank_id=conversation.get('institution_id')
    seen=set(conversation.get('spoken_fact_ids',[]));insurance_banks=list(conversation.get('insurance_bank_ids',[]));used=[];bodies=[]
    if action and action['type'] in {'stop','open_report','open_proof','end'}:question=''
    fresh=[f for f in facts if (repeat or f['fact_id'] not in seen) and (replay_fact_ids is None or f['fact_id'] in replay_fact_ids)]
    ending='।' if bn else '.'
    def assembled(parts):return ' '.join(clean(part)+ending for part in parts if part)+((' '+question) if question else '')
    def add(text,item=None,force=False):
        if not text:return False
        candidate=assembled([*bodies,text])
        try:validate_spoken_answer(candidate,language)
        except ValueError:return False
        if not force and bodies and len(candidate)>(125 if bn else 120):return False
        bodies.append(text)
        if item and item['fact_id'] not in used:used.append(item['fact_id'])
        return True
    name=spoken_bank_name(db,bank_id,bn)
    if tool=='bank_summary':
        status=next((f for f in facts if f.get('status')),None);code=(status or {}).get('status',{}).get('code','no_data')
        say_status=bool(status and (status['fact_id'] in replay_fact_ids if replay_fact_ids is not None else repeat or status['fact_id'] not in seen))
        starts={'strong':(f'{possessive(name,True)} অবস্থা ভালো',f'{name} looks good'),'watch':(f'{possessive(name,True)} কিছু বিষয়ে সতর্কতা দরকার',f'{name} has some warning signs'),'high':(f'{possessive(name,True)} ঝুঁকি বেশি',f'{name} faces risk'),'no_data':(f'{name} সম্পর্কে যথেষ্ট তথ্য নেই',f'{name} cannot be assessed')}
        start=starts.get(code,starts['no_data'])[0 if bn else 1] if say_status else ('এই ব্যাংকের সারাংশ আগেই বলেছি' if bn else 'I already summarised this bank')
        reasons=[f for f in fresh if not f['fact_id'].startswith(('status:','insurance:'))]
        reason=('হালনাগাদ হিসাব নেই' if bn else 'current records are missing') if code=='no_data' else brief_fact(db,reasons[0],bn,bank_id) if reasons else ('কারণগুলো আগেই ব্যাখ্যা করেছি' if bn else 'the reasons were already explained')
        ins=next((f for f in facts if f['fact_id'].startswith('insurance:')),None)
        speak_ins=bool(code=='high' and ins and (ins['fact_id'] in replay_fact_ids if replay_fact_ids is not None else repeat or bank_id not in insurance_banks))
        reason_said=False
        if speak_ins:
            numeric=db.get(Fact,reasons[0]['fact_id']) if reasons else None
            if numeric and numeric.metric=='crar':
                cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
                minimum=Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer']))
                if numeric.value<minimum:reason='মূলধন কম' if bn else 'capital’s short'
            elif numeric and numeric.metric=='npl_ratio':reason='খেলাপি ঋণ বেশি' if bn else 'problem loans are high'
            combined=start+(', কারণ ' if bn else ' because ')+reason
            reason_said=add(combined,status if say_status else None,True)
            if add(brief_insurance(db,bank_id,bn,short=True),ins,True) and bank_id not in insurance_banks:insurance_banks.append(bank_id)
        else:
            reason_said=add(start+(', কারণ ' if bn else ' because ')+reason,status if say_status else None,True)
        if reasons and reason_said:used.append(reasons[0]['fact_id'])
    elif tool in {'bank_reasons','bank_figures','bank_history'}:
        for item in [f for f in fresh if not f['fact_id'].startswith('script:')]:
            if len(bodies)>=1:break
            add(brief_fact(db,item,bn,bank_id),item)
            if tool=='bank_history':break
        if not bodies:add(('বিস্তারিত কার্ডে আছে' if bn else 'Details are on the card') if fresh else ('এই অঙ্কগুলো আগেই বলেছি, বিস্তারিত কার্ডে আছে' if bn else 'These figures were already explained, exact values are on the card') if any(not f['fact_id'].startswith('script:') for f in facts) else ('এই তথ্য এখনো নেই' if bn else 'This information is unavailable'))
    elif tool=='insurance':
        add(brief_insurance(db,bank_id,bn),facts[0] if facts else None,True)

        if bank_id and bank_id not in insurance_banks:insurance_banks.append(bank_id)
    elif tool=='service_compare':
        text=brief_comparison(db,facts,bn)
        if text:
            if add(text):used.extend(item['fact_id'] for item in facts[:2])
            else:add('তুলনার অঙ্ক কার্ডে আছে' if bn else 'Comparison figures are on the card')
        else:add('একই শর্তে মেলানোর তথ্য নেই' if bn else 'No matching quote is available on the same terms')
    elif tool=='service_detail':
        for item in facts[:1]:add(brief_offer(db,item,bn),item)
        if not bodies:add('এই সেবার তথ্য এখনো নেই' if bn else 'This service information is unavailable')
    elif tool=='services_overview' and any(f.get('counts') for f in facts):
        groups=[PRODUCTS[k][0 if bn else 1] for k in next(f['counts'] for f in facts if f.get('counts')) if k in PRODUCTS]
        add((', '.join(groups[:4])+' সম্পর্কে তথ্য আছে') if bn else 'Information is available on '+', '.join(groups[:4]),facts[0])
    else:
        for item in facts[:1]:add(brief_fact(db,item,bn,bank_id),item)
    if not bodies:add('বিস্তারিত কার্ডে দেখুন' if bn else 'See the card for details')
    speech=assembled(bodies)
    validate_spoken_answer(speech,language)
    return Narration(speech,list(dict.fromkeys(used)),insurance_banks)


# Compatibility for callers loaded before a normal service restart.
def fact_clause(db,item,bn,bank_id):
    return brief_fact(db,item,bn,bank_id)


def offer_clause(db,item,bn,comparison=False):
    return brief_offer(db,item,bn,comparison)


def insurance_clause(db,bank_id,bn,full=False):
    return brief_insurance(db,bank_id,bn,short=not full)
