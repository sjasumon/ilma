"""Bank-screen presentation derived from sourced records; risk rules are unchanged."""
import csv,hashlib,json,re
from pathlib import Path
from sqlalchemy import inspect
from ilma_api.rules.reasons import to_bn_digits
from ilma_api.db import BankProfile,ServiceOffer,Event
ROOT=Path(__file__).resolve().parents[2]
RISK={'strong':('ঝুঁকি কম','Low risk'),'watch':('ঝুঁকি মাঝারি','Medium risk'),'high':('ঝুঁকি বেশি','High risk'),'no_data':('মূল্যায়ন করা হয়নি','Not rated')}
def rating_meaning(agency,grade):
    grade=re.sub(r'[^A-Z]','',grade.upper())
    rows=list(csv.DictReader((ROOT/'seed/rating_scale_bn.csv').open()))
    row=next((r for r in rows if r['agency'].casefold()==agency.casefold() and r['grade']==grade),None)
    return {'meaning_bn':row['meaning_bn'],'meaning_en':row['meaning_en']} if row else {}
def source_label(title,year=None):
    match=re.search(r'20\d{2}',title or '');year=match[0] if match else str(year or '')[:4]
    return to_bn_digits((('বার্ষিক প্রতিবেদন ' if re.search(r'annual|বার্ষিক',title or '',re.I) else 'রেটিং প্রতিবেদন ' if re.search(r'rating',title or '',re.I) else 'মূল নথি ')+year).strip())
def eligible_award(slug,code,rows=None):
    if code!='strong':return None
    if rows is None:rows=list(csv.DictReader((ROOT/'seed/bank_awards.csv').open()))
    allowed=[r for r in rows if r['bank_slug']==slug and str(r['awarder_confirmed']).lower()=='true' and str(r['likely_paid']).lower()=='false' and re.match(r'^https://',r['source_url'])]
    return max(allowed,key=lambda r:int(r['year'])) if allowed else None
