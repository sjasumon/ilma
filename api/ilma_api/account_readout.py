"""Frozen account examples; code facts and saved recordings only."""
import hashlib,json,math,re
from pathlib import Path
from ilma_api.account_catalog import calculate,yearly
from ilma_api.deposit_catalog import AUDIENCES
from ilma_api.service_clips import SHORT,LOC,join_bn
ROOT=Path(__file__).resolve().parents[2]
PLANS=[('savings','all'),('debit','all'),('other','all')]+[('savings',a) for a in ['women','senior','student_child','nrb']]
def facts(result,item,audience):
    out=[]
    for b in result['banks']:
        info=dict(bank=b['slug'],name_bn=SHORT.get(b['slug'],b['name_bn']),status=b['status']['code'])
        if item=='savings':
            c=calculate(b,100000,True,True,audience);off=calculate(b,100000,True,False,audience);both=calculate(b,100000,False,False,audience)
            if c['interest'] is None and c['maintenance'] is None:continue
            info.update(interest=c['interest'],rate=c['rate']['value_num'] if c['rate'] else None,maintenance_half_year=c['maintenance']['value_num'] if c['maintenance'] else None,maintenance_year=yearly(c['maintenance']) if c['maintenance'] else None,debit_year=yearly(c['debit']) if c['debit'] else None,sms_year=yearly(c['sms']) if c['sms'] else None,net=c['net'],net_sms_off=off['net'],net_both_off=both['net'],maintenance_source=c['maintenance']['offer_id'] if c['maintenance'] else None)
        elif item=='debit':
            card=b['debit_main']
            if not card:continue
            info.update(card=card['product'],annual_base=card['value_num'],annual_year=yearly(card),vat_percent=card['vat_percent'],replacement=b['debit_replacement']['value_num'] if b['debit_replacement'] else None,variants=[dict(product=r['product'],annual_base=r['value_num']) for r in b['debit_variants']])
        else:
            if not b['other']:continue
            info['fees']=[dict(attribute=r['attribute'],value=r['value_num'],periods_per_year=r['periods_per_year'],vat_percent=r['vat_percent'],vat_included=r['vat_included'],yearly=yearly(r)) for r in b['other']]
        out.append(info)
    return dict(key=item+'-'+audience.replace('_','-'),item=item,audience=audience,balance=100000,card=True,sms=True,banks=out)

def check_draft(text,pack):
    """Check numeric drafts before pronunciation; manual wording review still required."""
    plain=text.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'));allowed=[1,2,6,12]
    def collect(value):
        if isinstance(value,dict):
            for v in value.values():collect(v)
        elif isinstance(value,list):
            for v in value:collect(v)
        elif isinstance(value,(int,float)) and not isinstance(value,bool):allowed.append(value)
    collect(pack)
    numbers=[float(n.replace(',','')) for n in re.findall(r'-?\d[\d,]*(?:\.\d+)?',plain)]
    if any(not any(abs(n-v)<.000001 for v in allowed) for n in numbers):return False
    if any(w in plain.casefold() for w in ['null','নাল','নেট নাল','তথ্য নেই','প্রকাশিত নয়','যাচাই হচ্ছে','গ্যারান্টি','নিশ্চিত']):return False
    for sentence in re.split(r'[।!?]',plain):
        if 'রক্ষণাবেক্ষণ' not in sentence:continue
        for bank in pack['banks']:
            if bank['name_bn'] in sentence and bank.get('maintenance_half_year') is None:return False
    return True

