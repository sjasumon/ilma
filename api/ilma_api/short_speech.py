"""Brief sourced narration; complete facts and qualifications stay on screen."""
import re
from datetime import date
from ilma_api.db import Institution,Fact,Rating,ServiceOffer,InsuranceRule
from ilma_api.rules.reasons import format_number

QUESTIONS={
 'BANK':('বিস্তারিত, না সেবা?','Details, or services?'),
 'DETAIL':('হিসাব, না আগের ঘটনা?','Figures, or past events?'),
 'FIGURES':('সেবা, না অন্য ব্যাংক?','Services, or another bank?'),
 'HISTORY':('সেবা, না অন্য ব্যাংক?','Services, or another bank?'),
 'SERVICES':('এফডিআর, ডিপিএস, কার্ড, না গৃহঋণ?','FDR, DPS, card, or home loan?'),
 'SERVICE':('তুলনা করবেন?','Compare?'),
 'COMPARE':('প্রথম ব্যাংকের অবস্থা শুনবেন?','Hear the first bank’s condition?'),
 'NEXT':('অন্য ব্যাংক, না শেষ?','Another bank, or finish?'),
 'ASK_BANK':('ব্যাংকের নাম বলুন।','Say a bank name.'),
 'WATCH_CONFIRM':('নজরে রাখবেন? সতর্কবার্তা চালু নেই।','Watch it? Notifications are unavailable.')}

def short_name(db,id,bn):
 bank=db.get(Institution,id) if id else None
 if not bank:return ''
 names=[a.alias for a in bank.aliases if bool(re.search('[\u0980-\u09ff]',a.alias))==bn]
 full=bank.name_bn if bn else bank.name_en
 name=min(names,key=len,default=re.sub(r'\s+(?:PLC|পিএলসি)\.?$','',full,flags=re.I))
 # Include the noun for a standalone Bangla brand alias to aid pronunciation.
 if bn and name=='ব্র্যাক':name+=' ব্যাংক'
 return name

def compact_fact(db,item,bn):
 rule=item.get('source',{}).get('rule')
 qualitative={'P1':('মূলধন ন্যূনতমের বেশি।','Capital exceeds the minimum.'),'P2':('খেলাপি ঋণ কম।','Bad loans are low.'),'P4':('মুনাফা হয়েছে।','The bank reported a profit.'),'W2':('মূলধন ন্যূনতমের কাছাকাছি।','Capital is close to the minimum.'),'H3':('মূলধন ন্যূনতমের নিচে।','Capital is below the minimum.')}
 if rule in qualitative:return qualitative[rule][0 if bn else 1]
 key=item['fact_id'];row=db.get(Fact,key)
 if row:
  labels={'npl_ratio':('খেলাপি ঋণ','Bad loans'),'crar':('মূলধন','Capital'),'net_profit':('নিট মুনাফা','Net profit'),'provision_shortfall':('প্রভিশন ঘাটতি','Provision shortfall')}
  label=labels.get(row.metric,('তথ্য','Figure'))[0 if bn else 1]
  if row.metric=='net_profit' and row.value<0:label='নিট লোকসান' if bn else 'Net loss'
  value=format_number(abs(row.value)*100,bn=bn)+'%' if row.unit=='ratio' else format_number(abs(row.value)/10000000,bn=bn)+(' কোটি টাকা' if bn else ' crore taka')
  calculated=('হিসাব করা ' if bn else 'Calculated ') if row.basis.endswith('_calculated') else ''
  return f'{calculated}{label}: {value}।' if bn else f'{calculated}{label}: {value}.'
 rating=db.get(Rating,key)
 if rating:
  old=bool(rating.valid_to and rating.valid_to<date.today())
  return ('পুরনো ' if bn and old else 'Old ' if old else '')+('রেটিং: ' if bn else 'Rating: ')+rating.long_term+('।' if bn else '.')
 text=item['text_bn' if bn else 'text_en']
 # Never truncate an allegation into an apparent finding.
 if item.get('unconfirmed'):return 'ঘটনার খবর নিশ্চিত নয়।' if bn else 'The incident report is unconfirmed.'
 if len(text.split())<=10:return text
 return 'বিস্তারিত তথ্য পর্দায় আছে।' if bn else 'The details are on screen.'

def parts(db,facts,conversation,question,tool,action=None):
 bn=conversation.get('language','bn')=='bn';state=conversation['state'];id=conversation.get('institution_id');lines=[]
 if action and action['type'] in {'stop','open_report','open_proof'}:return []
 if facts:
  if tool=='bank_summary':
   status=next((f for f in facts if f.get('status')),None)
   if status:lines.append(short_name(db,id,bn)+': '+status['status']['label_bn' if bn else 'label_en']+('।' if bn else '.'))
   reason=next((f for f in facts if not f['fact_id'].startswith(('status:','insurance:','script:'))),None)
   if reason:lines.append(compact_fact(db,reason,bn))
  elif tool=='bank_reasons':lines.extend(compact_fact(db,f,bn) for f in facts[:2])
  elif tool=='services_overview' and any(f.get('counts') for f in facts):lines.append('সেবার তথ্য আছে।' if bn else 'Service information is available.')
  elif tool=='insurance':
   bank=db.get(Institution,id) if id else None;rule=db.get(InsuranceRule,bank.type if bank else 'bank')
   if rule and rule.covered and rule.limit_bdt and 'per depositor per member bank' in rule.text_en:
    lines.append(f'জনপ্রতি সদস্য ব্যাংকে যোগ্য আমানত {format_number(rule.limit_bdt,bn=bn)} টাকা পর্যন্ত; সব হিসাব মিলে, শর্ত প্রযোজ্য।' if bn else f'Eligible deposits: up to {format_number(rule.limit_bdt)} taka per depositor per member bank, accounts combined. Conditions apply.')
   else:lines.append(compact_fact(db,facts[0],bn))
  elif tool in {'service_detail','service_compare'}:
   row=db.get(ServiceOffer,facts[0]['fact_id'])
   if row and row.value_num is not None:
    label=('আনুমানিক মুনাফা' if bn else 'Provisional profit') if row.basis=='islamic' else ('বার্ষিক হার' if bn else 'Annual rate') if row.unit=='pct_year' else ('ফি' if bn else 'Fee')
    value=format_number(row.value_num,bn=bn)+('%' if row.unit=='pct_year' else ' টাকা' if bn and row.unit=='bdt' else ' taka' if row.unit=='bdt' else ' '+row.unit)
    term=(format_number(row.tenor_months,bn=bn)+(' মাস: ' if bn else ' months: ')) if row.tenor_months else ''
    name=short_name(db,row.institution_id,bn)+': ' if tool=='service_compare' else ''
    lines.append(name+term+label+' '+value+('।' if bn else '.')+(' পুরনো তথ্য।' if bn and (row.stale or (date.today()-row.doc_date).days>365) else ' Old data.' if row.stale or (date.today()-row.doc_date).days>365 else ''))
   else:lines.append(compact_fact(db,facts[0],bn))
  else:lines.append(compact_fact(db,facts[0],bn))
 if question:lines.append(question)
 return [line for line in lines if line][:3]
