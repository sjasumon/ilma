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
from ilma_api.rules.reasons import format_number, format_date, MONTHS_BN, MONTHS_EN

@dataclass
class Narration:
    speech: str
    fact_ids: list[str]
    insurance_bank_ids: list[int]


def clean(text):
    text=re.sub(r'\b(?:PLC|Ltd|Limited)\b\.?|পিএলসি|লিমিটেড','',text,flags=re.I)
    # Source titles remain exact on the card. Speech uses ordinary punctuation.
    text=re.sub(r'[:;()\[\]—–]',' ',text)
    return ' '.join(text.split()).strip(' ,।.')


def bank_name(db,id,bn):
    bank=db.get(Institution,id) if id else None
    return clean(bank.name_bn if bn else bank.name_en) if bank else ('এই ব্যাংক' if bn else 'this bank')


def possessive(name,bn):
    if not bn:return name+'’s'
    return name+'ের' if name.endswith('ব্যাংক') else name+' এর'


def rounded(value,bn):
    value=Decimal(str(value));absolute=abs(value)
    # Never turn a small nonzero ratio into an apparently exact zero.
    precision=Decimal('.1') if 0<absolute<1 else Decimal('1')
    result=absolute.quantize(precision,rounding=ROUND_HALF_UP)
    return format_number(result,bn=bn,group=False)


def year(row,bn):
    match=re.search(r'(?:19|20)\d{2}',row.period or '')
    value=match[0] if match else str(row.period_end.year)
    return format_number(int(value),bn=bn,group=False)


def month_year(value,bn):
    return (format_number(value.year,bn=True,group=False)+' সালের '+MONTHS_BN[value.month]) if bn else MONTHS_EN[value.month]+' '+str(value.year)


