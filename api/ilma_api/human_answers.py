"""Code-written answers from stored facts, in the wording approved on 31 Oct 2026."""
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
import re
from ilma_api.human_tokens import FactToken,number,rating_words,term
from ilma_api.rules.reasons import format_date

AGENCIES={'CRISL':'সিআরআইএসএল','ECRL':'ইসিআরএল','CRAB':'ক্র্যাব','NCR':'এনসিআর','ACRSL':'এসিআরএসএল','ACRL':'এসিআরএল'}
OUTLOOK={'stable':'স্থিতিশীল','positive':'ইতিবাচক','negative':'নেতিবাচক','developing':'উন্নয়নশীল'}
LOW_LOANS=.03
BALANCE=re.compile(r'আমার.{0,40}ব্যালেন্স|ব্যালেন্স.{0,20}আমার|\b(?:my|check)\b.{0,30}\bbalance\b',re.I)
PIN=re.compile(r'(?<![ঀ-৿])পিন(?![ঀ-৿])|\bpin\b|পাসওয়ার্ড|\bpassword\b|\botp\b',re.I)
ACCOUNT=re.compile(r'একাউন্ট নম্বর|অ্যাকাউন্ট নম্বর|হিসাব নম্বর|account number',re.I)
SPORTS=re.compile(r'ক্রিকেট|ফুটবল|খেলার? |ম্যাচ|\bcricket\b|\bfootball\b|\bmatch\b|\bsports?\b',re.I)

