"""Deterministic claim checks on cited facts, before any speech is synthesized."""
from decimal import Decimal,ROUND_HALF_UP
import json,re
from ilma_api.voice_numbers import NUMBERS
from ilma_api.voice_text import normalize_alias

ADVICE=re.compile(r'(?:এখানে|ওখানে|এই ব্যাংকে|ওই ব্যাংকে|টাকা|আমানত)\s*(?:টাকা\s*)?(?:রাখুন|রাখবেন না)|তুলে নিন|বিনিয়োগ করুন|নিরাপদ জায়গা|\b(?:you should|i recommend|we recommend|put your money|invest in|safest|best bank)\b',re.I)
UNCONFIRMED=re.compile(r'সরকারিভাবে নিশ্চিত নয়|খবরের তথ্য|সংবাদের তথ্য|সংবাদ প্রতিবেদন|খবরে|reported|news|not officially confirmed|unconfirmed',re.I)
RANK=re.compile(r'সবচেয়ে|অন্যদের চেয়ে|সর্বাধিক|সর্বনিম্ন|\b(?:highest|lowest|more than other|less than other|best rate)\b',re.I)
MONTHS=('জানুয়ারি ফেব্রুয়ারি মার্চ এপ্রিল মে জুন জুলাই আগস্ট সেপ্টেম্বর অক্টোবর নভেম্বর ডিসেম্বর January February March April May June July August September October November December').split()


def sentences(text):return [s.strip() for s in re.split(r'(?<=[।.!?])\s+',text) if s.strip()]


def numeric_claims(text):
    text=text.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789')).replace('−','-')
    text=re.sub(r'(?<=\d),(?=\d)','',text)
    text=re.sub(r'(\d+)\s+দশমিক\s+(\d+)',r'\1.\2',text)
    text=re.sub(r'(?:মাইনাস|ঋণাত্মক|minus)\s+(?=\d)','-',text,flags=re.I)
    found=[Decimal(n) for n in re.findall(r'(?<!\w)-?\d+(?:\.\d+)?',text)]
    # Phrase-level halves/quarters are one claim, not two unrelated numbers.
    for marker,amount in [('সাড়ে',Decimal('.5')),('সোয়া',Decimal('.25')),('পৌনে',Decimal('-.25'))]:
        for word in re.findall(marker+r'\s+([^\s।,.!?]+)',text):
            value=NUMBERS.get(word)
            if value is not None:found.append(value+amount)
        text=re.sub(marker+r'\s+[^\s।,.!?]+',' ',text)
    for match in re.finditer(r'[\w\u0980-\u09ff]+',text):
        word=match[0]
        # Bengali নয় means either nine or "not". Count it only with an
        # explicit quantity unit, never inside the required news disclaimer.
        if word in {'নয়','নয়'} and not re.match(r'\s*(?:%|শতাংশ|টাকা|লাখ|কোটি|হাজার|বছর|মাস|জন|টি|টা)',text[match.end():]):continue
        if word in NUMBERS:found.append(NUMBERS[word])
    return found


def support_numbers(facts):
    values=set()
    def add(value):
        try:
            number=Decimal(str(value))
            if not number.is_finite():return
            values.add(number);values.add(abs(number));values.add(number.quantize(Decimal('1'),rounding=ROUND_HALF_UP));values.add((number*2).quantize(Decimal('1'),rounding=ROUND_HALF_UP)/2)
            values.update(number.quantize(Decimal(p),rounding=ROUND_HALF_UP) for p in ('.01','.1'))
        except Exception:pass
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key not in {'input_fact_ids','unusual'}:walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
        elif isinstance(value,(float,int,Decimal)) and not isinstance(value,bool):add(value)
        elif isinstance(value,str):
            for number in numeric_claims(value):add(number)
    for f in facts:
        if f.get('kind')=='history':add(1)
        walk(f.get('values',{}))
        for key in ['text_bn','text_en']:walk(f.get(key,''))
        walk(f.get('source',{}).get('quote',''))
        v=f.get('values',{})
        if v.get('metric') in {'crar','npl_ratio'}:
            add(Decimal(str(v['value']))*100);add(100)
        if v.get('metric')=='net_profit':add(Decimal(str(v['value']))/10000000)
        if f.get('kind')=='insurance' and v.get('limit'):
            add(v['limit']);add(Decimal(str(v['limit']))/100000)
            if v.get('per_person') or v.get('per_bank'):add(1)
        if f.get('kind')=='service' and v.get('unit')=='pct_year':
            add(v.get('rate'));add(100000);add(1)
            if v.get('selected_tenor')==12 and v.get('basis')=='conventional':add(Decimal(str(v['rate']))*1000)
        for key in ['tenor_months','selected_tenor','tenor_min_months','tenor_max_months']:
            if v.get(key):add(v[key]);add(Decimal(v[key])/12)
        for value in v.get('tenor_options') or []:add(value);add(Decimal(value)/12)
    return values