def fact_clause(db,item,bn,bank_id):
    """Return one plain sentence clause, with original qualifications preserved."""
    key=item['fact_id'];row=db.get(Fact,key)
    if row and row.institution_id==bank_id:
        value=Decimal(row.value);period=year(row,bn)
        calculated=('হিসাব করে পাওয়া ' if bn else 'calculated ') if row.basis.endswith('_calculated') else ''
        if row.metric=='crar':
            cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
            total=Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer']))
            threshold=format_number(total*100,bn=bn,group=False)
            number=rounded(value*100,bn)
            if value<0:
                return (f'{period} সালের হিসাবে {calculated}ব্যাংকের নিজের মূলধনের অনুপাত শূন্যের নিচে, প্রায় মাইনাস {number}%, তাই লোকসান সামলানোর মূলধনে ঘাটতি আছে' if bn else f'in {period}, the {calculated}capital ratio was below zero at about minus {number}%, indicating a shortfall in capital for absorbing losses')
            if value<total:
                return (f'{period} সালের হিসাবে {calculated}মূলধনের অনুপাত প্রায় {number}%, যা বাফারসহ {threshold}% সীমার নিচে, তাই লোকসান সামলানোর মূলধন কম' if bn else f'in {period}, the {calculated}capital ratio was about {number}%, below the {threshold}% threshold including the buffer, so capital for absorbing losses is limited')
            return (f'{period} সালের হিসাবে {calculated}ক্ষতি সামলানোর মূলধনের অনুপাত প্রায় {number}%, যা বাফারসহ {threshold}% সীমা পূরণ করে' if bn else f'in {period}, the {calculated}capital ratio was about {number}%, meeting the {threshold}% threshold including the buffer for absorbing losses')
        if row.metric=='npl_ratio':
            number=rounded(value*100,bn)
            cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
            level=('অনেক বেশি' if value>=Decimal(str(cfg['npl_high'])) else 'বেশি' if value>=Decimal(str(cfg['npl_watch'])) else 'তুলনামূলক কম') if bn else ('very high' if value>=Decimal(str(cfg['npl_high'])) else 'high' if value>=Decimal(str(cfg['npl_watch'])) else 'relatively low')
            return (f'{period} সালের হিসাবে {calculated}প্রতি ১০০ টাকা ঋণের প্রায় {number} টাকা আদায় নিয়ে সমস্যা আছে, যা {level}' if bn else f'in {period}, the {calculated}portion with repayment problems was about {number} taka in every 100 taka lent, which is {level}')
        if row.metric=='net_profit':
            number=rounded(value/Decimal(10000000),bn)
            return (f'{period} সালে ব্যাংকটি প্রায় {number} কোটি টাকা নিট '+('লোকসান করেছে' if value<0 else 'মুনাফা করেছে') if bn else f'in {period}, the bank reported a net '+('loss' if value<0 else 'profit')+f' of about {number} crore taka')
        if row.metric=='provision_shortfall':
            if value<=0:return 'এই হিসাবে সম্ভাব্য ঋণক্ষতির জন্য রাখা টাকায় ঘাটতি দেখানো হয়নি' if bn else 'this figure does not report a shortfall in money set aside for possible loan losses'
            number=rounded(value/Decimal(10000000),bn)
            return (f'সম্ভাব্য ঋণক্ষতির জন্য আলাদা করে রাখার টাকায় প্রায় {number} কোটি টাকার ঘাটতি আছে' if bn else f'the money set aside for possible loan losses has a shortfall of about {number} crore taka')
    rating=db.get(Rating,key)
    if rating and rating.institution_id==bank_id:
        old=bool(rating.valid_to and rating.valid_to<date.today())
        agency=clean(rating.agency);grade=clean(rating.long_term);when=month_year(rating.rated_on,bn)
        text=(f'{when} মাসে {agency} ব্যাংকটিকে {grade} রেটিং দিয়েছিল' if bn else f'in {when}, {agency} rated the bank {grade}')
        if old:text+=', এটি পুরনো রেটিং' if bn else ', and that rating has expired'
        elif grade=='AAA':text+=', এটি ওই সংস্থার সর্বোচ্চ রেটিং' if bn else ', its highest rating'
        if rating.outlook in {'negative','developing'}:text+=', তবে ভবিষ্যৎ পূর্বাভাস '+('নেতিবাচক' if rating.outlook=='negative' else 'অনিশ্চিত') if bn else ', with a '+('negative' if rating.outlook=='negative' else 'developing')+' outlook'
        return text
    incident=db.get(BankIncident,key)
    if incident and incident.institution_id==bank_id:
        when=format_number((incident.started_on or incident.first_reported_on).year,bn=bn,group=False)
        title=clean(incident.title_bn if bn else incident.title_en)
        if not incident.official:
            text=(f'{title} নিয়ে {when} সালের খবর পাওয়া গেছে। এটি খবরে প্রকাশিত তথ্য, সরকারিভাবে নিশ্চিত নয়' if bn else f'reports from {when} described {title}. This is reported information and is not officially confirmed') if not incident.started_on else (f'{when} সালের {title} নিয়ে খবর পাওয়া গেছে। এটি খবরে প্রকাশিত তথ্য, সরকারিভাবে নিশ্চিত নয়' if bn else f'reports described {title} from {when}. This is reported information and is not officially confirmed')
        else:text=(f'পাওয়া প্রাথমিক নথিতে {title} উল্লেখ আছে' if bn else f'the primary records describe {title}')
        if incident.status in {'case_filed','charged','convicted','settled','acquitted','case_withdrawn'}:
            from ilma_api.incidents import STATUS_LABELS
            label=STATUS_LABELS[incident.status][0 if bn else 1]
            text+=(', সর্বশেষ নথিতে '+label) if bn else ', with the latest recorded status of '+label.lower()
        return text
    event=db.get(Event,key)
    if event and event.institution_id==bank_id:
        when=format_number(event.event_date.year,bn=bn,group=False);title=clean(event.title_bn if bn else event.title_en)
        return (f'{when} সালের নথিতে {title} উল্লেখ আছে' if bn and event.official else f'{when} সালে খবরে {title} বলা হয়েছে, এটি সরকারিভাবে নিশ্চিত নয়' if bn else f'a primary document from {when} records {title}' if event.official else f'reports from {when} described {title}, but this is not officially confirmed')
    if item.get('unconfirmed'):
        return 'ঘটনার খবর পাওয়া গেছে, তবে সরকারিভাবে নিশ্চিত নয়' if bn else 'an incident has been reported, but it is not officially confirmed'
    return clean(item['text_bn' if bn else 'text_en'])