def clean(value):return format(Decimal(str(value)).normalize(),'f')
def rounded(value):return Decimal(str(value)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
def percent(value):return number((Decimal(str(value))*100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def crore(value):
    amount=abs(Decimal(str(value)))/10000000
    return f'{int(rounded(amount)):,}' if amount>=100 else format(amount.normalize(),'f')
def on(day,bn):
    day=date.fromisoformat(str(day)[:10])
    return format_date(day,True) if bn else f'{day.day} {day:%B %Y}'

def refusal(text,bn,named=False):
    """Account, PIN and off-topic questions end here. The words said are never repeated."""
    if PIN.search(text):
        return ('দুঃখিত, আমি হিসাবের ব্যালেন্স দেখতে পারি না। আপনার পিন কখনো কাউকে জানাবেন না, এখানেও না। ব্যালেন্স জানতে ব্যাংকের অ্যাপ বা শাখায় যোগাযোগ করুন। ব্যাংকের অবস্থা বা সুদের হার বলতে পারি।' if bn else 'Sorry, I cannot check your balance. Never share your PIN with anyone, including here. Please use your bank\'s app or visit a branch. I can tell you about bank conditions or rates.'),''
    if BALANCE.search(text) or ACCOUNT.search(text):
        return ('দুঃখিত, আমি আপনার হিসাবের ব্যালেন্স দেখতে পারি না। ব্যালেন্স জানতে আপনার ব্যাংকের অ্যাপ বা শাখায় যোগাযোগ করুন। এখানে হিসাব নম্বর দেবেন না। ব্যাংকের অবস্থা বা সুদের হার জানতে চাইলে বলতে পারি।' if bn else 'Sorry, I cannot see your account balance. Please use your bank\'s app or visit a branch, and do not share your account number here. I can tell you about bank conditions or rates.'),''
    if SPORTS.search(text) and not named:
        return ('দুঃখিত, আমি শুধু ব্যাংকের তথ্য নিয়ে সাহায্য করতে পারি, খেলার খবর দিতে পারি না।' if bn else 'Sorry, I can only help with bank information, not sports news.'),('কোনো ব্যাংকের অবস্থা বা সুদের হার জানতে চান?' if bn else "Would you like to hear about a bank's condition or rates?")
    return None

def figure(facts,bank,metric):
    return next((f for f in facts.values() if f.get('kind')=='figure' and f.get('institution_id')==bank and f.get('values',{}).get('metric')==metric),None)

def capital_clause(f,bn):
    v=f['values'];value=Decimal(str(v['value']))*100;low=number(v.get('minimum_percent',12.5))
    if value<0:return (f'মূলধনের অনুপাত ঋণাত্মক, মাইনাস {number(abs(value))}%, ন্যূনতম চাহিদা {low}%' if bn else f'its capital ratio was negative, minus {number(abs(value))}%, against a {low}% minimum')
    return (f'মূলধনের অনুপাত {number(value)}%, ন্যূনতম চাহিদা {low}%' if bn else f'its capital ratio is {number(value)}%, against a {low}% minimum')

def high_loans(f,bn):
    v=f['values'];x=percent(v['value']);share=rounded(Decimal(str(v['value']))*100);when=on(v['period_end'],bn)
    return (f'{when}-এর হিসাবে খেলাপি ঋণ {x}%, মানে প্রতি 100 টাকা ঋণের প্রায় {share} টাকা ফেরত আসছে না।' if bn else f'As of {when}, bad loans were {x}%.')

def overview_lines(name,whose,status,facts,bank,bn,intro=None,award=False,interim=None):
    """Status, capital and bad loans as plain stated figures, whichever opening the bank has."""
    capital,loans,profit=(figure(facts,bank,m) for m in ('crar','npl_ratio','net_profit'))
    ids=lambda *found:[f['fact_id'] for f in found if f]
    if status=='no_data':
        return [*(intro or []),((f"{'ব্যাংকটির ' if intro else whose}অবস্থা যাচাই করার মতো তথ্য আমাদের কাছে নেই। তাই ভালো বা খারাপ কিছুই বলছি না।" if bn else f"We have no audited information to assess {name}, so I am not calling it good or bad."),[])]
    if status=='high':
        lines=[((f'{whose}ঝুঁকি বেশি।' if bn else f'{name} is high risk.'),[next(f['fact_id'] for f in facts.values() if f.get('kind')=='status' and f.get('institution_id')==bank)])]
        if bn:
            if loans:lines.append((high_loans(loans,True),ids(loans)))
            if capital:lines.append((capital_clause(capital,True)+'।',ids(capital)))
        elif loans:
            text=high_loans(loans,False).rstrip('.')
            lines.append(((text+' and '+capital_clause(capital,False)+'.') if capital else text+'.',ids(loans,capital)))
        elif capital:lines.append(('Its '+capital_clause(capital,False)[4:]+'.',ids(capital)))
        if not bn and profit and profit['values']['value']<0:
            lines.append(((f"সে বছর নিট লোকসান প্রায় {crore(profit['values']['value'])} কোটি টাকা।" if bn else f"Its net loss that year was about Tk {crore(profit['values']['value'])} crore."),ids(profit)))
        return lines
    named=bool(intro)
    subject=('ব্যাংকটির ' if bn else 'It ') if named else (whose if bn else name+' ')
    status_id=[f['fact_id'] for f in facts.values() if f.get('kind')=='status' and f.get('institution_id')==bank]
    word={'strong':('অবস্থা ভালো','is in good condition'),'watch':('ক্ষেত্রে সতর্ক থাকুন, কিছু সূচকে দুর্বলতার লক্ষণ আছে','is on Watch, with warning signs in some indicators')}[status]
    if status=='strong' and capital:condition=f"{subject}{word[0]}, কারণ {capital_clause(capital,True)}।" if bn else f"{subject}{word[1]}: {capital_clause(capital,False)}."
    elif capital:condition=f"{subject}{word[0]}। {capital_clause(capital,True)}।" if bn else f"{subject}{word[1]}. {capital_clause(capital,False)[0].upper()+capital_clause(capital,False)[1:]}."
    else:condition=f'{subject}{word[0]}।' if bn else f'{subject}{word[1]}.'
    condition=(condition,status_id+ids(capital));loan=None
    if loans:
        x=percent(loans['values']['value']);year=loans['values']['period_end'][:4];small=loans['values']['value']<LOW_LOANS
        if award:loan=(f'ব্যাংকটির খেলাপি ঋণ {x}%, {year} সালের হিসাবে।' if bn else f'Its bad loans are {x}%, as of {year}.')
        elif small:loan=(f'আর {year} সালের হিসাবে খেলাপি ঋণ মাত্র {x}%।' if bn else f'Bad loans are only {x}%, as of {year}.')
        else:loan=(f'তবে {year} সালের হিসাবে খেলাপি ঋণ {x}%।' if bn else f'Bad loans are {x}%, as of {year}.')
        loan=(loan,ids(loans))
    # A dated part-year result carries the newer bad-loan figure, so the annual one is not said too.
    if interim:loan=None
    rows=[*(intro or []),*([loan] if award and loan else []),condition,*([interim] if interim else []),*([loan] if loan and not award else [])]
    return rows

def previous(db,bank,metric,year):
    from ilma_api.db import Fact
    return db.query(Fact).filter_by(institution_id=bank,metric=metric).filter(Fact.period_end<date(year,1,1)).order_by(Fact.period_end.desc()).first()

def loan_tokens(db,found,facts,bank,bn,status):
    v=found['values'];year=int(v['period_end'][:4]);x=percent(v['value']);ids=(found['fact_id'],)
    if status=='high':
        tokens={'asked:figure':FactToken(f"খেলাপি ঋণ {on(v['period_end'],True)}-এর হিসাবে {x}%, মানে প্রতি 100 টাকা ঋণের প্রায় {rounded(Decimal(str(v['value']))*100)} টাকা ফেরত আসছে না" if bn else f"Bad loans were {x}% as of {on(v['period_end'],False)}",ids,bank,'figure'),
         'asked:risk':FactToken('এই ব্যাংকের ঝুঁকি বেশি' if bn else 'This bank is high risk',(),bank,'gap')}
        capital=figure(facts,bank,'crar')
        if capital:
            text=capital_clause(capital,bn)
            tokens['asked:capital']=FactToken(text.replace('মূলধনের অনুপাত ','মূলধনের অনুপাতও ',1) if bn else text[0].upper()+text[1:],(capital['fact_id'],),bank,'figure')
        return tokens
    tokens={'asked:figure':FactToken(f'খেলাপি ঋণ {year} সালের হিসাবে মোট ঋণের {x}%' if bn else f'Bad loans were {x}% of total lending in {year}',ids,bank,'figure')}
    old=previous(db,bank,'npl_ratio',year)
    if old is not None and old.period_end.year==year-1:
        down=old.value>Decimal(str(v['value']))
        tokens['asked:previous']=FactToken(f"{year-1} সালে এটি ছিল {percent(old.value)}%, তাই হার {'কমেছে' if down else 'বেড়েছে'}" if bn else f"In {year-1} they were {percent(old.value)}%, so the rate has {'fallen' if down else 'risen'}",(old.fact_id,),bank,'figure')
        facts[old.fact_id]=dict(fact_id=old.fact_id,institution_id=bank,kind='figure_previous',text_bn='',text_en='',values={},source=dict(source_url=old.source.url,source_title=old.source.title,quote=old.quote))
    return tokens

def profit_tokens(db,found,facts,bank,bn):
    v=found['values'];value=Decimal(str(v['value']));year=int(v['period_end'][:4]);loss=value<0
    head=f"নিট {'লোকসান' if loss else 'মুনাফা'} {year} সালে প্রায় {crore(value)} কোটি টাকা" if bn else f"Net {'loss' if loss else 'profit'} was about Tk {crore(value)} crore in {year}"
    tokens={'asked:figure':FactToken(head,(found['fact_id'],),bank,'figure')}
    old=previous(db,bank,'net_profit',year)
    if old is None or old.period_end.year!=year-1 or old.value<=0 or loss:return tokens
    change=(value/Decimal(str(old.value))-1)*100;up=change>=0;size=abs(change)
    word=(f'প্রায় {rounded(size)}%' if size>=50 else 'কিছুটা' if size<10 else 'বেশ') if bn else (f'about {rounded(size)}%' if size>=50 else 'slightly' if size<10 else 'well')
    if not bn:
        tokens['asked:figure']=FactToken(f"{head}, {'up' if up else 'down'} {word} from about Tk {crore(old.value)} crore in {year-1}",(found['fact_id'],old.fact_id),bank,'figure')
    else:tokens['asked:change']=FactToken(f"{year-1} সালে এটি ছিল প্রায় {crore(old.value)} কোটি টাকা, তাই মুনাফা {word} {'বেড়েছে' if up else 'কমেছে'}",(old.fact_id,),bank,'figure')
    facts[old.fact_id]=dict(fact_id=old.fact_id,institution_id=bank,kind='figure_previous',text_bn='',text_en='',values={},source=dict(source_url=old.source.url,source_title=old.source.title,quote=old.quote))
    return tokens

def rating_tokens(found,facts,bank,bn,status):
    v=found['values'];grade=v['grade'];outlook=v.get('outlook');agency=v['agency']
    head=f'ক্রেডিট রেটিং {rating_words(grade)}'+(f', পূর্বাভাস {OUTLOOK[outlook]}' if outlook in OUTLOOK else '') if bn else f'Credit rating is {grade}'+(f' with a {outlook} outlook' if outlook else '')+f" from {agency} on {on(v['rated_on'],False)}"
    tokens={'asked:figure':FactToken(head,(found['fact_id'],),bank,'figure')}
    if bn:tokens['asked:by']=FactToken(f"রেটিং দিয়েছে {AGENCIES.get(agency,agency)}, {on(v['rated_on'],True)} তারিখে",(found['fact_id'],),bank,'figure')
    capital=figure(facts,bank,'crar')
    if status=='high' and capital:tokens['asked:risk']=FactToken(('তবে এই ব্যাংকের ঝুঁকি বেশি, '+capital_clause(capital,True)) if bn else 'But this bank is high risk: '+capital_clause(capital,False),(capital['fact_id'],),bank,'figure')
    else:tokens['asked:meaning']=FactToken('রেটিং ব্যাংকের ঋণ পরিশোধের সক্ষমতা নিয়ে মতামত, আমানতের নিশ্চয়তা নয়' if bn else 'A rating is an opinion on repaying debts, not a deposit guarantee',(),bank,'gap')
    return tokens

METRIC_GAP={'npl_ratio':('খেলাপি ঋণের হার','bad-loan figure'),'crar':('মূলধনের অনুপাত','capital ratio'),'net_profit':('নিট মুনাফার হিসাব','net profit figure'),'rating':('রেটিং','credit rating')}
def metric_gap(metric,bank,bn):
    label=METRIC_GAP.get(metric,('এই তথ্য','figure'))
    return {'asked:figure':FactToken(f'{label[0]} আমাদের কাছে নেই' if bn else f'{label[1]} is not in our collection',(),bank,'figure'),
     'asked:guess':FactToken('আমরা অনুমান করে কিছু বলি না' if bn else 'We do not guess',(),bank,'gap')}

PLAIN={'v62-PRIMEBANK_EMBEZZLE_2014':('ইসলামী ব্যাংকিং শাখায় পাসওয়ার্ড অপব্যবহার করে ভুয়া ঋণ তৈরির অভিযোগ ওঠে','password misuse and fake loans at an Islamic banking branch'),
 'v62-CITYBANK_CYBER_2016':('একটি এটিএম বুথে স্কিমিং ডিভাইস বসিয়ে জালিয়াতির ঘটনা ঘটে','a skimming device fitted at an ATM booth'),
 'v62-NBL_AUDIT_2025':('২০২৬ সালের জুনে নিরীক্ষক বিপুল প্রভিশন ঘাটতির কথা জানান','in June 2026 the auditor reported a large provision shortfall'),
 'v62-NBL_AUDIT_2024':('২০২৫ সালে নিরীক্ষক শ্রেণিকৃত ঋণে প্রভিশন ঘাটতির কথা জানান','in 2025 the auditor reported a provision shortfall on classified loans'),
 'v62-NBL_BOARD_2024':('২০২৪ সালে বাংলাদেশ ব্যাংক পরিচালনা পর্ষদ ভেঙে দেয়','in 2024 Bangladesh Bank dissolved the board'),
 'v62-NBL_LIQUIDITY_2026':('২০২৬ সালের অক্টোবরে জরুরি তারল্য সহায়তার খবর আসে','in October 2026 emergency liquidity support was reported'),
 'v62-NBL_PENALTY_2022':('২০২২ সালে ক্রেডিট কার্ডের ঋণ তথ্য গোপনের জন্য জরিমানা হয়','in 2022 it was fined over undisclosed credit card loan data')}

def history_lines(name,whose,items,bn):
    """Newest report of each kind, in plain words where they exist, else the stored headline."""
    items=sorted(items,key=lambda f:f['values']['first_reported_on'],reverse=True);seen=set();picked=[]
    for f in items:
        kind=f['fact_id'].rsplit('_',1)[0]
        if kind not in seen:seen.add(kind);picked.append(f)
    items=picked[:3]
    ids=[f['fact_id'] for f in items];plain=lambda f:PLAIN.get(f['fact_id'],(None,None))[0 if bn else 1]
    title=lambda f:plain(f) or f['text_bn' if bn else 'text_en'].rstrip('।.')
    year=lambda f:f['values']['event_date'][:4]
    unconfirmed=sum(not f['values'].get('official') for f in items)
    if len(items)==1:
        f=items[0]
        lines=[(f'{name} নিয়ে {year(f)} সালের একটি খবর আছে। {title(f)}।' if bn else f'{name} has one news report from {year(f)}, about {title(f)}.',ids)]
        if unconfirmed:lines.append(('খবরটি সরকারিভাবে নিশ্চিত নয়।' if bn else 'The report is not officially confirmed.',[]))
        return lines
    body=', '.join(title(f) if plain(f) else (f'{year(f)} সালে {title(f)}' if bn else f'in {year(f)}, {title(f)}') for f in items)
    lines=[(f'{whose}একাধিক ঘটনা আছে। {body}।' if bn else f'{name} has several reports: {body}.',ids)]
    if unconfirmed:lines.append(('এর কিছু খবর সরকারিভাবে নিশ্চিত নয়।' if bn else 'Some of these reports are not officially confirmed.',[]))
    return lines

def months_of(v):
    if v.get('tenor_options'):return list(v['tenor_options'])
    lo,hi=v.get('tenor_min_months'),v.get('tenor_max_months')
    return list(range(lo,hi+1)) if lo and hi else [lo] if lo else []

def spoken_months(m,bn):
    return (f'{m//12} বছর' if bn else f"{m//12} year{'s' if m>12 else ''}") if m%12==0 else (f'{m} মাস' if bn else f"{m} month{'s' if m>1 else ''}")

def rate_list(rows,bn):
    """"1, 2 or 3 years" for equal neighbouring terms, keeping ranges as published."""
    groups=[]
    for f in rows:
        v=f['values'];rate=number(v['rate']);options=v.get('tenor_options') or [];single=options or ([v.get('selected_tenor')] if v.get('selected_tenor') and v.get('tenor_min_months')==v.get('tenor_max_months') else [])
        unit=bool(single) and all(m%12==0 for m in single)
        if single and groups and groups[-1]['rate']==rate and groups[-1]['unit']==unit and groups[-1]['months']:groups[-1]['months']+=[m for m in single if m not in groups[-1]['months']]
        else:groups.append(dict(rate=rate,unit=unit,months=list(single),text=term(v,bn)))
    def when(g):
        if not g['months']:return g['text']
        m=g['months']
        if len(m)==1:return spoken_months(m[0],bn)
        size=12 if g['unit'] else 1
        return ', '.join(str(x//size) for x in m[:-1])+(' বা ' if bn else ' or ')+spoken_months(m[-1],bn)
    if bn:return ', '.join(f"{when(g)}ে {g['rate']}%" for g in groups)
    parts=[f"{g['rate']}% for {when(g)}" for g in groups]
    return parts[0] if len(parts)==1 else ', '.join(parts[:-1])+', and '+parts[-1]

SLAB=[(r'^<\s*([\d.]+)\s*(Crore|Cr|Lac)\b',lambda m,u:(f'{m[1]} {u[0]} টাকার কম জমায়',f'under {m[1]} {u[1]}')),
 (r'^([\d.]+)\s*(?:Crore|Cr|Lac)\s*-\s*<\s*([\d.]+)\s*(Crore|Cr|Lac)\b',lambda m,u:(f'{m[1]} {("লাখ" if "Lac" in m[0].split("-")[0] else "কোটি")} থেকে {m[2]} {u[0]} টাকার কম জমায়',f'{m[1]} {("lakh" if "Lac" in m[0].split("-")[0] else "crore")} to under {m[2]} {u[1]}')),
 (r'^([\d.]+)\s*(Crore|Cr|Lac)\s*(?:&|and)\s*above',lambda m,u:(f'{m[1]} {u[0]} বা তার বেশি জমায়',f'{m[1]} {u[1]} or more'))]
def slab(condition,bn):
    text=(condition or '').split(';')[-1].strip()
    for pattern,build in SLAB:
        m=re.match(pattern,text,re.I)
        if m:
            word=m.groups()[-1 if pattern!=SLAB[2][0] else 1].casefold()
            return build(m,('লাখ','lakh') if word.startswith('lac') else ('কোটি','crore'))[0 if bn else 1]
    return None

GENERAL=re.compile(r'regular|general|^savings|^prime savings|savings bank|high earning',re.I)
def savings_lines(rows,whose,bn,label,general_only=False):
    """Each account once: a slab pair reads as a range or its slabs, equal rates share a sentence."""
    grouped={}
    for f in rows:grouped.setdefault(f['values']['product'],[]).append(f)
    order=sorted(grouped,key=lambda p:not GENERAL.search(p));out=[];same={}
    if general_only and GENERAL.search(order[0]):order=order[:1]
    for product in order:
        items=grouped[product];values=sorted({f['values']['rate'] for f in items});ids=[f['fact_id'] for f in items]
        shown=label(items[0]['values'])
        if not bn and re.search(r'regular|general',product,re.I):shown='regular savings'
        if len(values)==1:
            if out and GENERAL.search(order[0]) and product!=order[0]:same.setdefault(values[0],[]).append((shown,ids));continue
            out.append(((f'{shown}ে সুদ {number(values[0])}%' if bn else f'{shown} pays {number(values[0])}%'),ids));continue
        slabs=[(slab(f['source'].get('condition'),bn),f['values']['rate']) for f in sorted(items,key=lambda f:f['values']['rate'])]
        wording=[]
        if all(s for s,_ in slabs):wording=[f'{s} {number(r)}%' if bn else (f'{number(r)}% from {s} taka' if ' to ' in s else f'{number(r)}% at {s}') for s,r in slabs]
        # Slabs that meet ("under 1 crore", "1 crore or more") already give the whole range.
        joined=len(slabs)==2 and any(re.match(r'\s*<',(f['source'].get('condition') or '').split(';')[-1]) for f in items)
        if joined and bn and wording:
            first=wording[0].replace(' জমায় ',' জমায় সুদ ',1);text=f"{shown}ে {first}, আর {wording[1]}"
        elif bn:text=f"{shown}ে সুদ জমার পরিমাণভেদে {number(values[0])}% থেকে {number(values[-1])}%"+('। '+', '.join(wording) if wording else '')
        else:text=f"{shown} rate runs from {number(values[0])}% to {number(values[-1])}% by balance"+(': '+', and '.join(wording) if wording else '')
        out.append((text,ids))
    for rate,items in same.items():
        names=[n for n,_ in items];ids=[i for _,x in items for i in x]
        joined=(', '.join(names[:-1])+' আর '+names[-1]) if bn and len(names)>1 else ', '.join(names)
        out.append(((f'{joined}ে {number(rate)}%' if bn else f'{joined} pay {number(rate)}%'),ids))
    sentences=[]
    for index,(text,ids) in enumerate(out):sentences.append(((whose+text if not index else text)+('।' if bn else '.'),ids))
    floor={re.search(r'Tk\.?\s*([\d,]+)\s*&\s*above',f['source'].get('condition') or '') and re.search(r'Tk\.?\s*([\d,]+)',f['source']['condition'])[1] for f in rows}
    if len(rows)>1 and len(floor)==1 and None not in floor:
        amount=next(iter(floor)).replace(',','');shown=f'{int(amount)//1000} হাজার' if bn and int(amount)%1000==0 else f'{int(amount):,}'
        sentences.append(((f'দুটিতেই {shown} টাকা বা তার বেশি জমা থাকলে এই হার।' if bn else f'Both need a balance of Tk {shown} or more.'),[rows[0]['fact_id']]))
    return sentences

def scheme_name(v,bn):
    """A product as people say it: the bank's own prefix and the code letters come off."""
    from ilma_api.human_tokens import product
    name=product(v,bn)
    if bn:return name
    return re.sub(r'\s*\(\w+\)$','',re.sub(r'^(?:NCC|MTB|EBL|Prime)\s+','',name)).replace('Deposit Scheme','Scheme')

def month_rates(rows):
    rates={}
    for f in sorted(rows,key=lambda f:bool(re.search(r'women|child|senior|premium',f['values'].get('product',''),re.I))):
        for m in months_of(f['values']):rates.setdefault(m,(f['values']['rate'],f['fact_id']))
    return rates

def compare_tokens(first,second,label,whose,status,bn):
    """Two named banks: their shared terms side by side, or each bank's own products."""
    (a,rows_a),(b,rows_b)=first,second
    rate_a,rate_b=month_rates(rows_a),month_rates(rows_b);shared=set(rate_a)&set(rate_b);tokens={}
    terms=[m for m in sorted(shared,key=lambda m:(m!=12,m)) if m==12 or m>=3][:2]
    word=label[0 if bn else 1]
    for index,m in enumerate(terms):
        when=spoken_months(m,bn);x,y=number(rate_a[m][0]),number(rate_b[m][0]);ids=(rate_a[m][1],rate_b[m][1])
        short=lambda n:n.removesuffix(' ব্যাংক')
        if bn:text=f'{a} {when}ের {word}ে {x}% দেয়, {b} দেয় {y}%' if not index else f'{when}ে {short(a)} {x}%, {short(b)} {y}%'
        else:text=f'For a {when.replace(" years","-year").replace(" year","-year").replace(" months","-month").replace(" month","-month")} {word}, {a} pays {x}% and {b} pays {y}%' if not index else f'For {when}, {a} pays {x}% and {b} pays {y}%'
        tokens[f'cmp:{index}']=FactToken(text,ids,None,'row')
    if not terms:
        for index,(name,rows) in enumerate((first,second)):
            ordered=sorted(rows,key=lambda f:-f['values']['rate'])[:3];ids=tuple(f['fact_id'] for f in ordered)
            if len(ordered)==2 and len({(f['values']['rate'],term(f['values'],bn)) for f in ordered})==1:
                v=ordered[0]['values']
                tokens[f'cmp:{index}']=FactToken(f"{whose(name)}দুটি {word}ে {term(v,True)}ে {number(v['rate'])}%" if bn else f"{whose(name)}two {word} schemes pay {number(v['rate'])}% for {term(v,False)}",ids,None,'row');continue
            parts=[f"{scheme_name(f['values'],True)}ে {term(f['values'],True)}ে সুদ {number(f['values']['rate'])}%" if bn else f"{scheme_name(f['values'],False)} pays {number(f['values']['rate'])}% for {term(f['values'],False)}" for f in ordered]
            if not bn:parts=[whose(name)+parts[0],*['its '+p for p in parts[1:]]]
            tokens[f'cmp:{index}']=FactToken((whose(name)+', '.join(parts)) if bn else ', and '.join(parts),ids,None,'row')
    if terms:
        for name,rows in (first,second):
            used=[f for f in rows if f['fact_id'] in {r[m][1] for r in (rate_a,rate_b) for m in terms if m in r}]
            floors={(re.search(r'below (\d+) Lac',f['source'].get('condition') or '') or [None,None])[1] for f in used}
            if len(floors)==1 and None not in floors:
                limit=next(iter(floors));tokens['cmp:limit']=FactToken(f'{whose(name)}হার {limit} লাখ টাকার কম জমার জন্য' if bn else f"{name}'s rates are for deposits under {limit} lakh taka",(),None,'gap')
    notes=[(n,s) for n,s in zip((a,b),status) if s in {'watch','high'}]
    for index,(name,code) in enumerate(notes):
        tokens[f'cmp:n{index}']=FactToken(({'watch':f'তবে {name}ে কিছু সতর্কতার লক্ষণ আছে','high':f'তবে {whose(name)}ঝুঁকি বেশি'}[code]) if bn else {'watch':f'{name} has some warning signs','high':f'{name} is high risk'}[code],(),None,'gap')
    return tokens


MORE_ABOUT_BANK=('আপনার কি আরও জানার আছে এই ব্যাংক সম্পর্কে?','আপনি কি এই ব্যাংক সম্পর্কে আরও কিছু জানতে চাচ্ছেন?')
ASK_ANY_BANK='আপনার কি কোন নির্দিষ্ট ব্যাংক এর সম্পর্কে জানার আছে?'
def closing(intent,text,status,bn,award=False,shared_terms=False):
    """The approved closing question for a turn, or None to keep the standard one."""
    if not bn:
        if intent=='explain_term':return 'Would you like to hear other bank services or another bank?'
        return None
    if intent in {'bank_overview','bank_condition'}:
        if 'সম্পর্কে' in text or status=='high':return MORE_ABOUT_BANK[0]
        if award:return MORE_ABOUT_BANK[1]
        return None
    if intent=='explain_term':return ASK_ANY_BANK
    if intent=='bank_awards' and 'কী কী' in text:return MORE_ABOUT_BANK[0]
    if intent=='compare' and shared_terms:return 'আপনি ব্যাংকের সেবাগুলো শুনবেন, না অন্য ব্যাংক দেখবেন?'
    return None