def bank_mentions(text,banks):
    normalized=' '+normalize_alias(text)+' ';result=set()
    for bank in banks:
        for name in [bank['name_bn'],bank['name_en'],*bank.get('aliases',[])]:
            alias=normalize_alias(name)
            if len(alias)<3:continue
            if re.search(r'(?<!\S)'+re.escape(alias)+r'(?:ের|র)?(?!\S)',normalized):result.add(bank['id']);break
    return result


def percent_claims(text):
    text=text.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789')).replace('−','-')
    text=re.sub(r'(?:মাইনাস|ঋণাত্মক|minus)\s+(?=\d)','-',text,flags=re.I)
    return [Decimal(n) for n in re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:%|percent|শতাংশ)',text,re.I)]


def percent_support(facts):
    allowed=set()
    for f in facts:
        v=f.get('values',{});values=[]
        if f.get('kind')=='service' and v.get('unit')=='pct_year':values=[v.get('rate')]
        elif v.get('metric') in {'crar','npl_ratio'}:
            values=[v.get('value'),v.get('median')] if f.get('kind')=='peer' else [Decimal(str(v['value']))*100,v.get('minimum_percent')]
        elif v.get('metric') in {'profit_change','fdr_12_rate','dps_12_rate'}:values=[v.get('value'),v.get('median')]
        for value in values:
            if value is None:continue
            n=Decimal(str(value));allowed.update((n,n.quantize(Decimal('1'),rounding=ROUND_HALF_UP),(n*2).quantize(Decimal('1'),rounding=ROUND_HALF_UP)/2))
            allowed.update(n.quantize(Decimal(p),rounding=ROUND_HALF_UP) for p in ('.01','.1'))
    return allowed


