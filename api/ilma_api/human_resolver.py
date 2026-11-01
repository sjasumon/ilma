"""Code-owned bank and service slots, resolved before paid wording requests."""
from dataclasses import dataclass,field
import re,unicodedata
from ilma_api.voice_text import join_acronyms,match_candidates,normalize_alias
from ilma_api.voice_numbers import normalize_numbers

ACRONYMS={'sbacbank':('SBAC','এসবিএসি','South Bangla Bank','South Bangla','সাউথ বাংলা ব্যাংক','সাউথ বাংলা'),'nbl':('National Bank','ন্যাশনাল ব্যাংক'),'islamibank':('Islami Bank','ইসলামী ব্যাংক'),'ebl':('EBL','ইবিএল'),'mtb':('MTB','এমটিবি'),
 'nccbank':('NCC','এনসিসি'),'dutchbangl':('DBBL','ডিবিবিএল'),
 'primebank':('Prime','প্রাইম'),
 'citybank':('City Bank','সিটি ব্যাংক'),'bracbank':('BRAC','ব্র্যাক','break bank','breakbank','bragg bank','brak bank','black bank','brack bank','ব্রেক ব্যাংক','ব্ল্যাক ব্যাংক','ব্রাক ব্যাংক')}
PROTECTION=re.compile(r'বীমা|বিমা|সুরক্ষা|\binsur(?:ance|ed|e)\b|\bprotect(?:ion|ed)\b|(?:ব্যাংক|bank).{0,20}(?:(?<!ম্)বন্ধ|clos)|টাকা.{0,15}সুরক্ষিত',re.I)
CORRECTION=re.compile(r'^না(?:[\s,।]|$)|না আমি|নয়|নয়|ভুল|শুধরে|বদলে|সংশোধন|ধরুন|আগের প্রশ্ন|আমার কথা ছিল|কথাই বলছি|আমি বলেছিলাম|নাম.{0,24}হবে|জন্যই জানতে চেয়েছি|\b(?:i meant|not|correct|instead|that should|use .*previous|was asking|previous question|bank in my last question)\b',re.I)

AWARDS=re.compile(r'পুরস্কার|পুরষ্কার|অ্যাওয়ার্ড|এওয়ার্ড|স্বীকৃতি|\bawards?\b|\brecogni[sz]',re.I)

def tidy_spelling(text):
    """Common spellings of the words the rest of the resolver looks for."""
    for wrong,right in (('ব্যাঙ্ক','ব্যাংক'),('সূদ','সুদ'),('ইসটার্ন','ইস্টার্ন'),('ইষ্টার্ন','ইস্টার্ন')):text=text.replace(wrong,right)
    return text

def is_banglish(text):
    """Bangla typed in Latin letters: bank words alone are not enough, so it needs a Bangla word."""
    return not re.search(r'[\u0980-\u09ff]',text) and bool(re.search(r'\b(?:er|koto|kemon|achhe|ache|kothay|sud|bolun|bolen)\b',text,re.I))

def is_interest_profit_question(text):
    return bool(not re.search(r'নিট|\bnet profit\b|\boperating profit\b',text,re.I) and re.search(r'সুদ|ইন্টারেস্ট|\binterest\b',text,re.I) and re.search(r'মুনাফা|লাভ|প্রফিট|\bprofit\b',text,re.I) and re.search(r'পার্থক্য|তফাত|ফারাক|difference|differ',text,re.I))

FOLLOW=re.compile(r'^(?:and\b|what about\b|how about\b|আর\s|ওই|এবার\s)',re.I)
HISTORY=re.compile(r'ঝামেলা|জালিয়াতি|কেলেঙ্কারি|অনিয়ম|আগে কোনো|\bscandals?\b|\bfraud\b|\bpast (?:events|incidents)\b',re.I)
def metric_named(text):
    return bool(re.search(r'মুনাফা|মূলধন|খেলাপি|রেটিং|অবস্থা|কেমন|profit|capital|rating|\bnpl\b',text,re.I))