def insurance_clause(db,bank_id,bn,full=False):
    bank=db.get(Institution,bank_id) if bank_id else None
    rule=db.get(InsuranceRule,bank.type if bank else 'bank')
    if not rule or not rule.source:return ('আমানত সুরক্ষার নির্ভরযোগ্য শর্ত আমাদের কাছে এখনো নেই' if bn else 'we do not yet have reliable deposit-protection terms')
    # Preserve eligibility, member-bank and combined-account limits from the law.
    qualified=rule.covered and rule.limit_bdt and 'per depositor per member bank' in rule.text_en and 'combining accounts' in rule.text_en
    if not qualified:return clean(rule.text_bn if bn else rule.text_en)
    limit=(format_number(rule.limit_bdt/100000,bn=bn,group=False)+(' লাখ টাকা' if bn else ' lakh taka')) if rule.limit_bdt%100000==0 else format_number(rule.limit_bdt,bn=bn)+(' টাকা' if bn else ' taka')
    if bn:
        text=(f'আমানত সুরক্ষার আওতায় থাকা ব্যাংকে একজনের সব হিসাব মিলিয়ে সর্বোচ্চ {limit} ফেরতের বিধান আছে, সব ধরনের আমানত এই সুরক্ষা পায় না' if full else f'সুরক্ষার আওতায় থাকা আমানতে এই ব্যাংকে সব হিসাব মিলিয়ে একজনের সর্বোচ্চ {limit} ফেরতের বিধান আছে')
    else:text=f'for protected deposits at a member bank, the limit per person across all accounts is {limit}'+(', and not every type of deposit qualifies' if full else '')
    if full and rule.payout_working_days==17 and '10 working days' in rule.text_en and 'then 7' in rule.text_en:
        text+=('। তালিকা পাঠাতে ১০ কার্যদিবস, তারপর প্রয়োজনীয় তথ্য পাওয়ার পর পরিশোধে আরও ৭ কার্যদিবস নির্ধারিত' if bn else '. The depositor list has a 10 working day deadline, followed by 7 working days for payment after the required information is received')
    return text


PRODUCTS={'fdr':('এফডিআর','FDR'),'dps':('ডিপিএস','DPS'),'savings':('সঞ্চয়ী হিসাব','savings account'),'card':('কার্ড','card'),'home_loan':('গৃহঋণ','home loan'),'auto_loan':('গাড়ির ঋণ','car loan'),'personal_loan':('ব্যক্তিগত ঋণ','personal loan'),'loan_against_fdr':('এফডিআরের বিপরীতে ঋণ','loan against FDR'),'account_fee':('হিসাবের ফি','account fee')}
FEES={'annual_fee':('বার্ষিক ফি','annual fee'),'renewal_fee':('নবায়ন ফি','renewal fee'),'late_fee':('দেরিতে পরিশোধের ফি','late payment fee'),'cash_advance_fee':('নগদ তোলার ফি','cash advance fee'),'rate':('হার','rate'),'interest_rate':('সুদের হার','interest rate')}


