"""Deterministic comparison narration and reviewed, saved clips; no runtime TTS."""
import hashlib,json,re
from pathlib import Path
from ilma_api.audio_integrity import verified_audio
from ilma_api.voice_numbers import pronounce
from ilma_api.card_catalog import numeric,NETWORKS,TIERS
ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'static/audio/services'
SHORT={'ebl':'ইস্টার্ন ব্যাংক','bracbank':'ব্র্যাক ব্যাংক','citybank':'সিটি ব্যাংক','dutchbangl':'ডাচ্ বাংলা','bankasia':'ব্যাংক এশিয়া','nccbank':'এনসিসি','primebank':'প্রাইম','mtb':'এমটিবি','sbacbank':'সাউথবাংলা'}

ATTRIBUTES=('annual_fee','interest_rate','late_fee','cash_advance_fee','foreign_currency_markup')

def key(network,tier,attribute=None):
    def slug(value):return re.sub('[^a-z0-9]+','-',value.casefold()).strip('-')
    return 'bn:card-'+slug(network)+'-'+slug(tier)+('-'+slug(attribute) if attribute else '')

def join_bn(items):
    items=list(items)
    return items[0] if len(items)==1 else ', '.join(items[:-1])+' ও '+items[-1] if items else ''

LOC={'ebl':'ইস্টার্ন ব্যাংকে','bracbank':'ব্র্যাক ব্যাংকে','citybank':'সিটি ব্যাংকে','bankasia':'ব্যাংক এশিয়ায়','nccbank':'এনসিসিতে','primebank':'প্রাইমে','mtb':'এমটিবিতে','sbacbank':'সাউথবাংলায়'}
GEN={'ebl':'ইস্টার্ন ব্যাংকের','bracbank':'ব্র্যাক ব্যাংকের','citybank':'সিটি ব্যাংকের','bankasia':'ব্যাংক এশিয়ার','nccbank':'এনসিসির','primebank':'প্রাইমের','mtb':'এমটিবির','sbacbank':'সাউথবাংলার'}

