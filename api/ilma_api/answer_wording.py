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
    completed_fact_ids: list[str] | None = None
    all_fact_ids: list[str] | None = None
    more: bool = False
    page: int = 0


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


MAX_SPOKEN_WORDS=70
MAX_SPOKEN_MS=30000


def validate_spoken_answer(text,language='bn',duration_ms=None,first=False):
    if len(text.split())>(45 if first else MAX_SPOKEN_WORDS):
        raise ValueError('Spoken answer exceeds wording budget')
    if duration_ms is not None and duration_ms>MAX_SPOKEN_MS:
        raise ValueError('Spoken answer exceeds 30 seconds')


def spoken_bank_name(db,id,bn):
    bank=db.get(Institution,id) if id else None
    return bank_name(db,id,bn)


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
            if value<0:return calculated+(f'লোকসানে ব্যাংকের নিজের মূলধন শেষ হয়ে গেছে, এখন মাইনাস {number}, অথচ বাফারসহ লাগে {limit}' if bn else f'Losses have exhausted its own capital, now minus {number}, against a {limit} minimum including the buffer')
            return calculated+(f'ব্যাংকের নিজের মূলধন প্রায় {number}, বাফারসহ ন্যূনতম লাগে {limit}' if bn else f'Its own capital is about {number}, against a {limit} minimum including the buffer')
        if row.metric=='npl_ratio':
            number=rounded(value*100,bn)
            return calculated+(f'প্রতি ১০০ টাকা ঋণে প্রায় {number} টাকা ফেরত আসছে না' if bn else f'About {number} taka in every 100 lent has repayment problems')
        if row.metric=='net_profit':
            number=rounded(value/10000000,bn)
            return (f'{when} সালে {bank_name(db,bank_id,True)} প্রায় {number} কোটি টাকা নিট '+('লোকসান করেছে' if value<0 else 'মুনাফা করেছে')) if bn else f'In {when}, {bank_name(db,bank_id,False)} made a net '+('loss' if value<0 else 'profit')+f' of about {number} crore taka'
        if row.metric=='provision_shortfall':
            if value<=0:return 'ব্যাংকের ঋণক্ষতির জন্য রাখা টাকায় ঘাটতি নেই' if bn else 'The records report no shortfall in loan-loss reserves'
            number=rounded(value/10000000,bn)
            return f'ব্যাংকের ঋণক্ষতির জন্য রাখা টাকায় প্রায় {number} কোটি টাকার ঘাটতি আছে' if bn else f'Its loan-loss reserves have a shortfall of about {number} crore taka'
    rating=db.get(Rating,key)
    if rating and rating.institution_id==bank_id:
        grade=clean(rating.long_term);agency=clean(rating.agency)
        # Long agency names stay on the source card, never cropped mid-name.
        if len(agency.split())>2:agency='সংস্থাটির' if bn else 'The agency’s'
        text=f'রেটিং সংস্থা {agency} '+('তাদের সর্বোচ্চ ' if grade=='AAA' and not (rating.valid_to and rating.valid_to<date.today()) else '')+f'{grade} রেটিং দিয়েছে' if bn else f'{agency} rated it {grade}'
        if rating.rated_on:
            months=['জানুয়ারি','ফেব্রুয়ারি','মার্চ','এপ্রিল','মে','জুন','জুলাই','আগস্ট','সেপ্টেম্বর','অক্টোবর','নভেম্বর','ডিসেম্বর']
            text+=f', {format_number(rating.rated_on.year,bn=True,group=False)} সালের {months[rating.rated_on.month-1]} মাসে' if bn else f' in {rating.rated_on:%B %Y}'
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
        text=f'{when} সালের নথিতে এই ব্যাংক সম্পর্কে বলা হয়েছিল, {title}' if bn else f'In {when}, records about this bank described {title}'
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
        return 'সুরক্ষার নির্ভরযোগ্য শর্ত এখনো আমাদের কাছে নেই' if bn else 'We do not yet have reliable protection terms'
    if 'per depositor per member bank' not in rule.text_en or 'combining accounts' not in rule.text_en:
        return 'সুরক্ষার শর্ত কার্ডে দেখুন' if bn else 'See the protection terms on the card'
    limit=(format_number(rule.limit_bdt/100000,bn=bn,group=False)+(' লাখ' if bn else ' lakh')) if rule.limit_bdt%100000==0 else format_number(rule.limit_bdt,bn=bn,group=False)
    if short:return f'শর্ত মেনে জনে {limit} টাকা পর্যন্ত সুরক্ষা পাবেন' if bn else f'Eligible deposits are protected up to {limit} taka per person'
    return (f'শর্ত মেনে সদস্য ব্যাংকের সব হিসাব মিলিয়ে জনপ্রতি {limit} টাকা পর্যন্ত আমানত সুরক্ষিত থাকে' if bn else f'Eligible deposits are protected up to {limit} taka per person per member bank, with accounts combined. Conditions apply')


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
        text=f'{possessive(name,True)} {term} {product}ে {label} {number}% হয়' if bn else f'{name} {term} {product} {label} is {number}%'
    else:
        fee=FEES.get(row.attribute,('ফি','fee'))[0 if bn else 1]
        text=f'{possessive(name,bn)} {product} {fee} {number} টাকা হয়' if bn else f'{name} {product} {fee} is {number} taka'
    if row.product_type=='fdr' and row.tenor_months==12 and row.unit=='pct_year' and row.basis=='conventional' and not row.stale and (date.today()-row.doc_date).days<=365:
        interest=format_number(Decimal(str(row.value_num))*1000,bn=bn,group=False)
        text+=f'। এই হার প্রযোজ্য হলে এক লাখ টাকায় বছরে প্রায় {interest} টাকা সুদ পাবেন, কর কাটার আগে' if bn else f'. If this rate applies, a fixed one lakh taka example earns about {interest} taka a year before tax'
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

