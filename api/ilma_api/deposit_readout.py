"""Fixed-default source-bound deposit narration; no runtime provider requests."""
import hashlib,json,math,re
from pathlib import Path
from ilma_api.audio_integrity import verified_audio
from ilma_api.deposit_catalog import select,fv,AUDIENCES
from ilma_api.service_clips import SHORT,LOC,join_bn
ROOT=Path(__file__).resolve().parents[2]
PLANS=[('fdr',m,'all') for m in [1,3,6,12,24,36]]+[('dps',m,'all') for m in [12,36,60]]+[('savings',12,'all'),('dps',36,'women'),('fdr',36,'senior'),('dps',48,'student_child'),('savings',12,'nrb')]
def key(p,m,a):return f'{p}-{m}-{a.replace("_","-")}'
def facts(result,p,m,a):
    amount=5000 if p=='dps' else 100000;out=[]
    for b in result['catalog_banks']:
        options=select(b['rates'],p,m,a,amount);priority=min((r.get('display_priority',0) for r in b['rates'] if r['product_type']==p and r['audience']==a),default=0);row=next((r for r in options if r['variant']!='scheme' and r.get('display_priority',0)==priority),None)
        if not row:continue
        if p=='dps' and ((row['min_monthly_installment'] and amount<row['min_monthly_installment']) or (row['installment_multiple'] and amount%row['installment_multiple'])):continue
        rate=row['value_num'];paid=amount*m if p=='dps' else amount;earnings=fv(amount,rate,m)-paid if p=='dps' else amount*rate*(12 if p=='savings' else m)/1200;total=paid+earnings
        out.append(dict(bank=b['slug'],name_bn=SHORT.get(b['slug'],b['name_bn']),status=b['status']['code'],rate=rate,interest=math.floor(earnings+.5+1e-8),maturity=math.floor(total+.5+1e-8),offer_id=row['offer_id'],variants=[dict(product=r['product'],rate=r['value_num']) for r in options if r['offer_id']!=row['offer_id']]))
    out.sort(key=lambda b:-b['interest'])
    schemes=[dict(bank=b['slug'],name_bn=SHORT.get(b['slug'],b['name_bn']),status=b['status']['code'],product=r['product'],rate=r['value_num']) for b in result['catalog_banks'] for r in select(b['rates'],p,m,a,amount) if r['variant']=='scheme']
    return dict(key=key(p,m,a),product_type=p,months=m,amount=amount,audience=a,banks=out,schemes=schemes,insurance=result['insurance'])
def narration(pack):
    from ilma_api.voice_numbers import pronounce
    p=pack['product_type'];m=pack['months'];a=pack['audience'];banks=pack['banks'];amount=pack['amount']
    if not banks:return ''
    term=f'{m//12} বছর' if m%12==0 else f'{m} মাস'
    parts=[(AUDIENCES[a][0]+'। ' if a!='all' else '')+(f'মাসে {amount} টাকা {term} ডিপিএসে জমার উদাহরণ।' if p=='dps' else f'{amount} টাকার '+(f'{term} এফডিআরের' if p=='fdr' else 'সঞ্চয়ী হিসাবের এক বছরের')+' উদাহরণ।')]
    grouped={}
    for b in banks:grouped.setdefault((b['rate'],b['interest'],b['maturity'],b['status'] if b['status'] in ['no_data','high'] else 'rated'),[]).append(b)
    for (rate,interest,maturity,status),members in grouped.items():
        line=join_bn(LOC.get(b['bank'],b['name_bn']+'তে') for b in members)+f" প্রকাশিত বার্ষিক হার {rate:g} শতাংশে আনুমানিক সুদ {interest} টাকা"
        if p=='dps':line+=f", মোট জমা {amount*m} টাকা থেকে মেয়াদ শেষে আনুমানিক {maturity} টাকা"
        if status=='no_data':line+='; এই ব্যাংক এখনো মূল্যায়ন করা হয়নি, বেশি হার মানেই ঝুঁকি কম নয়'
        elif status=='high':line+='; এই ব্যাংকের ঝুঁকি বেশি, বেশি হার মানেই নিরাপদ নয়'
        parts.append(line+'।')
    for b in banks:
        for variant in b['variants']:
            if 'extra value' in variant['product'].lower():parts.append(LOC.get(b['bank'],b['name_bn']+'তে')+f" এক্সট্রা ভ্যালু এফডিআর আলাদা পণ্য, এর প্রকাশিত হার {variant['rate']:g} শতাংশ।")
    if p=='dps':parts.append('ব্যাংকের হিসাবের নিয়ম আলাদা হতে পারে।')
    rule=pack['insurance']
    if rule:parts.append(f"আমানত সুরক্ষার নিয়ম অনুযায়ী কিছু শর্ত মেনে প্রতি ব্যাংকে একজন জমাকারীর যোগ্য আমানত {rule['limit_bdt']} টাকা পর্যন্ত ফেরত পাওয়ার নিয়ম আছে। একই ব্যাংকের সব হিসাব একত্রে গণ্য।")
    parts.append('হিসাব আনুমানিক, কর ও আবগারি শুল্ক কাটার আগে।')
    return pronounce(' '.join(parts),'bn')
def readouts(result, plans=None):
    try:clips=json.loads((ROOT/'static/audio/services/manifest.json').read_text()).get('clips',{})
    except (OSError,ValueError):clips={}
    source=hashlib.sha256(json.dumps({'banks':result['catalog_banks'],'insurance':result['insurance']},sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest();out={}
    for p,m,a in PLANS if plans is None else plans:
        pack=facts(result,p,m,a);k=pack['key'];text=narration(pack);item=clips.get('deposit:bn:'+k,clips.get(k,{}));url=None
        if not text:continue
        if item.get('approved_exact_text') and item.get('source_sha256')==source and hashlib.sha256(item.get('text','').encode()).hexdigest()==item.get('text_sha256'):
            text=item['text'];file=item.get('file','').removeprefix('static/audio/services/')
            if item.get('reviewed') and re.fullmatch(r'bn/deposit_[a-z0-9-]+\.mp3',file):
                path=ROOT/'static/audio/services'/file
                if verified_audio(path,item.get('audio_sha256')):url='/static/audio/services/'+file+'?v='+item['audio_sha256'][:16];text=item['text']
        from ilma_api.deposit_references import references
        out[k]=dict(references=references(result,p,m,a),text=text,audio_url=url,source_sha256=source,example_amount=pack['amount'],example_months=m,product_type=p,audience=a)
    return out