def check(answer,facts,banks,seen=(),allow_repeat=False,insurance_said=False):
    reasons=[];known={f['fact_id']:f for f in facts};ids=answer.used_fact_ids
    if any(id not in known for id in ids):return ['unknown_fact_id']
    cited=[known[id] for id in ids];parts=sentences(answer.reply)
    if len(parts)!=len(answer.sentence_fact_ids):reasons.append('sentence_citation_count')
    if set(id for ids in answer.sentence_fact_ids for id in ids)!=set(answer.used_fact_ids):reasons.append('sentence_citation_union')
    if not allow_repeat and set(ids)&set(seen):reasons.append('repeated_fact')
    if insurance_said and any(f['kind']=='insurance' for f in cited) and answer.intent not in {'insurance','repeat'}:reasons.append('insurance_repeated')
    text=answer.reply+' '+answer.next_question
    question_numbers=numeric_claims(answer.next_question)
    question_allowed=support_numbers(cited)
    if answer.buttons and not re.search(r'%|শতাংশ|টাকা|taka|বছর|years?|মাস|months?',answer.next_question,re.I):question_allowed.update((Decimal(1),Decimal(2)))
    for number in question_numbers:
        in_range=False
        if re.search(r'বছর|years?',answer.next_question,re.I):
            in_range=any(f.get('kind')=='service' and not f['values'].get('tenor_options') and f['values'].get('tenor_min_months') is not None and Decimal(f['values']['tenor_min_months'])<=number*12<=Decimal(f['values']['tenor_max_months']) for f in cited)
        if number not in question_allowed and not in_range:reasons.append('unsupported_question_number')
    if re.search(r'কত\s*(?:টাকা|পরিমাণ)|আপনার\s*ব্যালান্স|your balance|what amount',answer.next_question,re.I) or re.search(r'how much.*(?:deposit|invest|save|money)',answer.next_question,re.I):reasons.append('personal_amount_question')
    if re.search(r'[:;()\[\]—]|\bPLC\b|পিএলসি|\b[HWP][1-9]\b',text):reasons.append('report_style')
    if ADVICE.search(text):reasons.append('advice')
    if re.search(r'\b(?:safe|guaranteed|bankrupt)\b|নিশ্চিতভাবে নিরাপদ|দেউলিয়া|ডুবে যাচ্ছে',answer.reply,re.I):reasons.append('safety_guarantee')
    if answer.language=='en' and any(p[0].isalpha() and p[0].islower() for p in parts):reasons.append('sentence_capitalization')
    limit=20 if answer.intent in {'smalltalk','unclear','stop','out_of_scope'} else 60
    if len(text.split())>limit:reasons.append('word_limit')
    if answer.intent=='bank_overview' and not seen and len(text.split())<45:reasons.append('introduction_too_short')
    if answer.intent not in {'smalltalk','unclear','stop','out_of_scope','advice_request','best_bank','explain_term'} and not cited:reasons.append('missing_facts')
    worse=[f for f in facts if f.get('kind')=='peer' and f.get('institution_id')==answer.bank.id and f['values'].get('worse') and f['fact_id'] not in seen]
    if answer.intent=='bank_overview' and worse and not any(f['fact_id'] in ids for f in worse):reasons.append('missing_worse_peer')
    expected_banks={f.get('institution_id') for f in cited}|({answer.bank.id} if answer.bank.id else set())
    if not bank_mentions(text,banks)<=expected_banks:reasons.append('unsupported_bank')
    for index,part in enumerate(parts):
        part_ids=answer.sentence_fact_ids[index] if index<len(answer.sentence_fact_ids) else []
        if any(id not in known for id in part_ids):reasons.append('unknown_sentence_fact');continue
        support=[known[id] for id in part_ids]
        named=bank_mentions(part,banks)
        # Bind a named bank's numerical claims to that bank's cited records.
        if len(named)==1 and answer.intent=='compare':
            support=[f for f in support if f.get('institution_id') in named or f.get('institution_id') is None]
        allowed=support_numbers(support)
        if len(support)>1 and all(f.get('kind')=='history' for f in support) and re.search(r'খবর|ঘটনা|reports|incidents',part,re.I):
            allowed.add(Decimal(len({f['fact_id'] for f in support})))
        if any(n not in allowed and abs(n) not in allowed for n in numeric_claims(part)):reasons.append('unsupported_number')
        percentages=percent_claims(part)
        if any(n not in percent_support(support) for n in percentages):reasons.append('unsupported_percentage')
        if answer.intent=='compare' and len(named)>1 and percentages:reasons.append('ambiguous_bank_rate_binding')
        support_text=' '.join(str(f.get('values',{}).get('product',''))+' '+f.get('text_en','')+' '+f.get('text_bn','') for f in support)
        for grade in re.findall(r'(?<!\w)(?:AAA|AA[+-]?|BBB[+-]?|BB[+-]?|ST-[1-6])\b',part):
            if grade not in support_text:reasons.append('unsupported_rating')
        for agency in re.findall(r'\b(?:CRAB|CRISL|ECRL|NCR|ACRSL)\b',part):
            if agency not in support_text:reasons.append('unsupported_rating_agency')
        for product in re.findall(r'\b(?:[A-Z][a-zA-Z-]+\s+){1,3}(?:DPS|MSS|Scheme|Deposit|Savings)\b',part):
            product=re.sub(r'^(?:The|For|At|In)\s+','',product)
            if normalize_alias(product) not in normalize_alias(support_text):reasons.append('unsupported_product')
        for name in re.findall(r'\b(?:[A-Z][a-zA-Z-]+\s+){1,5}Bank\b',part):
            name=re.sub(r'^(?:The|For|At|In|Unlike)\s+','',name)
            exact=any(normalize_alias(name)==normalize_alias(alias) for b in banks for alias in [b['name_en'],*b.get('aliases',[])])
            # Capitalized extraction can return "Commerce Bank" from the full
            # verified "National Credit and Commerce Bank". Accept that suffix
            # only when the same sentence names that registered, cited bank.
            suffix=any(b['id'] in named and b['id'] in expected_banks and name.casefold() in b['name_en'].casefold() for b in banks)
            if not exact and not suffix:reasons.append('unsupported_bank')
        for f in support:
            v=f.get('values',{})
            if v.get('metric')=='crar' and re.search(r'প্রতি\s*(?:১০০|100|একশো)|per\s+100|every\s+100',part,re.I) and not re.search(r'ঝুঁকিভিত্তিক সম্পদ|risk.weighted assets',part,re.I):reasons.append('capital_denominator')
            if v.get('metric')=='crar' and v.get('value',0)<0 and re.search(r'capital|মূলধন',part,re.I):
                if not re.search(r'[-−]|মাইনাস|ঋণাত্মক|negative|minus',part,re.I):reasons.append('negative_capital_sign')
        for month in MONTHS:
            if re.search(r'(?<![\w\u0980-\u09ff])'+re.escape(month)+r'(?![\w\u0980-\u09ff])',part,re.I):
                from ilma_api.rules.reasons import MONTHS_BN
                month_num=next((k for k,v in MONTHS_BN.items() if v==month),None)
                if month_num is None:
                    import calendar
                    month_num=next((i for i in range(1,13) if calendar.month_name[i].lower()==month.lower()),None)
                dates=json.dumps([f.get('values',{}) for f in support],ensure_ascii=False)
                if month_num and not re.search(r'\d{4}-'+f'{month_num:02d}'+r'-',dates):reasons.append('unsupported_month')
        if any(f.get('kind')=='history' and not f['values'].get('official') for f in support) and not UNCONFIRMED.search(answer.reply):reasons.append('unconfirmed_history')
        history=[f for f in support if f.get('kind')=='history']
        if history:
            years={int(f['values']['event_date'][:4]) for f in history}
            mentioned={int(n) for n in numeric_claims(part) if 1900<=n<=2100}
            if mentioned and not mentioned<=years:reasons.append('history_event_year')
        if RANK.search(part):
            eligible=[f for f in support if f.get('kind')=='peer' or f.get('values',{}).get('rank')]
            if not eligible:reasons.append('unsupported_rank')
            else:
                high=bool(re.search(r'সবচেয়ে\s*(?:বেশি|উচ্চ)|highest|largest|more than other|অন্যদের চেয়ে বেশি',part,re.I))
                low=bool(re.search(r'সবচেয়ে\s*(?:কম|নিম্ন)|lowest|smallest|less than other|অন্যদের চেয়ে কম',part,re.I))
                key='rank_high' if high else 'rank_low' if low else 'rank'
                if not any(f['values'].get(key,f['values'].get('rank'))==1 for f in eligible):reasons.append('wrong_rank')
        # A status claim must use the computed status fact for that bank.
        codes={'strong':r'অবস্থা ভালো|ভালো অবস্থা|ভালো অবস্থায়|in good condition|looks good|condition is good|is strong|strong condition',
               'watch':r'সতর্কতা দরকার|কিছু সতর্কতা|সতর্ক থাকুন|warning signs|needs caution',
               'high':r'ঝুঁকি বেশি|high risk|faces risk',
               'no_data':r'অবস্থা যাচাই হয়নি|যথেষ্ট তথ্য নেই|তথ্য কম|condition unverified|cannot be assessed|not enough data'}
        statuses=[f.get('status',{}).get('code') for f in support if f.get('status')]
        statuses.extend(f['values'].get('status') for f in support if f.get('values',{}).get('status'))
        for code,pattern in codes.items():
            if code=='no_data' and answer.intent in {'bank_profile','explain_term','services_list'} and not re.search(r'অবস্থা|condition|risk|ঝুঁকি',part,re.I):continue
            if re.search(pattern,part,re.I) and code not in statuses:reasons.append('status_mismatch')
        if any(f.get('kind')=='insurance' for f in support):
            if re.search(r'বন্ধ.*ফেরত পাবেন|will (?:get|receive)|you get back',part,re.I) and not re.search(r'শর্ত|eligible|conditions|subject to',part,re.I):reasons.append('unconditional_insurance')
            if re.search(r'১৭|\b17\b|সতেরো|seventeen',part,re.I):reasons.append('unsupported_payout_deadline')
        if any(f.get('values',{}).get('dated') for f in support) and (percentages or re.search(r'সুদ|হার|ফি|interest|rate|fee|charge',part,re.I)) and not re.search(r'হারতালিকা|তালিকা|পুরনো|schedule|dated|old|as of',part,re.I):reasons.append('dated_rate_unqualified')
    return list(dict.fromkeys(reasons))