def page_narration(entries,question,bn,page=0):
    """Page source wording at clause/word boundaries, never cut an audio stream."""
    ending='।' if bn else '.';more_question='আরও শুনবেন?' if bn else 'Would you like to hear more?'
    pieces=[]
    for text,ids in entries:
        words=clean(text).split()
        # Conservative 30-word chunks leave room for number/acronym expansion.
        while words:
            count=min(30,len(words))
            if count<len(words):
                boundaries=[i+1 for i,w in enumerate(words[:count]) if w.endswith((',', '।','.')) and i>=12]
                if boundaries:count=boundaries[-1]
            pieces.append((' '.join(words[:count]),ids,count==len(words)));words=words[count:]
    pages=[];current=[]
    for piece in pieces:
        if current and sum(len(x[0].split()) for x in current)+len(piece[0].split())>45:pages.append(current);current=[]
        current.append(piece)
    if current:pages.append(current)
    if not pages:return '',[],[],False,0
    page=min(max(0,page),len(pages)-1);more=page+1<len(pages)
    selected=pages[page]
    speech=' '.join(clean(t)+ending for t,_,_ in selected)+' '+(more_question if more else question)
    used=list(dict.fromkeys(i for _,ids,_ in selected for i in ids))
    completed=[i for i in used if not any(i in ids for group in pages[page+1:] for _,ids,_ in group)]
    return speech.strip(),used,completed,more,page