def offer_clause(db,item,bn,comparison=False):
    row=db.get(ServiceOffer,item['fact_id'])
    if not row or row.institution_id!=item.get('institution_id') or row.hidden or row.variant=='excluded' or row.doc_date>date.today():return None
    name=bank_name(db,row.institution_id,bn);product=PRODUCTS.get(row.product_type,('এই সেবা','this service'))[0 if bn else 1]
    if bn and row.product_type=='account_fee':product='হিসাব'
    if row.product_type=='card':
        labels={'Visa':'ভিসা','Mastercard':'মাস্টারকার্ড','Amex':'অ্যামেক্স','Gold':'গোল্ড','Classic':'ক্লাসিক','Platinum':'প্লাটিনাম','Signature':'সিগনেচার','World':'ওয়ার্ল্ড','Infinite':'ইনফিনিট','Titanium':'টাইটানিয়াম'}
        product=' '.join([labels.get(value,value) if bn else value for value in [row.network,row.tier] if value]+[product])
    if row.value_num is None:return ('এই সেবার নির্দিষ্ট অঙ্ক আমাদের কাছে নেই' if bn else 'we do not have a figure for this service')
    number=format_number(row.value_num,bn=bn,group=False)
    if row.tenor_months:
        months=format_number(row.tenor_months,bn=bn,group=False)
        term=('এক বছরের' if row.tenor_months==12 else months+' মাসের') if bn else ('one year' if row.tenor_months==12 else months+' months')
        product=term+' '+product
    published=month_year(row.doc_date,bn)
    product_label=product+'ের' if bn else product
    if row.unit=='pct_year':
        label=('আনুমানিক মুনাফার হার' if row.basis=='islamic' else 'বার্ষিক সুদের হার') if bn else ('provisional profit rate' if row.basis=='islamic' else 'annual interest rate')
        text=f'{possessive(name,bn)} {product_label} {label} {number}%' if bn else f'{name} lists {number}% as the {label} for its {product}'
    else:
        label=FEES.get(row.attribute,('ফি','fee'))[0 if bn else 1]
        unit=' টাকা' if bn and row.unit=='bdt' else ' taka' if row.unit=='bdt' else ' '+clean(row.unit)
        text=f'{possessive(name,bn)} {product_label} {label} {number}{unit}' if bn else f'{name} lists a {product} {label} of {number}{unit}'
    text+=f', {published} মাসের হারতালিকা অনুযায়ী' if bn else f', according to its {published} schedule'
    if row.stale or (date.today()-row.doc_date).days>365:text+=', এটি পুরনো তথ্য' if bn else ', and this information is old'
    # A fixed, conditional arithmetic example; no personal amount is requested.
    if not comparison and row.product_type=='fdr' and row.tenor_months==12 and row.unit=='pct_year' and row.basis=='conventional' and not row.stale and (date.today()-row.doc_date).days<=365:
        example=format_number(Decimal(100000)*row.value_num/100,bn=bn)
        text+=f'। শুধু হিসাবের উদাহরণে এই হার প্রযোজ্য হলে ১ লাখে বছরে {example} টাকা সুদ, কর কাটার আগে' if bn else f'. As a fixed example, if this rate applies, 1 lakh earns {example} taka in a year before tax'
    return text


