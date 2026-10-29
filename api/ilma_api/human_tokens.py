"""Code-owned factual clauses and exact card values; models select opaque tokens."""
from dataclasses import dataclass
from decimal import Decimal
import re
from ilma_api.voice_numbers import pronounce

TOKEN=re.compile(r'⟨([^⟨⟩]+)⟩')
PROTECTION_WORDS=re.compile(r'বন্ধ হলেও|সুরক্ষিত|ফেরত পাওয়ার|আমানত সুরক্ষা|deposit protection|deposit insurance|if the bank closes|eligible deposits',re.I)
BANNED=re.compile(r'ঝুঁকিভিত্তিক|বাফার|মধ্যমান|গড়মান|সদস্য ব্যাংক|যোগ্য আমানত|অবস্থার তথ্য হলো|প্রকাশিত অঙ্ক|pct_year|founded_year|\bPLC\b|পিএলসি',re.I)
ADVICE=re.compile(r'রাখুন|রাখবেন না|তুলে নিন|বিনিয়োগ করুন|\bshould\b|\brecommend\b|safe place',re.I)
CONNECTORS=set('আর এছাড়া পাশাপাশি তবে ব্যাংকটির ব্যাংকের এর ের ে এখানে এদিকে কারণ তথ্য অনুযায়ী এবং এই and but also moreover its the this bank for here because at'.split())
PRODUCTS={'fdr':('এফডিআর','FDR'),'dps':('ডিপিএস','DPS'),'savings':('সঞ্চয়ী হিসাব','savings account'),'card':('কার্ড','card'),'home_loan':('গৃহঋণ','home loan'),'auto_loan':('গাড়ির ঋণ','car loan'),'personal_loan':('ব্যক্তিগত ঋণ','personal loan')}
FIELDS={'founded_year':('প্রতিষ্ঠা','Established'),'branches':('শাখা','Branches'),'sub_branches':('উপশাখা','Sub-branches'),'atms':('এটিএম','ATMs'),'agent_outlets':('এজেন্ট আউটলেট','Agent outlets'),'customers':('গ্রাহক','Customers'),'known_for':('পরিচিতি','Known for')}

def number(value):return format(Decimal(str(value)).normalize(),'f')
def unit_label(unit,bn):
    return {'pct_year':('%','%'),'bdt':(' টাকা',' taka'),'usd':(' মার্কিন ডলার',' US dollars'),'count':('টি',' items'),'days':(' দিন',' days'),'months':(' মাস',' months')}.get(unit,('',''))[0 if bn else 1]
def term(v,bn,selected=None):
    def one(m):return f'{m//12} '+('বছর' if bn else 'year' if m==12 else 'years') if m%12==0 else f'{m} '+('মাস' if bn else 'month' if m==1 else 'months')
    if selected:return one(selected)
    if v.get('tenor_options'):return (' বা ' if bn else ' or ').join(one(m) for m in v['tenor_options'])
    lo,hi=v.get('tenor_min_months'),v.get('tenor_max_months')
    return one(lo)+((' থেকে ' if bn else ' to ')+one(hi) if hi and hi!=lo else '') if lo else ''

def product(v,bn):
    name=re.sub(r'\s+PLC\.?','',v.get('product',''),flags=re.I)
    if not bn:return name
    for pattern,label in [('Women Confidence','নারীদের কনফিডেন্স ডিপিএস'),('Child Future','শিশুদের ফিউচার প্ল্যান ডিপিএস'),('Confidence','কনফিডেন্স ডিপিএস'),('Kotipoti','কোটিপতি ডিপিএস'),('Lakhopati','লাখপতি স্কিম'),('Monthly Savings Scheme','মাসিক সঞ্চয় স্কিম'),('Extra Value','এক্সট্রা ভ্যালু এফডিআর')]:
        if pattern.casefold() in name.casefold():return label
    if v.get('product_type')=='card':return pronounce(' '.join(x for x in (v.get('network'),v.get('tier'),'কার্ড') if x),'bn')
    return PRODUCTS.get(v.get('product_type'),('এই সেবা',name))[0]

@dataclass(frozen=True)
class FactToken:
    text:str
    fact_ids:tuple=()
    bank_id:int|None=None
    kind:str='fact'