def is_best_dps_question(text):
    """Only the global best-DPS question family; no ASR normalization changes."""
    value=unicodedata.normalize('NFC',text).casefold()
    if not re.search(r'ডি\s*পি\s*এস|(?<![a-z])d\s*p\s*s(?![a-z])',value):return False
    best=bool(re.search(r'(?:সবথেকে|সবচেয়ে|সবচে)\s*(?:ভালো|ভাল|বেশি)|সেরা|সর্বোচ্চ|\bbest\b|\bhighest\b',value))
    where=bool(re.search(r'কোথায়|কোথায়|কোন\s*ব্যাংক|\bwhere\b|\bwhich\s*bank',value))
    good=bool(re.search(r'ভালো|ভাল|বেশি|\bgood\b|\bbetter\b',value))
    normalized=normalize_numbers(value.replace('বছরের','বছর').replace('মাসের','মাস'))
    explicit=re.search(r'(?<!\w)(\d+)\s*months?\b',normalized)
    return (best or where and good) and (not explicit or int(explicit[1])==60)

def is_best_fdr_question(text):
    """The global best-FDR question family; one-year term unless another is named."""
    value=unicodedata.normalize('NFC',text).casefold()
    if not re.search(r'এফ\s*ডি\s*আর|(?<![a-z])f\s*d\s*r(?![a-z])|fixed\s+deposit|স্থায়ী\s*আমানত|স্থায়ী\s*আমানত',value):return False
    best=bool(re.search(r'(?:সবথেকে|সবচেয়ে|সবচে|সবচেয়ে)\s*(?:ভালো|ভাল|বেশি)|সেরা|সর্বোচ্চ|\bbest\b|\bhighest\b',value))
    where=bool(re.search(r'কোথায়|কোথায়|কোন\s*ব্যাংক|\bwhere\b|\bwhich\s*bank',value))
    good=bool(re.search(r'ভালো|ভাল|বেশি|\bgood\b|\bbetter\b',value))
    normalized=normalize_numbers(value.replace('বছরের','বছর').replace('মাসের','মাস'))
    explicit=re.search(r'(?<!\w)(\d+)\s*months?\b',normalized)
    return (best or where and good) and (not explicit or int(explicit[1])==12)

def best_rate_product(text):
    return 'dps' if is_best_dps_question(text) else 'fdr' if is_best_fdr_question(text) else None

@dataclass
class ResolvedTurn:
    text:str
    bank_id:int|None
    product:str|None
    tenor:int|None
    basis:str
    network:str|None
    tier:str|None
    intent:str|None=None
    correction:bool=False
    direct_protection:bool=False
    compare_bank_ids:list[int]=field(default_factory=list)
    candidates:list[dict]=field(default_factory=list)
    confirm_ids:list[int]=field(default_factory=list)
    requested_field:str|None=None
    requested_metric:str|None=None
    fee:str='annual_fee'
    term_asked:bool=False
    follow:bool=False
    confirm_pair:bool=False
    account_overview:bool=False


