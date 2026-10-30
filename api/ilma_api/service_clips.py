"""Deterministic comparison narration and reviewed, saved clips; no runtime TTS."""
import hashlib,json,re
from pathlib import Path
from ilma_api.voice_numbers import pronounce
from ilma_api.card_catalog import numeric,NETWORKS,TIERS
ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'static/audio/services'
SHORT={'ebl':'ইস্টার্ন ব্যাংক','bracbank':'ব্র্যাক ব্যাংক','citybank':'সিটি ব্যাংক','dutchbangl':'ডাচ্ বাংলা','bankasia':'ব্যাংক এশিয়া','nccbank':'এনসিসি','primebank':'প্রাইম','mtb':'এমটিবি','sbacbank':'সাউথবাংলা'}

def key(network,tier):
    def slug(value):return re.sub('[^a-z0-9]+','-',value.casefold()).strip('-')
    return 'bn:card-'+slug(network)+'-'+slug(tier)

def narration(result,language='bn'):
    if result['choice']['product_type']!='card' or language!='bn':return ''
    rows=[b for b in result['rows'] if b.get('facts',{}).get('annual_fee') and not b['facts']['annual_fee']['stale'] and b['facts']['annual_fee']['value_num'] is not None]
    rows.sort(key=lambda b:(b['facts']['annual_fee']['value_num'],b['id']))
    if len(rows)<2:return ''
    name=lambda b:SHORT.get(b['slug'],re.sub(r'\s*পিএলসি$','',b['name_bn']))
    val=lambda n:format(float(n),'g')
    def values(attribute):return [(b,b['facts'][attribute]['value_num']) for b in rows if b['facts'].get(attribute) and not b['facts'][attribute]['stale'] and b['facts'][attribute]['value_num'] is not None and (attribute!='cash_advance_fee' or b['facts'][attribute]['unit']=='bdt')]
    annual=values('annual_fee');low=annual[0][1];high=annual[-1][1]
    choice=result['choice'];title=NETWORKS.get(choice['network'],choice['network'])+' '+TIERS.get(choice['tier'],choice['tier'])
    parts=[f'{title} কার্ড দেয় {len(rows)}টি ব্যাংক। বার্ষিক ফি {val(low)} থেকে {val(high)} টাকা; পার্থক্য {val(high-low)} টাকা। কম {name(rows[0])} {val(low)}, তারপর {name(rows[1])} {val(annual[1][1])} টাকা।']
    at=lambda b:{'ebl':'ইস্টার্ন ব্যাংকে','bracbank':'ব্র্যাক ব্যাংকে','primebank':'প্রাইমে','nccbank':'এনসিসিতে','bankasia':'ব্যাংক এশিয়ায়','mtb':'এমটিবিতে','sbacbank':'সাউথবাংলায়'}.get(b['slug'],name(b)+'-এ')
    waivers=[]
    for b in rows:
        f=b['facts'].get('fee_waiver_rule')
        if not f or f['stale']:continue
        found=re.search(r'(\d+)\s+transactions',f['value_text']+' '+f['condition'],re.I)
        if found:waivers.append(f"{at(b)} {found[1]}টি")
    if waivers:parts.append('বছরে '+', '.join(waivers[:2])+' লেনদেনে ফি মওকুফ।')
    interest=values('interest_rate');late=sorted(values('late_fee'),key=lambda v:v[1]);cash=values('cash_advance_fee')
    costs=[]
    if interest:costs.append(f"সুদ বছরে {val(min(v for _,v in interest))} থেকে {val(max(v for _,v in interest))}%।")
    if late:costs.append(f"বিলম্ব ফি {name(late[0][0])} {val(late[0][1])}, {name(late[-1][0])} {val(late[-1][1])} টাকা।")
    if cash:costs.append(f"নগদ তোলার টাকায় ফি {val(min(v for _,v in cash))} থেকে {val(max(v for _,v in cash))}; শতাংশের শর্ত সূত্রে।")
    if costs:parts.append(' '.join(costs)+' সময়মতো পুরো বিল দিলে সুদ নেই; দেরির খরচ বার্ষিক ফি ছাড়াতে পারে।')
    foreign=values('foreign_currency_markup');extra=[]
    if foreign:
        nums={v for _,v in foreign}
        extra.append(('সব ব্যাংকেই ' if len(foreign)==len(rows) and len(nums)==1 else 'প্রকাশিত ')+'বিদেশি মুদ্রার মার্কআপ '+(val(next(iter(nums))) if len(nums)==1 else val(min(nums))+' থেকে '+val(max(nums)))+'%।')
    free=[name(b) for b in rows if b['facts'].get('supplementary_card_fee') and not b['facts']['supplementary_card_fee']['stale'] and ('প্রথম অতিরিক্ত কার্ড বিনামূল্যে' in b['facts']['supplementary_card_fee'].get('condition_bn','') or 'প্রথম দুটি' in b['facts']['supplementary_card_fee'].get('condition_bn',''))]
    if free:extra.append(f'{free[0]}-এ প্রথম অতিরিক্ত কার্ড বিনামূল্যে।')
    if extra:parts.append(' '.join(extra))
    strong=sum(b['status']['code']=='strong' for b in rows);unknown=[name(b) for b in rows if b['status']['code']=='no_data'];highrisk=[name(b) for b in rows if b['status']['code']=='high'];watch=[name(b) for b in rows if b['status']['code']=='watch']
    status=f'{strong}টির অবস্থা ভালো।'
    if unknown:status+=' '+', '.join(unknown)+'র অবস্থা যাচাই হয়নি।'
    if highrisk:status+=' '+', '.join(highrisk)+'র ঝুঁকি বেশি।'
    if watch:status+=' '+', '.join(watch)+'তে সতর্কতার লক্ষণ।'
    parts.append(status)
    # VAT is conditional on actual selected source rows; never invent a charge.
    if any(re.search(r'15\s*%\s*vat',f.get('condition','')+' '+f.get('quote',''),re.I) for b in rows for f in b['facts'].values() if f and not f['stale']):parts.append('ফির সাথে 15% ভ্যাট যোগ হয়।')
    parts.append('প্রকাশিত তালিকা; পছন্দ নির্ভর করে ব্যবহারের ওপর। সংখ্যার সূত্র স্ক্রিনে আছে।')
    stale=sum(bool(b.get('facts',{}).get('annual_fee') and b['facts']['annual_fee']['stale']) for b in result['rows'])
    if stale:parts.append(f'{stale}টি ব্যাংকের তথ্য পুরনো, তাই বাদ।')
    text=' '.join(parts)
    text=re.sub(r'(\d+(?:\.\d+)?) থেকে \1(?=[% ।;])',r'\1',text)
    return pronounce(text,'bn')

def manifest(directory=None):
    directory=Path(directory or DIRECTORY)
    try:data=json.loads((directory/'manifest.json').read_text())
    except (OSError,ValueError):return {'version':1,'clips':{}}
    return data if isinstance(data,dict) and isinstance(data.get('clips'),dict) else {'version':1,'clips':{}}

def readout(result,language='bn',directory=None):
    text=narration(result,language);directory=Path(directory or DIRECTORY)
    if not text:return {'audio_url':None,'text':text}
    item=manifest(directory)['clips'].get(key(result['choice']['network'],result['choice']['tier']))
    # A changed data set or unreviewed/tampered file must not play stale speech.
    if item and item.get('reviewed') is True and item.get('reviewer') and item.get('reviewed_at') and item.get('text_sha256')==hashlib.sha256(text.encode()).hexdigest() and re.fullmatch(r'bn/card-[a-z0-9-]+\.mp3',item.get('file','')):
        path=directory/item['file']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item.get('audio_sha256'):
            return {'audio_url':'/static/audio/services/'+item['file'],'text':text}
    return {'audio_url':None,'text':text}