def material(f):
    v=f.get('values',{});metric=v.get('metric')
    if f.get('kind')!='peer':return False
    if v.get('rank_high')==1 or v.get('rank_low')==1:return True
    if metric=='rating':return v.get('grade')!=v.get('median_grade') and bool(v.get('worse'))
    threshold={'crar':2,'npl_ratio':1,'fdr_12_rate':.5,'dps_12_rate':.5,'profit_change':20}.get(metric)
    return threshold is not None and abs(v['value']-v['median'])>=threshold


def card_text(f,language):
    bn=language=='bn';v=f.get('values',{});kind=f.get('kind')
    if kind=='profile':
        label=FIELDS.get(v['field'],('তথ্য','Information'))[0 if bn else 1]
        from datetime import date
        from ilma_api.rules.reasons import format_date
        when=format_date(date.fromisoformat(v['as_of']),bn)
        return f"{label}: {v['value']}"+(f" · {when}" if v['field']!='founded_year' else '')
    if kind=='service':
        from datetime import date
        from ilma_api.rules.reasons import format_date
        unit='% বার্ষিক' if bn and v['unit']=='pct_year' else '% per year' if v['unit']=='pct_year' else unit_label(v['unit'],bn)
        return product(v,bn)+': '+number(v['rate'])+unit+(' · '+term(v,bn) if term(v,bn) else '')+' · '+format_date(date.fromisoformat(v['doc_date']),bn)
    return f.get('text_bn' if bn else 'text_en','')


def rating_words(grade):
    """Bangla spoken form of a rating grade: "AA+" -> "ডাবল এ প্লাস"."""
    found=re.fullmatch(r'([A-D])(\1{0,2})([+-]?)',grade or '')
    if not found:return grade
    count=1+len(found[2]);letter={'A':'এ','B':'বি','C':'সি','D':'ডি'}[found[1]]
    return ' '.join(x for x in (('','ডাবল','ট্রিপল')[count-1],letter,{'+':'প্লাস','-':'মাইনাস','':''}[found[3]]) if x)


GENERIC=re.compile(r'\d|\bmonths?\b|\byears?\b|^fixed deposit|^retail|^term deposit|^general',re.I)
def english_offer(v,when,label,amount):
    """Plain English: "pays 7% on a 1-year fixed deposit"; raw sheet titles are not read out."""
    name=product(v,False);kind={'fdr':'fixed deposit','dps':'DPS'}.get(v.get('product_type'))
    single=re.fullmatch(r'(\d+) (year|month)s?',when or '')
    if not kind:return f'{name} '+(f'over {when} ' if when else '')+f'has {label} of {amount}'
    verb='pays' if label=='interest' else 'pays a provisional profit of'
    if kind and (not name or GENERIC.search(name)):
        if single:return f'{verb} {amount} on a {single[1]}-{single[2]} {kind}'
        return f'{verb} {amount} on a {kind}'+(f' for {when}' if when else '')
    return f'{verb} {amount} on its {name}'+(f' for {when}' if when else '')