def narration(result,language='bn'):
    """Complete sentences with explicit units; never shorten facts to fit audio."""
    if result['choice']['product_type']!='card' or language!='bn':return ''
    rows=[b for b in result['rows'] if b.get('facts',{}).get('annual_fee') and not b['facts']['annual_fee']['stale'] and b['facts']['annual_fee']['value_num'] is not None]
    rows.sort(key=lambda b:(b['facts']['annual_fee']['value_num'],b['id']))
    if len(rows)<2:return ''
    name=lambda b:SHORT.get(b['slug'],re.sub(r'\s*পিএলসি$','',b['name_bn']))
    loc=lambda b:LOC.get(b['slug'],name(b)+' ব্যাংকে')
    gen=lambda b:GEN.get(b['slug'],name(b)+' ব্যাংকের')
    val=lambda n:format(float(n),'g')
    def values(attribute):
        return [(b,b['facts'][attribute]) for b in rows if b['facts'].get(attribute) and not b['facts'][attribute]['stale'] and b['facts'][attribute]['value_num'] is not None]
    def amount(fact):return fact['value_num']
    def span(low,high,unit):return f'{val(low)} {unit}' if low==high else f'{val(low)} থেকে {val(high)} {unit}'
    annual=values('annual_fee');low=amount(annual[0][1]);high=amount(annual[-1][1])
    choice=result['choice'];title=NETWORKS.get(choice['network'],choice['network'])+' '+TIERS.get(choice['tier'],choice['tier'])
    parts=[f'{title} কার্ডের বার্ষিক ফির তথ্য আছে {len(rows)}টি ব্যাংকের।']
    if low!=high:parts.append(f'ফি {span(low,high,"টাকা")}। অর্থাৎ বছরে {val(high-low)} টাকার পার্থক্য।')
    else:parts.append(f'সবগুলোর প্রকাশিত বার্ষিক ফি একই, {val(low)} টাকা।')
    groups={}
    for bank,fact in annual[:3]:groups.setdefault(amount(fact),[]).append(bank)
    for i,(fee,banks) in enumerate(groups.items()):
        if i==0:
            parts.append(f'এর মধ্যে {join_bn(gen(b) for b in banks)} বার্ষিক ফি সবচেয়ে কম, {val(fee)} টাকা।')
        else:parts.append(f'এরপর {join_bn(gen(b) for b in banks)} প্রকাশিত বার্ষিক ফি {val(fee)} টাকা।')
    waivers=[]
    for bank in rows:
        fact=bank['facts'].get('fee_waiver_rule')
        if not fact or fact['stale']:continue
        found=re.search(r'(\d+)\s+transactions',fact['value_text']+' '+fact['condition'],re.I)
        if found:waivers.append(f'{loc(bank)} বছরে {found[1]}টি লেনদেন করলে বার্ষিক ফি মওকুফ হয়।')
    parts.extend(waivers[:2])
    interest=values('interest_rate')
    if interest:
        rates=[amount(f) for _,f in interest]
        parts.append(f'প্রকাশিত সুদের হার বছরে {span(min(rates),max(rates),"%")}।')
    late=sorted(values('late_fee'),key=lambda item:amount(item[1]))
    if len(late)==1:parts.append(f'বিলম্ব ফির যে তথ্য আছে, তাতে {gen(late[0][0])} ফি {val(amount(late[0][1]))} টাকা।')
    elif late:
        if amount(late[0][1])==amount(late[-1][1]):parts.append(f'প্রকাশিত বিলম্ব ফি একই, {val(amount(late[0][1]))} টাকা।')
        else:parts.append(f'বিলম্ব ফি {loc(late[0][0])} {val(amount(late[0][1]))} টাকা, আর {loc(late[-1][0])} {val(amount(late[-1][1]))} টাকা।')
    # Cash fees combine percentages, currency floors and ATM context. A taka
    # floor must never become a percentage or be presented as the total fee.
    cash=values('cash_advance_fee');cash_groups={}
    from ilma_api.export_seed import quote_numbers
    for bank,fact in cash:
        text=fact['condition']+' '+fact['value_text']
        pct=re.search(r'(\d+(?:\.\d+)?)\s*%',text)
        money=re.search(r'(BDT|Tk\.?|USD|US\$)\s*([\d,]+(?:\.\d+)?)',text,re.I)
        scope='own_atm' if bank['slug']=='ebl' and re.search(r'at EBL ATM',text,re.I) else ''
        if pct and money and re.search('whichever is higher',text,re.I):
            from decimal import Decimal
            percent=pct[1];currency='ডলার' if money[1].upper() in {'USD','US$'} else 'টাকা';floor=money[2].replace(',','')
            if {Decimal(percent),Decimal(floor)}<=quote_numbers(fact.get('quote','')):
                wording=f'{percent}% অথবা {floor} {currency}, যেটি বেশি'
            else:wording=f'{val(amount(fact))} '+('%' if '%' in fact['value_text'] else 'টাকা')+'। অতিরিক্ত শর্ত মূল সূত্রে আছে'
        elif fact['unit']=='bdt':wording=f'{val(amount(fact))} টাকা'
        elif '%' in fact['value_text']:wording=f'{val(amount(fact))}%'
        else:continue
        cash_groups.setdefault((wording,scope),[]).append(bank)
    if cash_groups:parts.append('নগদ তোলার ফি আলাদা করে খেয়াল করা দরকার।')
    for (wording,scope),banks in cash_groups.items():
        subject=join_bn(gen(b) for b in banks)
        parts.append(f'{subject} '+('নিজস্ব এটিএমে ' if scope else '')+f'নগদ তোলার ফি {wording}।')
    if interest or late:parts.append('সুদ কখন প্রযোজ্য হবে, তা বিল পরিশোধ ও নগদ তোলার শর্তের ওপর নির্ভর করে।')
    foreign=values('foreign_currency_markup')
    if foreign:
        numbers=[amount(f) for _,f in foreign]
        parts.append(('সব ব্যাংকের প্রকাশিত ' if len(foreign)==len(rows) else 'যেসব তথ্য আছে, তাতে ')+'বিদেশি মুদ্রার মার্কআপ '+span(min(numbers),max(numbers),'%')+'। কোন মুদ্রায় প্রযোজ্য, তা মূল সূত্রে আছে।')
    for bank in rows:
        fact=bank['facts'].get('supplementary_card_fee')
        if not fact or fact['stale']:continue
        condition=fact.get('condition_bn','')
        count=2 if 'প্রথম দুটি' in condition else 1 if 'প্রথম অতিরিক্ত কার্ড বিনামূল্যে' in condition else 0
        if count:
            parts.append(f'{loc(bank)} '+('প্রথম দুটি অতিরিক্ত কার্ড বিনামূল্যে।' if count==2 else 'প্রথম অতিরিক্ত কার্ডটি বিনামূল্যে।'));break
    strong=sum(b['status']['code']=='strong' for b in rows)
    parts.append(f'প্রকাশিত তথ্যে এই তালিকার {strong}টি ব্যাংকের অবস্থা ভালো।')
    for code,description in [('no_data','অবস্থা যাচাই হয়নি'),('high','ঝুঁকির শ্রেণি বেশি'),('watch','অবস্থায় সতর্কতার লক্ষণ আছে')]:
        banks=[b for b in rows if b['status']['code']==code]
        if banks:parts.append(join_bn(gen(b) for b in banks)+' '+description+'।')
    if any(re.search(r'15\s*%\s*vat',f.get('condition','')+' '+f.get('quote',''),re.I) for b in rows for f in b['facts'].values() if f and not f['stale']):parts.append('কিছু প্রকাশিত ফির সঙ্গে 15% ভ্যাট যোগ হওয়ার শর্ত আছে।')
    stale=sum(bool(b.get('facts',{}).get('annual_fee') and b['facts']['annual_fee']['stale']) for b in result['rows'])
    if stale:parts.append(f'আরও {stale}টি ব্যাংকের তথ্য পুরনো, তাই এই তুলনায় রাখা হয়নি।')
    parts.append('এটি প্রকাশিত খরচের তুলনা, ব্যাংকের র‌্যাঙ্কিং নয়। প্রতিটি সংখ্যার সূত্র স্ক্রিনে আছে।')
    return pronounce(' '.join(parts),'bn')