def compose(db,facts,conversation,question,tool,action=None,repeat=False):
    bn=conversation.get('language','bn')=='bn';bank_id=conversation.get('institution_id')
    seen=set(conversation.get('spoken_fact_ids',[]));insurance_banks=list(conversation.get('insurance_bank_ids',[]));used=[];sentences=[]
    stop=bool(action and action['type'] in {'stop','open_report','open_proof','end'})
    name=bank_name(db,bank_id,bn)
    fresh=[f for f in facts if repeat or f['fact_id'] not in seen]
    def add(text,item=None):
        if text:sentences.append(clean(text))
        if item and item['fact_id'] not in used:used.append(item['fact_id'])
    if tool=='bank_summary':
        status=next((f for f in facts if f.get('status')),None)
        code=(status or {}).get('status',{}).get('code','no_data')
        starts={'strong':(f'আমাদের পাওয়া তথ্যে {possessive(name,True)} অবস্থা ভালো',f'Our records show that {name} is in good condition'),'watch':(f'{possessive(name,True)} কিছু বিষয়ে সতর্ক থাকা দরকার',f'Our records flag some concerns about {name}'),'high':(f'{possessive(name,True)} তথ্যে ঝুঁকির বড় সংকেত আছে',f'Our records flag high risk at {name}'),'no_data':(f'{name} কেমন আছে বলার মতো যথেষ্ট তথ্য আমাদের কাছে নেই',f'We do not have enough information to assess {name}')}
        if status and (repeat or status['fact_id'] not in seen):add(starts.get(code,starts['no_data'])[0 if bn else 1],status)
        else:add('এই ব্যাংকের সারাংশ আগেই বলেছি' if bn else 'I have already summarised this bank')
        reasons=[f for f in fresh if not f['fact_id'].startswith(('status:','insurance:'))]
        if code=='no_data':add('কারণ হালনাগাদ হিসাবের কিছু তথ্য এখনও পাওয়া যায়নি' if bn else 'That is because some current financial records are missing',reasons[0] if reasons else None)
        elif reasons:
            add(('কারণ, ' if bn else 'That is because ')+fact_clause(db,reasons[0],bn,bank_id),reasons[0])
        else:add('এর কারণগুলো আগেই ব্যাখ্যা করেছি, সঠিক অঙ্ক কার্ডে আছে' if bn else 'I have explained the reasons, and the exact figures are on the card')
        ins=next((f for f in facts if f['fact_id'].startswith('insurance:')),None)
        if ins and (repeat or bank_id not in insurance_banks):
            add(('আর ' if bn else 'Also, ')+insurance_clause(db,bank_id,bn),ins)
            if bank_id not in insurance_banks:insurance_banks.append(bank_id)
    elif tool in {'bank_reasons','bank_figures'}:
        selected=[f for f in fresh if not f['fact_id'].startswith('script:')][:2]
        for index,item in enumerate(selected):
            lead=('আরও বলি, ' if index==0 and tool=='bank_reasons' else 'এছাড়া ' if index else '') if bn else ('To explain further, ' if index==0 and tool=='bank_reasons' else 'Also, ' if index else '')
            add(lead+fact_clause(db,item,bn,bank_id),item)
        if not selected:
            has_figures=any(not f['fact_id'].startswith('script:') for f in facts)
            add(('এই অঙ্কগুলো আগেই ব্যাখ্যা করেছি, সঠিক তথ্য কার্ডে আছে' if bn else 'I have already explained these figures, and the exact values are on the card') if has_figures else ('এই হিসাবের তথ্য আমাদের কাছে এখনো নেই' if bn else 'We do not have these financial figures yet'))
    elif tool=='bank_history':
        selected=[f for f in fresh if not f['fact_id'].startswith('script:')][:1]
        if selected:
            add(fact_clause(db,selected[0],bn,bank_id),selected[0])
            add('এটি আমাদের পাওয়া নথির কথা, সম্পূর্ণ ইতিহাস নয়' if bn else 'This describes the records we have, not a complete history')
        else:add('এই ব্যাংকের নতুন কোনো ঘটনার নথি আমাদের কাছে নেই, এর মানে ঘটনা ঘটেনি এমন নয়' if bn else 'We have no further incident record for this bank, which does not mean there have been no incidents')
    elif tool=='insurance':
        add(insurance_clause(db,bank_id,bn,full=True),facts[0] if facts else None)
        if bank_id and bank_id not in insurance_banks:insurance_banks.append(bank_id)
    elif tool in {'service_detail','service_compare'}:
        selected=facts[:2] if tool=='service_compare' else facts[:1]
        for index,item in enumerate(selected):
            text=offer_clause(db,item,bn,tool=='service_compare')
            if text:
                if tool=='service_compare' and len(selected)>1:text=(('একই মেয়াদ ও শর্তে তুলনা করলে, ' if index==0 else 'অন্যদিকে ') if bn else ('For the same term and conditions, ' if index==0 else 'In comparison, '))+text
                add(text,item)
        if tool=='service_compare' and len(selected)==1:add('আমাদের নথিতে একই শর্তে আরেকটি ব্যাংকের হার পাওয়া যায়নি' if bn else 'Our records do not contain another bank’s rate on the same terms')
        if not sentences:add('এই সেবার হার বা শর্ত আমাদের কাছে এখনো নেই' if bn else 'We do not yet have the rate or terms for this service')
    elif tool=='services_overview' and any(f.get('counts') for f in facts):
        groups=[PRODUCTS[key][0 if bn else 1] for key in next(f['counts'] for f in facts if f.get('counts')) if key in PRODUCTS]
        add((f'{possessive(name,True)} '+', '.join(groups[:4])+' সম্পর্কে তথ্য আছে') if bn else f'We have information about {name}’s '+', '.join(groups[:4]),facts[0])
    else:
        for item in facts[:1]:add(fact_clause(db,item,bn,bank_id),item)
    if not sentences:add('এই তথ্যটা আমাদের কাছে এখনো নেই' if bn else 'We do not have that information yet')
    ending='।' if bn else '.'
    # Internal full stops (insurance procedure/example) are intentional sentences.
    speech=' '.join(s[0].upper()+s[1:]+ending if not s.endswith(('।','.','?')) else s for s in sentences)
    if question and not stop:speech+=' '+question
    return Narration(speech,used,insurance_banks)