def narration(pack):
    from ilma_api.voice_numbers import pronounce
    parts=[];kind=pack['item'];banks=pack['banks']
    if not banks:return ''
    if kind=='savings':
        parts.append(('সঞ্চয়ী হিসাবে এক লাখ টাকা ব্যালান্স ধরে হিসাব।' if pack['audience']=='all' else AUDIENCES[pack['audience']][0]+' সঞ্চয়ী হিসাবে এক লাখ টাকা ব্যালান্স ধরে হিসাব।'))
        for b in banks:
            if b['interest'] is not None:
                line=LOC.get(b['bank'],b['name_bn']+'তে')+f" প্রকাশিত বার্ষিক হার {b['rate']:g} শতাংশে সুদ {b['interest']:g} টাকা"
                if b['status']=='no_data':line+='; এই ব্যাংক এখনো মূল্যায়ন করা হয়নি'
                elif b['status']=='high':line+='; এই ব্যাংকের ঝুঁকি বেশি'
                parts.append(line+'।')
            if b['maintenance_year'] is not None:parts.append(LOC.get(b['bank'],b['name_bn']+'তে')+f" এই ব্যালান্সে রক্ষণাবেক্ষণ ফি ছয় মাসে {b['maintenance_half_year']:g} টাকা, প্রযোজ্য ভ্যাটসহ বছরে {b['maintenance_year']:g} টাকা।")
            if b['net_sms_off'] is not None:parts.append('এসএমএস অ্যালার্ট বাদ দিয়ে, ডেবিট কার্ডসহ এই ব্যাংকে বছরে '+(f"খরচ সুদের চেয়ে {-b['net_sms_off']:g} টাকা বেশি।" if b['net_sms_off']<0 else f"হাতে থাকে প্রায় {b['net_sms_off']:g} টাকা।"))
            if b['net_both_off'] is not None:parts.append(f"ডেবিট কার্ড ও এসএমএস দুটোই বাদ দিলে হাতে থাকে প্রায় {b['net_both_off']:g} টাকা।")
        parts.append('হাতে থাকে তখনই দেখানো হয়, যখন সুদ ও নির্বাচিত সব ফির প্রযোজ্য অঙ্ক জানা আছে।')
    elif kind=='debit':
        for b in banks:
            parts.append(LOC.get(b['bank'],b['name_bn']+'তে')+f" সাধারণ ডেবিট কার্ডের প্রকাশিত বার্ষিক ফি {b['annual_base']:g} টাকা"+(f", {b['vat_percent']:g} শতাংশ ভ্যাটসহ {b['annual_year']:g} টাকা" if b['vat_percent'] else '')+'।')
            if b['replacement'] is not None:parts.append(f"এই কার্ড বদলানোর ফি {b['replacement']:g} টাকা।")
        parts.append('অন্য কার্ডের ধরন ও শর্ত আলাদা; স্ক্রিনে প্রতিটি পণ্যের সূত্র আছে।')
    else:
        for attribute,label in [('closing_fee','হিসাব বন্ধের ফি'),('atm_other_bank_fee','অন্য ব্যাংকের এটিএমে প্রতি বার টাকা তোলার ফি'),('sms_alert_fee','ছয় মাসের এসএমএস ফি')]:
            groups={}
            for b in banks:
                for f in b['fees']:
                    if f['attribute']==attribute:groups.setdefault((f['value'],f['vat_percent'],f['vat_included']),[]).append(b)
            for (value,vat,included),members in groups.items():
                risk='; '+join_bn(b['name_bn']+' এখনো মূল্যায়ন করা হয়নি' if b['status']=='no_data' else b['name_bn']+'র ঝুঁকি বেশি' for b in members if b['status'] in ['no_data','high']) if any(b['status'] in ['no_data','high'] for b in members) else ''
                parts.append(join_bn(LOC.get(b['bank'],b['name_bn']+'তে') for b in members)+f' {label} {value:g} টাকা'+(f', সঙ্গে {vat:g} শতাংশ ভ্যাট' if vat and not included else ', ভ্যাটসহ' if included else '')+risk+'।')
    parts.append('সুদ কর কাটার আগে। শুধু উৎসে উল্লেখ থাকা ফির সঙ্গে প্রযোজ্য ভ্যাট যোগ করা হয়েছে। এটি তথ্য, পরামর্শ নয়।')
    return pronounce(' '.join(parts),'bn')
def readouts(result):
    source=hashlib.sha256(json.dumps(result['banks'],sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
    try:clips=json.loads((ROOT/'static/audio/accounts/manifest.json').read_text()).get('clips',{})
    except (OSError,ValueError):clips={}
    out={}
    for item,a in PLANS:
        pack=facts(result,item,a);text=narration(pack);k=pack['key'];saved=clips.get(k,{});url=None
        if not text:continue
        if saved.get('approved_exact_text') and saved.get('source_sha256')==source and hashlib.sha256(saved.get('text','').encode()).hexdigest()==saved.get('text_sha256'):
            file=saved.get('file','')
            if saved.get('reviewed') and re.fullmatch(r'bn/[a-z0-9-]+\.mp3',file):
                path=ROOT/'static/audio/accounts'/file
                if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==saved.get('audio_sha256'):text=saved['text'];url='/static/audio/accounts/'+file+'?v='+saved['audio_sha256'][:16]
        out[k]=dict(text=text,audio_url=url,source_sha256=source,example_balance=100000)
    return out