def selected_narration(result,language='bn'):
    """Read the chosen cost only, including every fresh bank and its conditions."""
    if language!='bn' or result['choice']['product_type']!='card':return ''
    from ilma_api.card_explanation import build
    article=build(result)
    parts=[article['title_bn'].replace(' · ',' কার্ডের ')+'।']
    for section in article['sections']:
        # Never read stale prices as current comparison facts.
        if section['id']=='stale':
            parts.append(f"{len(section['paragraphs'])}টি ব্যাংকের এই খরচের তথ্য পুরনো, তাই বর্তমান তুলনায় রাখা হয়নি।")
        elif section['id']=='coverage':
            attribute=result['choice']['attribute']
            fresh=[b for b in result['rows'] if b.get('facts',{}).get(attribute) and not b['facts'][attribute]['stale']]
            parts.append(f'এই খরচের পুরনো নয় এমন প্রকাশিত তথ্য আছে {len(fresh)}টি ব্যাংকের। প্রতিটি ব্যাংকের অঙ্ক, শর্ত ও তারিখ বলছি।')
            facts=[b['facts'][attribute] for b in fresh]
            if attribute!='cash_advance_fee' and facts and all(f.get('value_num') is not None for f in facts) and len({f['unit'] for f in facts})==1:
                unit='টাকা' if facts[0]['unit']=='bdt' else '%' if facts[0]['unit']=='pct_year' or '%' in facts[0]['value_text'] else ''
                if unit:
                    numbers=[float(f['value_num']) for f in facts];lo=min(numbers);hi=max(numbers)
                    parts.append(('প্রকাশিত অঙ্ক একই, '+format(lo,'g') if lo==hi else 'প্রকাশিত অঙ্ক '+format(lo,'g')+' থেকে '+format(hi,'g'))+' '+unit+'।')
            strong=sum(b['status']['code']=='strong' for b in fresh)
            parts.append(f'এই তালিকার {strong}টি ব্যাংকের আর্থিক অবস্থার শ্রেণি ভালো। এটি কার্ডের মানের রায় নয়।')
        else:parts.extend(p['text_bn'] for p in section['paragraphs'])
    return '\n\n'.join(pronounce(part,'bn') for part in parts)

def manifest(directory=None):
    directory=Path(directory or DIRECTORY)
    try:data=json.loads((directory/'manifest.json').read_text())
    except (OSError,ValueError):return {'version':1,'clips':{}}
    return data if isinstance(data,dict) and isinstance(data.get('clips'),dict) else {'version':1,'clips':{}}

def readout(result,language='bn',directory=None):
    attribute=result['choice'].get('attribute');directory=Path(directory or DIRECTORY)
    item=manifest(directory)['clips'].get(key(result['choice']['network'],result['choice']['tier'],attribute))
    if item and item.get('approved_exact_text') is True:
        text=item.get('text','')
    else:text=selected_narration(result,language) if attribute else narration(result,language)
    if language!='bn' or not text:return {'audio_url':None,'text':''}
    # Approved verbatim scripts are never passed through pronunciation rewriting.
    # A changed data set or unreviewed/tampered file must not play stale speech.
    if item and item.get('reviewed') is True and item.get('reviewer') and item.get('reviewed_at') and item.get('text_sha256')==hashlib.sha256(text.encode()).hexdigest() and re.fullmatch(r'bn/card-[a-z0-9-]+\.mp3',item.get('file','')):
        path=directory/item['file']
        if verified_audio(path,item.get('audio_sha256')):
            return {'audio_url':'/static/audio/services/'+item['file']+'?v='+item['audio_sha256'][:16],'text':text}
    return {'audio_url':None,'text':text}