def fact_clause(f,language,meaning=False):
    bn=language=='bn';v=f.get('values',{});metric=v.get('metric');kind=f.get('kind')
    if kind=='term':
        name=f['fact_id'].casefold()
        if 'crar' in name:return 'ব্যাংক কতটা ঝুঁকি নিচ্ছে, তার তুলনায় নিজের টাকা কতটা আছে, সেই হিসাব' if bn else 'how much of its own money the bank has relative to the risks it takes'
        if 'buffer' in name:return 'ন্যূনতম চাহিদার ওপরে বাড়তি মূলধন, যা ক্ষতি সামলানোর জায়গা বাড়ায়' if bn else 'extra capital above the minimum, adding capacity to absorb losses'
    if kind=='status':
        code=f.get('status',{}).get('code') or v.get('status','no_data')
        return {'strong':('অবস্থা ভালো, বর্তমান সূচকগুলো ইতিবাচক','is in good condition based on the current indicators'),
          'watch':('কিছু বিষয়ে সতর্কতা দরকার, সূচকে দুর্বলতার লক্ষণ আছে','has warning signs in some indicators'),
          'high':('ঝুঁকির লক্ষণ বেশি, আর্থিক সূচকে বড় দুর্বলতা আছে','shows substantial weaknesses in its financial indicators'),
          'no_data':('অবস্থা যাচাই করার মতো যথেষ্ট তথ্য এখনো নেই','does not yet have enough information to assess its condition')}.get(code,('তথ্য কম','has insufficient information'))[0 if bn else 1]
    if metric=='crar' and meaning:
        value=Decimal(str(v['value']))*100;minimum=Decimal(str(v.get('minimum_percent',12.5)))
        if value<0:return 'নিজের মূলধন ঋণাত্মক, যা বড় দুর্বলতার লক্ষণ' if bn else 'its own capital is negative, a significant weakness'
        if value>=minimum:return 'নিজের মূলধন ন্যূনতম চাহিদার ওপরে আছে, তাই ক্ষতি সামলানোর বাড়তি জায়গা আছে' if bn else 'its own capital exceeds the minimum, giving it extra capacity to absorb losses'
        return 'নিজের মূলধন ন্যূনতম চাহিদার নিচে আছে, যা চিন্তার বিষয়' if bn else 'its own capital is below the minimum, which is concerning'
    if metric=='npl_ratio' and meaning:
        if v['value']<=.03:return 'দেওয়া ঋণের খুব সামান্য অংশ নিয়ে পরিশোধের সমস্যা হচ্ছে, যা ভালো লক্ষণ' if bn else 'only a small share of lending has repayment problems, a positive sign'
        return 'ঋণের একটি অংশ ফেরত পেতে সমস্যা হচ্ছে, যা নজরে রাখা দরকার' if bn else 'repayment problems affect part of its lending and deserve attention'
    if kind=='figure' and metric=='crar':return f'মূলধনের অনুপাত {number(Decimal(str(v["value"]))*100)}%, ন্যূনতম চাহিদা {number(v.get("minimum_percent",12.5))}%' if bn else f'The capital ratio is {number(Decimal(str(v["value"]))*100)}%, against a minimum of {number(v.get("minimum_percent",12.5))}%'
    if kind=='figure' and metric=='npl_ratio':return f'মোট ঋণের {number(Decimal(str(v["value"]))*100)}% খেলাপি হয়েছে' if bn else f'{number(Decimal(str(v["value"]))*100)}% of total lending has repayment problems'
    if kind=='figure' and metric=='net_profit':
        value=Decimal(str(v['value']));amount=number(abs(value)/10000000)
        return f'নিট '+('লোকসান' if value<0 else 'মুনাফা')+f' {amount} কোটি টাকা' if bn else f'Net '+('loss' if value<0 else 'profit')+f' is {amount} crore taka'
    if kind=='figure' and metric=='profit_change':
        value=Decimal(str(v['value']));amount=number(abs(value))
        return f'আগের বছরের তুলনায় নিট মুনাফা {amount}% '+('কমেছে' if value<0 else 'বেড়েছে') if bn else f'Net profit '+('fell' if value<0 else 'rose')+f' {amount}% from the previous year'
    if kind=='history':
        title=f.get('text_en','')+' '+f.get('text_bn','')
        category='এটিএম কার্ড নিয়ে একটি ঘটনা' if re.search(r'atm|card|এটিএম|কার্ড',title,re.I) else 'গ্রাহকের টাকা নিয়ে একটি অনিয়মের ঘটনা' if re.search(r'customer|deposit|গ্রাহক|আমানত',title,re.I) else 'ব্যাংকটির কার্যক্রম নিয়ে একটি ঘটনা'
        english='an incident involving ATM cards' if 'এটিএম' in category else 'an irregularity involving customer funds' if 'গ্রাহক' in category else 'an incident involving the bank’s operations'
        year=v['event_date'][:4];caution='' if v.get('official') else ', খবরের তথ্য সরকারিভাবে নিশ্চিত নয়' if bn else '; the news report is not officially confirmed'
        return f'{year} সালে {category}র খবর আসে'+caution if bn else f'In {year}, reports described {english}'+caution
    if kind=='insurance' and v.get('limit'):
        amount=number(Decimal(str(v['limit']))/100000)+' লাখ' if bn and v['limit']%100000==0 else number(v['limit'])
        return f'একই ব্যাংকের সব হিসাব মিলিয়ে জনপ্রতি {amount} টাকার সীমা আছে, কিছু শর্তের ওপর এটি নির্ভর করে, সেগুলো কার্ডে আছে' if bn else f'The limit is {amount} taka per depositor per bank, combining accounts; conditions apply and are explained on the card'
    if kind=='profile':
        if v['field']=='founded_year':return f"প্রতিষ্ঠিত হয় {v['value']} সালে" if bn else f"was established in {v['value']}"
        from datetime import date
        from ilma_api.rules.reasons import format_date
        when=format_date(date.fromisoformat(v['as_of']),bn)
        label=FIELDS.get(v['field'],('তথ্য','information'))[0 if bn else 1]
        return f'{when} অনুযায়ী {label} ছিল {v["value"]}' if bn else f'reported {v["value"]} {label.lower()} as of {when}'
    if kind=='service':
        if not unit_label(v['unit'],bn):return 'এই সেবার বিস্তারিত শর্ত কার্ডে আছে' if bn else 'The detailed terms of this service are on the card'
        label=('বার্ষিক ফি' if v.get('attribute')=='annual_fee' else 'আনুমানিক মুনাফা' if v.get('basis')=='islamic' else 'সুদ') if bn else ('annual fee' if v.get('attribute')=='annual_fee' else 'provisional profit' if v.get('basis')=='islamic' else 'interest')
        unit=unit_label(v['unit'],bn)
        when=term(v,bn,v.get('selected_tenor') if v.get('asked_tenor') else None)
        text=f'{product(v,bn)}ে '+(when+' মেয়াদে ' if when else '')+f'{label} {number(v["rate"])}{unit}' if bn else english_offer(v,when,label,number(v['rate'])+unit)
        if v.get('nearest'):text+=', চাওয়া মেয়াদের তথ্য নেই, এটি আলাদা মেয়াদের' if bn else '; the requested term is unavailable, this is a different term'
        if v.get('dated'):
            from datetime import date
            from ilma_api.rules.reasons import format_date
            when=format_date(date.fromisoformat(v['doc_date']),bn)
            text+=', হারতালিকা '+when if bn else ', schedule dated '+when
        return text
    if kind=='peer' and metric=='rating' and material(f):
        median=re.search(r'মধ্যমান\s+(\S+)',f.get('text_bn',''))
        grade=str(v.get('grade') or '')
        good=bool(re.fullmatch(r'AAA|AA[+-]?',grade))
        if bn:
            text=f'রেটিং সংস্থা ব্যাংকটিকে {rating_words(grade)} দিয়েছে'+(', যা ভালো রেটিং' if good else '')
            return text+(f'; আমাদের তালিকার ভালো ব্যাংকগুলোর সাধারণ রেটিং {rating_words(median[1])}' if median else '')
        text=f'its credit rating is {grade}'+(', a good rating' if good else '')
        return text+(f'; the typical rating among strong banks in our list is {median[1]}' if median else '')
    if kind=='peer' and material(f):
        direction=v.get('value',0)>v.get('median',0)
        if metric=='npl_ratio':return ('অন্য তুলনাযোগ্য ভালো ব্যাংকের চেয়ে খেলাপি ঋণ বেশি, যা চিন্তার বিষয়' if direction else 'অন্য তুলনাযোগ্য ভালো ব্যাংকের চেয়ে খেলাপি ঋণ কম, যা ভালো লক্ষণ') if bn else ('problem loans are higher than comparable peers, a concern' if direction else 'problem loans are lower than comparable peers, a positive sign')
        if metric=='crar':return ('তুলনাযোগ্য ব্যাংকের চেয়ে নিজের মূলধন বেশি' if direction else 'তুলনাযোগ্য ব্যাংকের চেয়ে নিজের মূলধন কম') if bn else ('its own capital ratio is higher than comparable peers' if direction else 'its own capital ratio is lower than comparable peers')
    if kind=='coverage':return 'এই তথ্যের নির্ভরযোগ্য উদ্ধৃতি এখনো আমাদের কাছে নেই' if bn else 'we do not yet have a reliable quotation for that detail'
    return f.get('text_bn' if bn else 'text_en','').replace('মধ্যমান','তুলনাযোগ্য ব্যাংকের সাধারণ মান')