def enrich(db,card):
    from ilma_api.extra_data import items
    from ilma_api.voice_numbers import pronounce
    bank=card['institution'];code=card['status']['code'];bn,en=RISK[code]
    card['status'].update(label_bn=bn,label_en=en)
    card['reasons']=[r for r in card['reasons'] if r.get('source_url')]
    from ilma_api.service_clips import GEN
    for r in card['reasons']:r['source_label_bn']=GEN.get(bank['slug'],bank['name_bn'].replace('পিএলসি','').strip()+'-এর')+' '+source_label(r.get('source_title'),r.get('published_at'))
    for r in card['ratings']:r.update(rating_meaning(r['agency'],r['long_term']))
    profile=[]
    if inspect(db.connection()).has_table('bank_profile'):profile=db.query(BankProfile).filter_by(bank_id=bank['id'],field='founded_year').order_by(BankProfile.as_of.desc()).all()
    card['founded_year']=profile[0].value if profile and re.fullmatch(r'\d{4}',profile[0].value) else None
    card['founding_source']={'source_url':profile[0].source_url,'quote':profile[0].quote,'page':profile[0].page} if card['founded_year'] else None
    card['award']=eligible_award(bank['slug'],code)
    card['section_counts']={'health':len(card['figures']),'rating':len(card['ratings']),'history':card['incident_count'],
      'news':db.query(Event).filter_by(institution_id=bank['id'],type='other',official=False).count(),
      'services':db.query(ServiceOffer).filter_by(institution_id=bank['id'],hidden=False).count(),
      'announcements':len(items(db,'announcement',bank['id'])),'reports':len(items(db,'report',bank['id'])),'bb-notices':len(items(db,'bank_notice',bank['id']))}
    parts=[bank['name_bn']+'।']
    if card['founded_year']:parts.append('প্রতিষ্ঠা '+card['founded_year']+' সালে।')
    parts.append(('প্রকাশিত তথ্য অনুযায়ী ঝুঁকি '+{'strong':'কম','watch':'মাঝারি','high':'বেশি'}[code]+'।') if code!='no_data' else 'এই ব্যাংকের ঝুঁকি এখনো মূল্যায়ন করা হয়নি।')
    if code=='high':parts=[parts[-1],*parts[:-1]]
    for reason in card['reasons']:
        if reason['rule'] in {'P3','W3','H5'}:continue # The rating is spoken once below.
        line=re.sub(r'\([০-৯0-9]{4}\)','',reason['text_bn']).replace('+','ও')
        if reason['rule'] in {'P1','H3','W2'}:line+=' এই মূলধন লোকসান সামলানোর জন্য রাখা হয়।'
        if reason['rule']=='P2':
            npl=next((f for f in card['figures'] if f['metric']=='npl_ratio'),None)
            if npl:line+=f" অর্থাৎ প্রতি একশো টাকার ঋণে {npl['value']*100:g} টাকা সময়মতো ফেরত আসছে না।"
        parts.append(line)

    if card['ratings']:
        r=card['ratings'][0];grade=r['long_term'].replace('+',' প্লাস').replace('-',' মাইনাস')
        parts.append(r['agency']+' রেটিং '+grade+'। '+(r.get('meaning_bn','')+'। ' if r.get('meaning_bn') else '')+'এটি আমানতের নিশ্চয়তা নয়।')
    if card['insurance'].get('covered') and card['insurance'].get('limit_bdt')==200000:
        parts.append('প্রতি ব্যাংকে একজন জমাকারীর দুই লাখ টাকা পর্যন্ত আমানত সুরক্ষার নিয়ম আছে, শর্ত প্রযোজ্য।')
    if card['award']:parts.append('স্বীকৃতি: '+card['award']['title_bn']+'।')
    parts.append('সব সংখ্যার সূত্র স্ক্রিনে আছে।')
    raw=' '.join(parts).translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    from ilma_api.voice_numbers import bangla_number
    raw=re.sub(r'(-\d+(?:\.\d+)?)\s*%',lambda m:bangla_number(m[1])+' শতাংশ',raw)
    text=pronounce(raw,'bn');key=bank['slug'];clip={}
    frozen={'bank':bank,'risk':code,'founding':card['founded_year'],'reasons':card['reasons'],'figures':sorted(card['figures'],key=lambda f:f['metric']),'ratings':card['ratings'],'insurance':card['insurance'],'award':card['award']}
    source_sha=hashlib.sha256(json.dumps(frozen,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
    try:clip=json.loads((ROOT/'static/audio/bank/manifest.json').read_text()).get('clips',{}).get(key,{})
    except (OSError,ValueError):pass
    if clip.get('approved_exact_text') and clip.get('source_sha256')==source_sha and clip.get('text_sha256')==hashlib.sha256(clip.get('text','').encode()).hexdigest():text=clip['text']
    url=None;filename=clip.get('file','')
    if clip.get('reviewed') and (not clip.get('approved_exact_text') or clip.get('source_sha256')==source_sha) and re.fullmatch(r'bn/[a-z0-9-]+\.mp3',filename) and clip.get('text_sha256')==hashlib.sha256(text.encode()).hexdigest():
        path=ROOT/'static/audio/bank'/filename
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==clip.get('audio_sha256'):url='/static/audio/bank/'+filename+'?v='+clip['audio_sha256'][:16]
    card['readout']={'text':text,'audio_url':url,'source_sha256':source_sha}
    return card

def publication_label(row):
    topic=row.topic;title=row.title
    if re.search(r'annual report',title,re.I):topic='annual_report'
    elif re.search(r'election.*chairman|chairman.*elect',title,re.I):topic='chairman_election'
    elif re.search(r'director.*share|share.*director',title,re.I):topic='director_share'
    mapping={r['topic']:r for r in csv.DictReader((ROOT/'seed/announcement_type_bn.csv').open())}
    item=mapping.get(topic,mapping['company_notice'])
    bn,en=item['label_bn'],item['label_en']
    if row.kind=='report':
        quarter=next((n for n,p in [(1,r'first|1st|q1'),(2,r'second|2nd|q2'),(3,r'third|3rd|q3')] if re.search(p,title,re.I)),None)
        if re.search(r'annual',title,re.I):bn='বার্ষিক প্রতিবেদন';en='Annual report'
        elif re.search(r'half.year|six.month|semi.annual',title,re.I):bn='অর্ধবার্ষিক';en='Half-year report'
        elif quarter:bn={1:'প্রথম প্রান্তিক',2:'দ্বিতীয় প্রান্তিক',3:'তৃতীয় প্রান্তিক'}[quarter];en=f'Quarter {quarter}'
        if row.report_year:bn+=' '+str(row.report_year);en+=' '+str(row.report_year)
        if re.search(r'unaudited',title,re.I):bn+=' (অনিরীক্ষিত)';en+=' (unaudited)'
    if row.kind=='bank_notice':bn='বাংলাদেশ ব্যাংকের নোটিশ';en='Bangladesh Bank notice'
    return dict(type_label_bn=to_bn_digits(bn),type_label_en=en,filter_group=item['group'])
