"""Fixed-example loan facts and saved audio lookup. No runtime provider requests."""
import hashlib,json,math,re
from pathlib import Path
from ilma_api.loan_catalog import DEFAULTS,LABELS,emi,fee_amount
from ilma_api.service_clips import SHORT,LOC,join_bn
ROOT=Path(__file__).resolve().parents[2]
CLIP_KEYS={'home_loan':'loan:bn:home','auto_loan':'loan:bn:auto','personal_loan':'loan:bn:personal','loan_against_fdr':'loan:bn:fdr'}
def facts(result):
    kind=result['choice']['product_type'];amount,years=DEFAULTS[kind];values=[]
    for b in result['rows']:
        rate=(b.get('rate') or {}).get('value_num')
        item=dict(bank=b['slug'],name_bn=SHORT.get(b['slug'],b['name_bn']),status=b['status']['code'],declared_rate=rate,rate_min=(b.get('rate_min') or {}).get('value_num'),rate_max=(b.get('rate_max') or {}).get('value_num'),margin_min=b.get('margin_min'),margin_max=b.get('margin_max'),fdr_rate=(b.get('fdr_12m_rate') or {}).get('value_num'))
        if rate is not None:
            payment=emi(amount,rate,years*12);item.update(monthly=math.floor(payment+.5),interest=math.floor(payment*years*12-amount+.5),total=math.floor(payment*years*12+.5))
        if item['fdr_rate'] is not None:
            for bound in ['min','max']:
                addition=item['margin_'+bound]
                if addition is not None:
                    effective=item['fdr_rate']+addition;item['example_rate_'+bound]=effective;item['example_monthly_'+bound]=math.floor(emi(amount,effective,years*12)+.5)
        item['fees']=[dict(attribute=f['attribute'],percent=f['value_num'],is_maximum=f.get('is_maximum',False),cap_bdt=f['cap_bdt'],slab_min=f['slab_min'],slab_max=f['slab_max'],vat_percent=f['vat_percent'],example_fee=fee_amount(f,amount) if f['attribute']=='processing_fee' else None) for f in b['fees']]
        values.append(item)
    priced=sorted([v for v in values if v.get('monthly') is not None],key=lambda b:b['monthly'])
    spread=dict(monthly_difference=priced[-1]['monthly']-priced[0]['monthly'],total_difference=priced[-1]['total']-priced[0]['total']) if priced else {}
    return dict(product_type=kind,amount=amount,amount_lakh=amount/100000,years=years,banks=values,spread=spread)