def build_registry(packs,comparison,language,insurance=False):
    bn=language=='bn';registry={};facts={f['fact_id']:f for p in packs for f in p['facts']}
    facts.update((f['fact_id'],f) for f in comparison)
    for p in packs:
        if p.get('bank'):
            b=p['bank'];registry['bank:'+str(b['id'])]=FactToken(re.sub(r'\s*(?:PLC\.?|পিএলসি)$','',b['name_bn' if bn else 'name_en'],flags=re.I),(),b['id'],'bank')
    for f in comparison:
        key='bank:'+str(f['institution_id'])
        if key not in registry:
            name=f.get('bank_name_bn' if bn else 'bank_name_en')
            if name:registry[key]=FactToken(re.sub(r'\s*(?:PLC\.?|পিএলসি)$','',name,flags=re.I),(),f['institution_id'],'bank')
    for fid,f in facts.items():
        if f['kind']=='insurance' and not insurance:continue
        if f['kind']=='peer' and not material(f):continue
        meaning=f['kind'] in {'status','figure'} and f.get('values',{}).get('metric') in {None,'crar','npl_ratio'}
        registry['f:'+fid]=FactToken(fact_clause(f,language,meaning), (fid,), f.get('institution_id'),f['kind'])
        registry['value:'+fid]=FactToken(fact_clause(f,language,False) if f['kind']=='figure' else card_text(f,language),(fid,),f.get('institution_id'),f['kind'])
        from ilma_api.human_styles import alternatives
        for index,wording in enumerate(alternatives(f,language)):
            registry['v'+str(index)+':'+fid]=FactToken(wording,(fid,),f.get('institution_id'),f['kind'])
    for index,f in enumerate(comparison):
        v=f['values'];prefix='row:'+str(index)+'.'
        bank=registry.get('bank:'+str(f['institution_id']))
        if bank:registry[prefix+'bank']=FactToken(bank.text,(f['fact_id'],),f['institution_id'],'row')
        registry[prefix+'rate']=FactToken(number(v['rate'])+unit_label(v['unit'],bn),(f['fact_id'],),f['institution_id'],'row')
        registry[prefix+'term']=FactToken(term(v,bn,v.get('selected_tenor')),(f['fact_id'],),f['institution_id'],'row')
        registry[prefix+'offer']=registry['f:'+f['fact_id']]
        if v.get('status')=='no_data':
            base=registry[prefix+'offer']
            registry[prefix+'offer']=FactToken(base.text+(', তবে ব্যাংকটির অবস্থা যাচাইয়ের তথ্য কম' if bn else '; there is insufficient information to assess this bank'),base.fact_ids,base.bank_id,base.kind)
    return registry,facts