def resolve(text,c,banks):
    text=tidy_spelling(join_acronyms(unicodedata.normalize('NFC',text)).strip())
    matched_text=re.sub(r'(প্রাইম|সিটি|ইবিএল|এনসিসি|এমটিবি|ব্র্যাক)(?:ের|র)(?=$|[\s,।.!?])',r'\1',text)
    indexed=[{**b,'aliases':[*b.get('aliases',[]),*ACRONYMS.get(b.get('slug'),())]} for b in banks]
    # A possessive ending on any Bangla bank name ("ব্যাংক এশিয়ার") still names that bank.
    for alias in sorted({unicodedata.normalize('NFC',a) for b in indexed for a in [b.get('name_bn') or '',*b['aliases']] if re.search(r'[ঀ-৿]$',a)},key=len,reverse=True):
        matched_text=re.sub(re.escape(alias)+r'(?:ের|র)(?=$|[\s,।.!?])',alias,matched_text)
    # Words that name no bank ("compare with other banks") must not fuzzy-match one such as "Commerce Bank".
    matched_text=re.sub(r'\b(?:compare|comparison|(?:with |to )?(?:the )?other banks?|another bank|all (?:the )?banks|other bank)\b|অন্য (?:কোনো )?ব্যাংক(?:ের|গুলোর)?|অন্যান্য ব্যাংক(?:ের)?','',matched_text,flags=re.I)
    # Joined names are independent mentions, not alternative spellings.
    # Fuzzy pairs only propose a joint confirmation; they never authorize facts.
    declared_pair=[]
    parts=re.split(r'\s+(?:এবং|ও|and|&)\s+',matched_text,flags=re.I)
    full_name_connector=any(re.search(r'(?<!\S)(?:and|এবং|ও)(?!\S)',normalize_alias(alias)) and (' '+normalize_alias(alias)+' ') in (' '+normalize_alias(matched_text)+' ') for b in indexed for alias in [b['name_bn'],b['name_en'],*b['aliases']]) if len(parts)==2 else False
    if len(parts)==2 and not full_name_connector:
        for part in parts:
            options=match_candidates(part,indexed)
            if not options or options[0]['confidence']<.8 or (len(options)>1 and options[0]['confidence']-options[1]['confidence']<.05) or (options[0]['confidence']<1 and not re.search(r'ব্যাংক|\bbank\b',part,re.I)):break
            declared_pair.append(options[0])
    if len(declared_pair)!=2 or declared_pair[0]['id']==declared_pair[1]['id']:declared_pair=[]
    correction=bool(CORRECTION.search(text))
    candidates=match_candidates(matched_text,indexed)
    clear_context=correction or bool(re.search(r'বলেছি|কথা|ধরুন|আগের প্রশ্ন|সংশোধন|সম্পর্কে|জানতে|ব্যাংক|asking|previous question|\bmean\b|\bbank\b',text,re.I))
    strong=[b for b in candidates if b['confidence']>=.9 and (not b.get('confirm') or b['confidence']==1 and (clear_context or normalize_alias(matched_text)==normalize_alias(b['alias'])))]
    normalized_text=normalize_alias(matched_text)
    excluded=set()
    spans=[]
    for b in strong:
        alias=normalize_alias(b['alias'])
        spans.extend((m.start(),m.end(),b['id']) for m in re.finditer(r'(?<!\S)'+re.escape(alias)+r'(?!\S)',normalized_text))
    if correction:
        for neg in re.finditer(r'(?<!\S)(নয়|নয়|not)(?!\S)',normalized_text,re.I):
            nearby=[s for s in spans if s[1]<=neg.start()] if neg[1].casefold()!='not' else [s for s in spans if s[0]>=neg.end()]
            if nearby:
                span=max(nearby,key=lambda s:s[1]) if neg[1].casefold()!='not' else min(nearby,key=lambda s:s[0])
                excluded.add(span[2])
        positive=[b for b in strong if b['id'] not in excluded]
        if positive:strong=positive
    if correction and len(strong)>1:
        tail=re.split(r'নয়|নয়|\bnot\b|বরং|\binstead\b',text,flags=re.I)[-1]
        affirmative=[b for b in match_candidates(tail,indexed) if b['confidence']>=.9 and not b.get('confirm')]
        if len(affirmative)==1:strong=affirmative
    named=list(dict.fromkeys(b['id'] for b in strong))
    bank=named[0] if named else c.institution_id
    # A plausible new name must not silently become the previous bank.
    uncertain_name=not named and any(b['confidence']<.9 for b in candidates)
    explicit_new_name=bool(re.search(r'\b(?:tell me about|what about|how about|about)\s+(?!(?:this|that|the|my|your|its)\b)[a-z][a-z -]*\bbank\b',text,re.I))
    if uncertain_name or (explicit_new_name and not named):bank=None
    if correction and not [b for b in strong if b['id'] not in excluded] and excluded:
        bank=c.institution_id if c.institution_id not in excluded else None
    product=next((p for p,pattern in [('fdr',r'এফডিআর|এফ ডি আর|\bfdr\b|fixed deposit|ফিক্সড ডিপোজিট|স্থায়ী আমানত'),('dps',r'ডিপিএস|ডি পি এস|\bdps\b|monthly savings|মাসিক সঞ্চয়|কনফিডেন্স|কোটিপতি|লাখপতি'),('savings',r'সঞ্চয়ী|সেভিংস|\bsavings?\b'),('card',r'কার্ড|\bcards?\b|visa|mastercard'),('home_loan',r'গৃহঋণ|home loan'),('personal_loan',r'personal loan|ব্যক্তিগত ঋণ'),('auto_loan',r'গাড়ি|car loan|auto loan')] if re.search(pattern,text,re.I)),None)
    account_word=bool(re.search(r'অ্যাকাউন্টস?|একাউন্টস?|একাউণ্ট|হিসাব|\baccounts?\b',text,re.I))
    debit_requested=bool(re.search(r'ডেবিট|\bdebit\b',text,re.I))
    fee_requested=bool(re.search(r'ফি(?=$|[\s।?!,]|র(?:\s|$))|চার্জ|\bfees?\b|\bcharges?\b',text,re.I))
    interest_requested=bool(re.search(r'সুদ|সুদের হার|\binterest\b|\brate\b',text,re.I))
    account_overview=account_word and product is None and not re.search(r'মূলধন|মুনাফা|খেলাপি|ব্যালেন্স|নম্বর|পিন|ঋণ|লোন|বীমা|বিমা|সুরক্ষা|\b(?:capital|profit|balance|number|pin|loan|insurance|protection)\b',text,re.I)
    if debit_requested:product='account_fee';account_overview=False
    elif account_overview:
        product='savings' if interest_requested else 'account_fee'
        account_overview=not fee_requested and not interest_requested
    elif fee_requested and product is None and c.product=='account_fee':product='account_fee'
    elif interest_requested and product is None and c.product in {'account_fee','savings'}:product='savings'
    changed=bank!=c.institution_id
    follow=bool(FOLLOW.match(text)) and product is None and bool(c.product) and bool(named) and len(text.split())<=6
    retained=correction or not changed or follow
    selected=product or (c.product if retained else None)
    normalized=normalize_numbers(text.replace('বছরের','বছর').replace('মাসের','মাস').replace('-',' ')).translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    match=re.search(r'(?<!\w)(\d+)\s*(?:months?|মাস)(?:ের)?',normalized,re.I)
    tenor=int(match[1]) if match and 1<=int(match[1])<=600 else c.tenor if retained and (product is None or product==c.product) else None
    network=next((value for value,pattern in [('Visa',r'visa|ভিসা'),('Mastercard',r'mastercard|মাস্টারকার্ড'),('Amex',r'amex|অ্যামেক্স')] if re.search(pattern,text,re.I)),None)
    tier=next((value for value,pattern in [('Gold',r'gold|গোল্ড'),('Platinum',r'platinum|প্লাটিনাম|প্ল্যাটিনাম'),('Signature',r'signature|সিগনেচার|সিগনিচার'),('Classic',r'classic|ক্লাসিক'),('World',r'world|ওয়ার্ল্ড'),('Infinite',r'infinite|ইনফিনিট'),('Titanium',r'titanium|টাইটানিয়াম')] if re.search(pattern,text,re.I)),None)
    if selected=='card':network=network or (c.network if retained else None);tier=tier or (c.tier if retained else None)
    else:network=tier=None
    direct=bool(PROTECTION.search(text))
    intent='insurance' if direct else 'compare' if re.search(r'তুলনা|মিলিয়ে|মেলান|পাশাপাশি|অন্য ব্যাংক|অন্যদের|আর কোন ব্যাংক|\bcompare|comparison|other banks?|side by side|\bvs\b',text,re.I) else 'service_detail' if product or follow else None
    if correction and (named or match):intent=c.last_intent if c.last_intent not in {None,'unclear','repeat','stop','correction'} else 'bank_overview'
    if re.fullmatch(r'থামুন|থামান|stop|stop speaking',text.strip(' .!?।'),re.I):intent='stop'
    if re.fullmatch(r'আবার(?: বলুন| শুনুন)?|আগের উত্তর|repeat(?: that)?|again|once more',text.strip(' .!?।'),re.I):intent='repeat'
    if re.search(r'আগের উত্তর|আগেরটা শুনতে|শেষ কথাটা|একই কথাটা|যা বললেন|শেষ উত্তর|পুনরায় শুনতে|আবার শুনতে|last answer|previous reply|what you just said|say it again|once more|replay.*answer',text,re.I):intent='repeat'
    compare=list(dict.fromkeys([*named,*([c.institution_id] if correction and c.institution_id and c.last_intent=='compare' else [])]))
    if intent=='compare' and not correction and c.institution_id and (c.institution_id in named or re.search(r'এই ব্যাংক|ওই ব্যাংক|this bank|current bank',text,re.I)):
        bank=c.institution_id
        if bank not in compare:compare.insert(0,bank)
        if product is None:selected=c.product
        if match is None:tenor=c.tenor
        if selected=='card':network=network or c.network;tier=tier or c.tier
    if intent=='compare' and not named and c.last_intent=='compare' and c.compare_bank_ids:
        compare=list(dict.fromkeys(([c.institution_id] if c.institution_id else [])+c.compare_bank_ids))
    if intent!='compare':compare=[]
    confirm=[b['id'] for b in candidates if .7<=b['confidence']<.9][:2] if not named else []
    # One close name with a clear topic is that bank; two close names still ask.
    if len(confirm)==1 and (selected or metric_named(text)):bank=confirm[0];confirm=[]
    wanted=next((name for name,pattern in [('sub_branches',r'উপশাখা|sub.branch'),('branches',r'শাখা|branches'),('founded_year',r'প্রতিষ্ঠা(?=$|[\s:?।]|কাল|সাল|বছর)|প্রতিষ্ঠিত|কোন সালে|যাত্রা শুরু|founded|established'),('atms',r'এটিএম|\batms?\b'),('customers',r'গ্রাহকের সংখ্যা|customers'),('agent_outlets',r'এজেন্ট|agent outlet'),('known_for',r'কী জন্য পরিচিত|known for')] if re.search(pattern,text,re.I)),None)
    metric=next((name for name,pattern in [('net_profit',r'মুনাফা|নিট লাভ|লাভ কত|লাভ কম|লাভ কেমন|লোকসান|profit'),('crar',r'মূলধন|\bcapital\b|\bcrar\b'),('npl_ratio',r'খেলাপি ঋণ|bad loans|percentage of loans|\bnpl\b'),('rating',r'রেটিং|rating')] if re.search(pattern,text,re.I)),None)
    # "এফডিআরের মুনাফার হার" is an Islamic deposit rate, not the bank's profit.
    if selected in {'fdr','dps','savings'} and product:metric=None
    if metric=='net_profit' and re.search(r'আগের বছর|গত বছর|last year|previous year',text,re.I) and not re.search(r'অন্য ব্যাংক|other bank',text,re.I):intent='bank_figures'
    explain=bool(re.search(r'মানে|অর্থ|জিনিস|শব্দটা.*বুঝিয়ে|বোঝায়|(?:এফডিআর|ডিপিএস|মূলধন) (?:কী|কি)[?।.!]*$|\bmean\b|what(?:’s|\'s| is| are) (?:an? |the )?(?:fdr|dps|npl|crar|fixed deposits?|savings accounts?)[?।.!]*$|what is (?:a |an |net |capital |credit )|explain .*simply',text,re.I))
    if not correction and intent not in {'compare','insurance','stop','repeat'}:
        if explain and (metric or product or re.search(r'মধ্যমান|বাফার|median|buffer',text,re.I)):intent='explain_term'
        elif wanted:intent='bank_profile'
        elif metric and (named or c.institution_id) and re.search(r'কত|কেমন|পর্যাপ্ত|অঙ্ক|হিসাব|figure|how much|\bhow\b|enough|adequate|ratio|percentage|profit|রেটিং|\brating\b',text,re.I):intent='bank_figures'
        elif HISTORY.search(text):intent='bank_history'
    if not correction and intent not in {'compare','insurance','stop','repeat'} and AWARDS.search(text):intent='bank_awards'
    if not direct and intent not in {'repeat','stop','bank_awards'}:
        if re.search(r'সেরা|(?:সবচেয়ে|সবার চেয়ে).*(?:ভালো|ভাল|নিরাপদ|ভরসা)|এক নম্বর ব্যাংক|\b(?:best|safest|most reliable|number (?:one|1))\b',text,re.I):intent='best_bank'
        elif re.search(r'টাকা.*(?:রাখব|রাখা উচিত|তুলে|সরাব)|কোথায়.*রাখ|কোন ব্যাংকে.*সঞ্চয়|বেছে|সিদ্ধান্ত.*(?:নিন|নেব|নিতে)|পরামর্শ চাই|আমার হয়ে|\brecommend\b|\bshould (?:i|we)\b|\b(?:i|we) should\b|(?:which|what) bank should|decide.*(?:keep|savings)|choose.*bank|where.*(?:keep|invest|deposit)',text,re.I):intent='advice_request'
    if intent is None and re.search(r'সেবা|পণ্য|services|products',text,re.I):intent='services_list'
    if intent is None and re.search(r'where (?:(?:can|could) (?:i|we)|(?:i|we) (?:can|could)) (?:save|keep|deposit)|পেনশন.*(?:কোথায়|কোথায়)',text,re.I):intent='advice_request'
    if intent is None:
        if re.search(r'বর্তমান অবস্থা|ঝুঁকি|সতর্কতার|নিরাপদ|current condition|warning signs|\bsafe\b|\brisk\b',text,re.I):intent='bank_condition'
        elif re.search(r'কেমন আছে|কেমন চলছে|কেমন ব্যাংক|সম্পর্কে বল|সম্বন্ধে.*বল|নিয়ে বল|একটা ধারণা|ব্যাংকটা কেমন|how is .*doing|tell me about|what can you tell|general introduction',text,re.I):intent='bank_overview'
    basis=c.basis or 'conventional'
    if re.search(r'ইসলামি|ইসলামী|শরিয়াহ|islamic|sharia',text,re.I):basis='islamic'
    elif re.search(r'প্রচলিত|conventional',text,re.I):basis='conventional'
    elif changed:
        named_bank=next((b for b in banks if b['id']==bank),{})
        basis='islamic' if named_bank.get('islamic') else 'conventional'
    if len(named)>=2 and (intent in {'bank_overview','bank_condition'} or intent is None and not wanted and not metric):
        intent='compare';compare=named;selected=None;tenor=None
    # Two banks joined by "and" with one service: answer both, not just one.
    joined=len(named)>=2 and selected not in {None,'account_fee'} and intent in {None,'service_detail'} and not correction
    if joined:intent='compare';compare=named
    confirm_pair=False
    if declared_pair and intent in {None,'bank_overview','bank_condition','compare','service_detail'}:
        pair_ids=[row['id'] for row in declared_pair]
        if any(row['confidence']<1 for row in declared_pair) or not all(id in named for id in pair_ids):
            confirm_pair=True;confirm=pair_ids;compare=pair_ids;bank=c.institution_id;intent='compare'
            if product is None:selected=None;tenor=None
    if account_overview:intent='services_list';selected='account_fee';tenor=None;network=tier=None;metric=None;wanted=None
    elif product=='account_fee':intent='service_detail';wanted='debit' if debit_requested else 'account_fees';tenor=None;network=tier=None
    if is_interest_profit_question(text):intent='explain_term';selected=None;metric=None;compare=[]
    best=best_rate_product(text)
    if best:
        bank=None;selected=best;tenor=60 if best=='dps' else 12;basis='conventional';network=tier=None;intent='compare';compare=[];confirm=[]
    # One bank in a comparison (the other name was misheard or left out) is compared with every bank, not with itself.
    if intent=='compare' and len(compare)==1 and not confirm_pair:compare=[]
    fee='late_fee' if re.search(r'লেট|দেরিতে|বিলম্ব|\blate\b',text,re.I) else 'annual_fee'
    # Where a question names two banks, keep them in the order it said them.
    compare.sort(key=lambda id:next((s[0] for s in sorted(spans) if s[2]==id),99))
    if joined and intent=='compare' and compare:bank=compare[0]
    return ResolvedTurn(text,bank,selected,tenor,basis,network,tier,intent,correction,direct,compare,candidates,confirm,wanted,metric,fee,bool(match),follow or bool(FOLLOW.match(text)),confirm_pair,account_overview)