def narration(pack):
    from ilma_api.voice_numbers import pronounce
    kind=pack['product_type'];amount=pack['amount'];years=pack['years'];banks=pack['banks'];priced=sorted([b for b in banks if b.get('monthly') is not None],key=lambda b:b['monthly'])
    if not banks:return ''
    parts=[f"{amount/100000:g} লাখ টাকার {LABELS[kind][0]} {years} বছরে শোধ করার উদাহরণ।"]
    if priced:
        low,high=priced[0]['monthly'],priced[-1]['monthly'];parts.append(f"{len(priced)}টি ব্যাংকের ঘোষিত হারে মাসিক কিস্তি {low} থেকে {high} টাকা।")
        for payment in dict.fromkeys([low,high]):
            group=[b for b in priced if b['monthly']==payment];parts.append(join_bn(LOC.get(b['bank'],b['name_bn']+'তে') for b in group)+f" কিস্তি {payment} টাকা।")
        if high>low:parts.append(f"মাসে পার্থক্য {high-low} টাকা; পুরো মেয়াদে কিস্তির পার্থক্য প্রায় {priced[-1]['total']-priced[0]['total']} টাকা।")
    if kind=='loan_against_fdr':
        for b in banks:
            lo,hi=b['margin_min'],b['margin_max']
            if lo is not None or hi is not None:parts.append(LOC.get(b['bank'],b['name_bn']+'তে')+' এফডিআরের হারের চেয়ে '+(f'{lo:g} থেকে {hi:g} শতাংশ বেশি।' if lo is not None and hi is not None and lo!=hi else f'{lo:g} শতাংশ বেশি।' if lo==hi else f'কমপক্ষে {lo:g} শতাংশ বেশি।' if hi is None else f'সর্বোচ্চ {hi:g} শতাংশ বেশি।'))
    parts.append('এগুলো ব্যাংকের ঘোষিত হার ধরে হিসাব; আপনার আয়, জামানত ও লেনদেনের ইতিহাস দেখে ব্যাংক চূড়ান্ত হার ও কিস্তি ঠিক করে।')
    fees=[(b,f) for b in banks for f in b['fees'] if f['attribute']=='processing_fee' and f['example_fee'] is not None]
    if fees:
        grouped={}
        for b,f in fees:grouped.setdefault((f['percent'],f['cap_bdt'],f['example_fee'],f.get('is_maximum',False)),[]).append(b)
        for (pct,cap,value,maximum),members in grouped.items():parts.append(join_bn(LOC.get(b['bank'],b['name_bn']+'তে') for b in members)+f' একবারের প্রসেসিং ফি '+('সর্বোচ্চ ' if maximum else '')+f'{pct:g} শতাংশ'+(f', সর্বোচ্চ {cap:g} টাকা' if cap else '')+'; এই উদাহরণে '+('সর্বোচ্চ ' if maximum else '')+f'{value:g} টাকা।')
    early={}
    for b in banks:
        for f in b['fees']:
            if f['attribute']=='early_settlement_fee':early.setdefault((f['percent'],f.get('is_maximum',False)),[]).append(b)
    for (pct,maximum),members in early.items():parts.append(join_bn(LOC.get(b['bank'],b['name_bn']+'তে') for b in members)+' মেয়াদের আগে পুরো শোধ করলে বাকি ঋণের ওপর '+('সর্বোচ্চ ' if maximum else '')+f'{pct:g} শতাংশ ফি।')
    low=sum(b['status']=='strong' for b in banks)
    if low:parts.append(f'প্রকাশিত তথ্য অনুযায়ী {low}টি ব্যাংকের ঝুঁকি কম।')
    notrated=[b['name_bn'] for b in banks if b['status']=='no_data']
    if notrated:parts.append(join_bn(notrated)+' এখনো মূল্যায়ন করা হয়নি।')
    if any(f['vat_percent'] for b in banks for f in b['fees']):parts.append('প্রযোজ্য ফির সঙ্গে পনেরো শতাংশ ভ্যাট যোগ হয়।')
    return pronounce(' '.join(parts),'bn')
def readout(result):
    pack=facts(result);source=hashlib.sha256(json.dumps({'rows':result['rows'],'defaults':result['defaults']},sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest();text=narration(pack);kind=pack['product_type'];item={};url=None
    try:item=json.loads((ROOT/'static/audio/services/manifest.json').read_text()).get('clips',{}).get(CLIP_KEYS[kind],{})
    except (OSError,ValueError):pass
    if item.get('approved_exact_text') and item.get('source_sha256')==source and hashlib.sha256(item.get('text','').encode()).hexdigest()==item.get('text_sha256'):
        text=item['text'];file=item.get('file','').removeprefix('static/audio/services/')
        expected='bn/loan_'+CLIP_KEYS[kind].removeprefix('loan:bn:')+'.mp3'
        if item.get('reviewed') and file==expected and item.get('example_amount')==pack['amount'] and item.get('example_years')==pack['years']:
            path=ROOT/'static/audio/services'/file
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item.get('audio_sha256'):url='/static/audio/services/'+file+'?v='+item['audio_sha256'][:16]
    return dict(text=text,audio_url=url,source_sha256=source,example_amount=pack['amount'],example_years=pack['years'])