def fill(sentence,registry,used,*,insurance=False):
    keys=TOKEN.findall(sentence)
    if not keys:raise ValueError('missing_fact_token')
    if any(key not in registry for key in keys):raise ValueError('unknown_token')
    if any(fid not in used for key in keys for fid in registry[key].fact_ids):raise ValueError('undeclared_fact')
    residual=TOKEN.sub('',sentence)
    if re.search(r'[0-9০-৯%]|শতাংশ|percent|সবচেয়ে|highest|lowest|সর্বাধিক|সর্বনিম্ন',residual,re.I):raise ValueError('raw_value')
    if ADVICE.search(residual):raise ValueError('advice')
    words=re.findall(r'[\w\u0980-\u09ff]+',residual.lower())
    if any(word not in CONNECTORS for word in words):raise ValueError('raw_claim')
    if BANNED.search(residual):raise ValueError('jargon')
    if not insurance and PROTECTION_WORDS.search(residual):raise ValueError('unsolicited_protection')
    ids=list(dict.fromkeys(fid for key in keys for fid in registry[key].fact_ids))
    rows={key.split('.')[0] for key in keys if key.startswith('row:')}
    if len(rows)>1:raise ValueError('mixed_comparison_rows')
    named={registry[key].bank_id for key in keys if registry[key].kind=='bank' or key.startswith('row:') and key.endswith('.bank')}
    claimed={registry[key].bank_id for key in keys if registry[key].fact_ids and registry[key].bank_id is not None}
    if named and not claimed<=named:raise ValueError('bank_fact_binding')
    text=re.sub(r'([।.?])\1+',r'\1',TOKEN.sub(lambda m:registry[m[1]].text,sentence))
    if not insurance and PROTECTION_WORDS.search(text):raise ValueError('unsolicited_protection')
    if BANNED.search(text) and not insurance:raise ValueError('jargon')
    return text,ids