def compose(db,facts,conversation,question,tool,action=None,repeat=False,replay_fact_ids=None,page=0):
    bn=conversation.get('language','bn')=='bn';language='bn' if bn else 'en';bank_id=conversation.get('institution_id')
    seen=set(conversation.get('spoken_fact_ids',[]));insurance_banks=list(conversation.get('insurance_bank_ids',[]));used=[];bodies=[];entries=[]
    if action and action['type'] in {'stop','open_report','open_proof','end'}:question=''
    fresh=[f for f in facts if (repeat or f['fact_id'] not in seen) and (replay_fact_ids is None or f['fact_id'] in replay_fact_ids)]
    ending='।' if bn else '.'
    def assembled(parts):return ' '.join(clean(part)+ending for part in parts if part)+((' '+question) if question else '')
    def add(text,item=None,force=False):
        if not text:return False
        candidate=assembled([*bodies,text])
        if tool=='bank_summary' and len(candidate.split())>(45 if bn else 47):return False
        bodies.append(text);entries.append((text,[item['fact_id']] if item else []))
        if item and item['fact_id'] not in used:used.append(item['fact_id'])
        return True
    name=spoken_bank_name(db,bank_id,bn)
    if tool=='bank_summary':
        status=next((f for f in facts if f.get('status')),None);code=(status or {}).get('status',{}).get('code','no_data')
        say_status=bool(status and (status['fact_id'] in replay_fact_ids if replay_fact_ids is not None else repeat or status['fact_id'] not in seen))
        starts={'strong':(f'{possessive(name,True)} অবস্থা ভালো',f'{name} is in good condition'),'watch':(f'{possessive(name,True)} কিছু বিষয়ে সতর্কতা দরকার',f'{name} has some warning signs'),'high':(f'{possessive(name,True)} ঝুঁকি বেশি',f'{name} faces risk'),'no_data':(f'{name} সম্পর্কে যথেষ্ট তথ্য নেই',f'{name} cannot be assessed')}
        start=starts.get(code,starts['no_data'])[0 if bn else 1] if say_status else ('এই ব্যাংকের সারাংশ আগেই বলেছি' if bn else 'I already summarised this bank')
        reasons=[f for f in fresh if not f['fact_id'].startswith(('status:','insurance:'))]
        ins=next((f for f in facts if f['fact_id'].startswith('insurance:')),None)
        speak_ins=bool(ins and (ins['fact_id'] in replay_fact_ids if replay_fact_ids is not None else repeat or bank_id not in insurance_banks))
        add(start,status if say_status else None,True)
        # Budget the whole paragraph, reserving the conditional protection line.
        protection=brief_insurance(db,bank_id,bn,short=True) if speak_ins else None
        for index,item in enumerate(reasons[:1 if code=='no_data' else 2]):
            row=db.get(Fact,item['fact_id'])
            text=brief_fact(db,item,bn,bank_id)
            if row and row.metric=='crar' and row.value>=0:
                cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
                minimum=(Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer'])))*100
                number=spoken_percent(row.value*100,bn);limit=spoken_percent(minimum,bn,negative=True)
                if row.value*100>=minimum:
                    text=f'নিজস্ব মূলধন প্রায় {number}, লাগে {limit}, তাই ক্ষতি সামলাতে পারে' if bn else f'Its capital is about {number}, above the {limit} buffer minimum'
                else:text=f'নিজস্ব মূলধন প্রায় {number}, লাগে {limit}, তাই ঘাটতি আছে' if bn else f'Its capital is about {number}, below the {limit} buffer inclusive minimum'
            if row and row.metric=='crar' and row.value>=0 and not bn and len(name.split())>4:
                text=f'Its own capital exceeds the required {limit}' if row.value*100>=minimum else f'Its own capital falls below the required {limit}'
            if row and row.metric=='crar' and row.value<0:
                number=spoken_percent(row.value*100,bn,negative=True)
                cfg=json.loads(Path(__file__).with_name('rules').joinpath('thresholds.json').read_text())
                limit=spoken_percent((Decimal(str(cfg['crar_min']))+Decimal(str(cfg['crar_buffer'])))*100,bn,negative=True)
                text=f'লোকসানে নিজস্ব মূলধন শেষ হয়েছে, এখন মাইনাস {number}, প্রয়োজন {limit}' if bn else text
            rating=db.get(Rating,item['fact_id']) if not row else None
            if rating and rating.outlook in {'negative','developing'} and not (rating.valid_to and rating.valid_to<date.today()):
                text=('রেটিংয়ের পূর্বাভাস '+('নেতিবাচক' if rating.outlook=='negative' else 'অনিশ্চিত')+' রয়েছে') if bn else 'Its rating outlook is '+rating.outlook
            if index and reasons and db.get(Fact,reasons[0]['fact_id']) and db.get(Fact,reasons[0]['fact_id']).metric=='crar' and db.get(Fact,reasons[0]['fact_id']).value<0:continue
            if row and row.metric=='npl_ratio':
                number=rounded(row.value*100,bn)
                text=f'ঋণের ১০০ টাকায় প্রায় {number} টাকা ফেরত আসে না' if bn else f'About {number}% of lending has repayment problems' if len(name.split())>4 else f'About {number} per 100 taka lent has repayment problems'
            if row and row.basis.endswith('_calculated') and not text.startswith(('হিসাবে ','Calculated ')):
                text=('আমাদের হিসাবে '+text) if bn else 'Our calculation shows that '+text[:1].lower()+text[1:]
            if index==0:text=('কারণ, '+text if bn else 'That is because '+text[:1].lower()+text[1:])
            candidate=assembled([*bodies,text,*([protection] if protection else [])])
            if len(candidate.split())<=(45 if bn else 47):add(text,item,True)
        if protection and add(protection,ins,True) and bank_id not in insurance_banks:insurance_banks.append(bank_id)
    elif tool in {'bank_reasons','bank_figures','bank_history'}:
        for item in [f for f in fresh if not f['fact_id'].startswith('script:')]:
            if len(bodies)>=2:break
            add(brief_fact(db,item,bn,bank_id),item)
            if tool=='bank_history':break
        if not bodies:add(('বিস্তারিত কার্ডে আছে' if bn else 'Details are on the card') if fresh else ('এই অঙ্কগুলো আগেই বলেছি, বিস্তারিত কার্ডে আছে' if bn else 'These figures were already explained, exact values are on the card') if any(not f['fact_id'].startswith('script:') for f in facts) else ('এই তথ্য এখনো নেই' if bn else 'This information is unavailable'))
    elif tool=='insurance':
        add(brief_insurance(db,bank_id,bn),facts[0] if facts else None,True)

        if bank_id and bank_id not in insurance_banks:insurance_banks.append(bank_id)
    elif tool=='service_compare':
        text=brief_comparison(db,facts,bn)
        if text:
            if add(text):
                used.extend(item['fact_id'] for item in facts[:2]);entries[-1]=(text,[item['fact_id'] for item in facts[:2]])
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
    if tool=='bank_summary' and len(bodies)>1 and bodies[1].startswith(('কারণ, ','That is because ')):
        reason=bodies[1].replace('কারণ, ','কারণ ',1) if bn else bodies[1].replace('That is because ','because ',1)
        bodies[:2]=[bodies[0]+', '+reason]
        entries[:2]=[(bodies[0],entries[0][1]+entries[1][1])]
    speech=assembled(bodies)
    if (tool!='bank_summary' and len(speech.split())>50) or page:
        speech,page_ids,completed,more,page=page_narration(entries,question,bn,page)
        validate_spoken_answer(speech,language)
        return Narration(speech,page_ids,insurance_banks,completed,list(dict.fromkeys(used)),more,page)
    validate_spoken_answer(speech,language,first=tool=='bank_summary')
    return Narration(speech,list(dict.fromkeys(used)),insurance_banks,list(dict.fromkeys(used)),list(dict.fromkeys(used)))


# Compatibility for callers loaded before a normal service restart.
def fact_clause(db,item,bn,bank_id):
    return brief_fact(db,item,bn,bank_id)


def offer_clause(db,item,bn,comparison=False):
    return brief_offer(db,item,bn,comparison)


def insurance_clause(db,bank_id,bn,full=False):
    return brief_insurance(db,bank_id,bn,short=not full)
