"""Narrow five-year DPS comparison: code owns selection, money and validation."""
import asyncio,json,re,time
from datetime import date
from decimal import Decimal,ROUND_HALF_UP,localcontext
import httpx
from ilma_api import settings
from ilma_api.db import ServiceOffer,Institution
from ilma_api.service_terms import terms
from ilma_api.report_card import get_institution_report_card
from ilma_api.database_tasks import call
from ilma_api.voice_numbers import pronounce,NUMBERS,SCALES

QUESTION='আপনি মাসে কত টাকা রাখতে চান?'
SHORT={'primebank':'প্রাইম','nccbank':'এনসিসি','bracbank':'ব্র্যাক','ebl':'ইস্টার্ন ব্যাংক','citybank':'সিটি ব্যাংক','sbacbank':'সাউথবাংলা','bankasia':'ব্যাংক এশিয়া','mtb':'এমটিবি'}

def rate(row):
    if row.value_num is not None:return Decimal(row.value_num)
    value=row.value_text.strip().rstrip('%').strip()
    return Decimal(value) if re.fullmatch(r'\d+(?:\.\d+)?',value) else None

def maturity(annual_percent,monthly=1000,months=60):
    """Illustration: end-month deposits, monthly compounding, zero upfront."""
    with localcontext() as context:
        context.prec=40;r=Decimal(annual_percent)/1200
        value=Decimal(monthly)*((1+r)**months-1)/r if r else Decimal(monthly)*months
        return int(value.quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def inventory(db):
    rows=db.query(ServiceOffer).filter_by(product_type='dps',attribute='rate',hidden=False).order_by(ServiceOffer.institution_id,ServiceOffer.offer_id).all()
    output=[];cards={}
    for row in rows:
        value=rate(row)
        if value is None or row.unit!='pct_year':continue
        bank=db.get(Institution,row.institution_id)
        if bank.id not in cards:cards[bank.id]=get_institution_report_card(db,bank.id) or {}
        card=cards[bank.id]
        output.append({'offer_id':row.offer_id,'bank_id':bank.id,'slug':bank.slug,'bank_bn':bank.name_bn,
          'name_bn':SHORT.get(bank.slug,re.sub(r'\s*পিএলসি$','',bank.name_bn)),
          'status':(card.get('status') or {}).get('code','no_data'),
          'rate_percent':format(value.normalize(),'f'),'terms':terms(row),'date':str(row.doc_date),
          'basis':row.basis,'stale':row.stale or (date.today()-row.doc_date).days>365,
          'future':row.doc_date>date.today(),'product':row.product,'condition':row.condition,
          'source_url':row.source_url,'page':row.page,'quote':row.quote})
    return output

def build(db):
    records=inventory(db);banks={row['bank_id'] for row in records}
    base={'ready':False,'inventory':records,'bank_count':len(banks)}
    if len(banks)<3:return {**base,'reason':'fewer_than_three_dps_banks'}
    current=[r for r in records if not r['stale'] and not r['future'] and r['basis']=='conventional']
    def five(row):
        value=row['terms'];return 60 in value['tenor_options'] if value['tenor_options'] else value['tenor_min_months'] is not None and value['tenor_min_months']<=60<=value['tenor_max_months']
    strongest={}
    for row in current:
        if row['status']!='strong' or not five(row):continue
        old=strongest.get(row['bank_id'])
        # Highest published five-year rate per bank; equal-rate products use a
        # stable offer ID. Equal-rate banks use bank ID, not a quality judgement.
        if old is None or (-Decimal(row['rate_percent']),row['offer_id'])<(-Decimal(old['rate_percent']),old['offer_id']):strongest[row['bank_id']]=row
    top=sorted(strongest.values(),key=lambda r:(-Decimal(r['rate_percent']),r['bank_id']))[:3]
    if len(top)<3:return {**base,'reason':'fewer_than_three_strong_five_year_rates'}
    warnings={};highest=Decimal(top[0]['rate_percent'])
    for row in current:
        if row['status']=='strong' or Decimal(row['rate_percent'])<=highest:continue
        old=warnings.get(row['bank_id'])
        if old is None or (not five(row),-Decimal(row['rate_percent']),row['offer_id'])<(not five(old),-Decimal(old['rate_percent']),old['offer_id']):warnings[row['bank_id']]=row
    selected=[];conditions=[]
    for row in top:
        item={**row,'maturity_estimate_bdt':maturity(row['rate_percent'])};selected.append(item)
        if re.search(r'initial\s+amount',row['quote'],re.I):
            amount=re.search(r'\b(\d{1,3}(?:,\d{3})+)\b',row['quote'])
            if amount:conditions.append({'bank_id':row['bank_id'],'name_bn':row['name_bn'],'initial_example_bdt':int(amount[1].replace(',','')),'not_in_illustration':True})
    flagged=[]
    for row in sorted(warnings.values(),key=lambda r:(-Decimal(r['rate_percent']),r['bank_id'])):
        value=row['terms'];months=60 if five(row) else value['tenor_min_months']
        flagged.append({**row,'comparison_months':months,'matches_five_years':five(row)})
    return {**base,'ready':True,'top':selected,'flagged':flagged,'conditions':conditions,'monthly_bdt':1000,'months':60,'years':5,
      'calculation':'Monthly compounding; payments at month end; no upfront amount; before tax/fees. Illustration, not a bank maturity quote or eligibility promise.',
      'tie_break':'Equal rates use stable bank ID; excluded equal-rate banks are not worse.',
      'cutoff_ties':[r for r in strongest.values() if r['bank_id'] not in {x['bank_id'] for x in top} and Decimal(r['rate_percent'])==Decimal(top[-1]['rate_percent'])]}

def spoken_facts(data):
    facts=[{'id':'example','text_bn':'মাসশেষে ১০০০ জমিয়ে ৫ বছরে মাসিক চক্রবৃদ্ধিতে কর-ফি কাটার আগে আনুমানিক হিসাব।'}]
    for row in data['top']:
        facts.append({'id':row['offer_id'],'text_bn':f"ভালো অবস্থার {row['name_bn']}: {row['rate_percent']}%, আনুমানিক {row['maturity_estimate_bdt']} টাকা।"})
    for row in data['conditions']:
        facts.append({'id':'initial:'+str(row['bank_id']),'text_bn':f"{row['name_bn']}-এর উৎসের উদাহরণে আগাম {row['initial_example_bdt']} টাকা আছে; এই হিসাবে তা বাদ।"})
    for row in data['flagged']:
        label='অযাচাইকৃত' if row['status']=='no_data' else 'উচ্চ ঝুঁকি' if row['status']=='high' else 'সতর্কতার লক্ষণ'
        months=row['comparison_months'];term='মেয়াদের তথ্য নেই' if months is None else f'{months//12} বছর' if months%12==0 else f'{months} মাস'
        facts.append({'id':'flag:'+row['offer_id'],'text_bn':f"{row['name_bn']}: {row['rate_percent']}%, {term}; অবস্থা {label}।"+('৫ বছরের তথ্য নেই।' if not row['matches_five_years'] else '')})
    return facts

def template(data):
    rows=[f"{r['name_bn']} {r['rate_percent']}%—{r['maturity_estimate_bdt']}" for r in data['top']]
    text='মাসশেষে ১০০০, ৫ বছরে মাসিক চক্রবৃদ্ধিতে কর-ফি কাটার আগে আনুমানিক: ভালো অবস্থার '+', '.join(rows)+' টাকা।'
    for row in data['conditions']:text+=f" {row['name_bn']}র উদাহরণের আগাম {row['initial_example_bdt']} ধরা হয়নি।"
    for row in data['flagged']:
        label='অযাচাইকৃত' if row['status']=='no_data' else 'উচ্চ ঝুঁকি' if row['status']=='high' else 'সতর্কতার লক্ষণ'
        if row['comparison_months'] is None:
            text+=f" {row['name_bn']}র {row['rate_percent']}%, মেয়াদ অজানা, অবস্থা {label}।";continue
        amount=row['comparison_months']//12;unit='বছরের' if row['comparison_months']%12==0 else 'মাসের'
        if unit=='মাসের':amount=row['comparison_months']
        text+=f" {row['name_bn']}র {row['rate_percent']}% {amount} {unit}; "+('৫ বছরের তথ্য নেই, ' if not row['matches_five_years'] else '')+label+'।'
    return text+' '+QUESTION

def quantities(text):
    value=text.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    value=re.sub(r'(?<=\d),(?=\d)','',value)
    return [Decimal(n) for n in re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?',value)]

def validate(answer,data):
    """Conservative number/name whitelist plus completeness and bank binding."""
    if not answer.endswith(QUESTION):return 'closing_question'
    if len(pronounce(answer,'bn').split())>=60:return 'word_limit'
    if re.search('[A-Za-z]',answer):return 'non_bangla'
    if re.search(r'নিশ্চিত লাভ|নিরাপদ|সেরা|সবচেয়ে ভালো|রাখুন|বিনিয়োগ করুন',answer):return 'advice_or_guarantee'
    allowed={number for fact in spoken_facts(data) for number in quantities(fact['text_bn'])}
    if any(number not in allowed for number in quantities(answer)):return 'unknown_number'
    words=lambda text:re.findall(r'[\u0980-\u09ff]+',re.sub(r'[0-9০-৯]+',' ',text))
    for word in words(answer):
        if word in NUMBERS or word in SCALES or re.match(r'^(?:এক|দুই|তিন|চার|পাঁচ|ছয়|সাত|আট|নয়|দশ)(?:বছর|মাস|হাজার|লাখ)',word):return 'quantities_must_use_digits_before_tts'
    # Restrict free wording as well as named banks: a new bank or unsupported
    # claim cannot hide behind numbers that happen to occur in another row.
    text=answer
    names={r['name_bn'] for r in data['top']+data['flagged']}
    for name in sorted(names,key=len,reverse=True):text=text.replace(name+'ের',' ').replace(name+'র',' ').replace(name,' ')
    lexicon=set(words(template(data)+' '.join(f['text_bn'] for f in spoken_facts(data))))|set('এর ব্যাংক ব্যাংকের হার হারে সুদ সুদের শতাংশ শতাংশে তুলনায় তুলনা হিসেবে মোট পাবেন হয় হবে হতে পারে এবং আর তবে এখানে এই হিসাবে হিসাব একই তিনটি ব্যাংকের মধ্যে দেখুন আছে মাসের শেষে মাসে জমালে জমিয়ে ফি কর আগে কাটার বাদ বাদে উৎসে তথ্য যাচাই হয়নি শুধুমাত্র আপনার জন্য পরিমাণ আনুমানিকভাবে'.split())
    if any(word not in lexicon for word in words(text)):return 'unknown_bank_or_claim'
    normalized=answer.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    normalized=re.sub(r'(?<=\d),(?=\d)','',normalized)
    positions=sorted((match.start(),match.end(),name) for name in names for match in re.finditer(re.escape(name),normalized))
    def spans(name):
        return [normalized[end:positions[i+1][0] if i+1<len(positions) else len(normalized)] for i,(_,end,current) in enumerate(positions) if current==name]
    def rate_in(text,value):return any(Decimal(number)==Decimal(value) for number in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*(?:%|শতাংশ)',text))
    for row in data['top']:
        if not any(rate_in(span,row['rate_percent']) and Decimal(row['maturity_estimate_bdt']) in quantities(span) for span in spans(row['name_bn'])):return 'missing_or_swapped_bank_fact'
    for row in data['flagged']:
        label='অযাচাইকৃত' if row['status']=='no_data' else 'উচ্চ ঝুঁকি' if row['status']=='high' else 'সতর্কতার লক্ষণ'
        amount=None if row['comparison_months'] is None else Decimal(row['comparison_months'])/12 if row['comparison_months']%12==0 else Decimal(row['comparison_months'])
        if not any(rate_in(span,row['rate_percent']) and label in span and (amount is None or amount in quantities(span)) and (row['matches_five_years'] or 'নেই' in span and 'তথ্য' in span) for span in spans(row['name_bn'])):return 'missing_risk_or_term_flag'
    for row in data['conditions']:
        if not any(Decimal(row['initial_example_bdt']) in quantities(span) and 'আগাম' in span and ('বাদ' in span or 'ধরা হয়নি' in span) and 'উদাহরণ' in span for span in spans(row['name_bn'])):return 'missing_initial_deposit_caveat'
    if not (Decimal(1000) in quantities(answer) and re.search(r'5\s*বছর|60\s*মাস',normalized) and ('মাসশেষে' in answer or 'মাসের শেষে' in answer) and 'মাসিক' in answer and 'চক্রবৃদ্ধি' in answer and 'কর' in answer and 'ফি' in answer and 'আগে' in answer and 'আনুমানিক' in answer and ('ভালো অবস্থার' in answer or 'অবস্থা ভালো' in answer)):return 'missing_calculation_scope'
    return None

SYSTEM='''You write only a DPS comparison from the supplied fact list. Use ALL facts
and NOTHING ELSE, in simple spoken Bangla, fewer than 60 words AFTER numbers are
spoken aloud. Combine the repeated good-status label once. Keep each bank's rate
and estimated maturity together. Never recommend a bank or promise a return.
Keep the upfront-example caveat and the unverified bank's different tenor/no
five-year-data warning. Write ALL quantities as digits, not spelled-out number
words; code will pronounce them. End exactly with the last fact, the question.
Do not mention source dates or add background information. Return JSON answer.'''

async def compose(data,trace,client=None):
    started=time.monotonic();fallback=template(data)
    if validate(fallback,data):raise ValueError('The complete fixed DPS template does not fit the response constraints')
    if not settings.META_MODEL_API_KEY and client is None:return fallback,'unconfigured'
    from ilma_api.http_clients import shared
    http=client or shared();owned=http is None
    if owned:http=httpx.AsyncClient(follow_redirects=False)
    facts=spoken_facts(data)+[{'id':'next_question','text_bn':QUESTION}]
    body={'model':settings.MUSE_SPARK_MODEL,'temperature':.2,'reasoning_effort':'minimal','max_tokens':1600,
      'response_format':{'type':'json_schema','json_schema':{'name':'dps_comparison','strict':True,'schema':{'type':'object','additionalProperties':False,'properties':{'answer':{'type':'string'}},'required':['answer']}}},
      'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(facts,ensure_ascii=False)}]}
    reason=None
    try:
        response=await asyncio.wait_for(http.post(settings.MUSE_SPARK_API_URL,headers={'Authorization':'Bearer '+settings.META_MODEL_API_KEY},json=body,timeout=httpx.Timeout(settings.HUMAN_MODEL_TIMEOUT_SECONDS,connect=2)),settings.HUMAN_MODEL_TIMEOUT_SECONDS)
        if response.status_code!=200:reason='http_'+str(response.status_code);answer=fallback
        else:
            answer=json.loads(response.json()['choices'][0]['message']['content'])['answer'].strip()
            reason=validate(answer,data)
            if reason:answer=fallback
    except (httpx.HTTPError,asyncio.TimeoutError,ValueError,KeyError,TypeError,IndexError):reason='provider_or_schema';answer=fallback
    finally:
        if owned:await http.aclose()
    trace.append({'stage':'PLAN','model':settings.MUSE_SPARK_MODEL,'ms':round((time.monotonic()-started)*1000),'status':'fallback' if reason else 'ok','reason':reason or 'dps_fact_list_only'})
    return answer,reason

async def run_question(text,context,banks,db,watch_identity=None,client=None,device_hash=None,on_sentence=None):
    from ilma_api.human_agent import controls,render,finish
    from ilma_api.human_memory import load
    from ilma_api.voice_agent import Conversation
    from ilma_api.voice_pipeline import consume_question
    started=time.monotonic();initial=context.conversation or Conversation()
    id,memory=await call(db,lambda session:load(session,initial.conversation_token))
    c=Conversation.model_validate(memory.get('conversation') or initial.model_dump()).model_copy(update={'institution_id':None,'product':'dps','tenor':60,'basis':'conventional','network':None,'tier':None,'language':'bn'})
    memory['protocol']=2;trace=[{'stage':'RESOLVER','model':'code','ms':0,'status':'ok','reason':'best_dps_comparison'}]
    data=await call(db,build)
    if not data['ready']:
        answer=controls('compare',c,'ডিপিএস তুলনার জন্য যথেষ্ট প্রকাশিত তথ্য নেই।','',['repeat','end'])
        result=render(answer,c,[],trace,'template');result['dps_data_ready']=False;result['reason']=data['reason']
        return await finish(result,'[redacted]',id,memory,db,started)
    await call(db,lambda session:consume_question(session,watch_identity or device_hash or 'dps-comparison'))
    spoken,reason=await compose(data,trace,client)
    facts=[]
    for row in data['top']+data['flagged']:
        fid='dps-compare:'+row['offer_id']
        line=next(f['text_bn'] for f in spoken_facts(data) if f['id']==row['offer_id'] or f['id']=='flag:'+row['offer_id'])
        from ilma_api.rules.reasons import format_date
        extra=' '.join(f['text_bn'] for f in spoken_facts(data) if f['id']=='initial:'+str(row['bank_id']))
        card=('৫ বছরের ডিপিএস। ' if row in data['top'] else '')+line+' '+extra+' হারতালিকা '+format_date(date.fromisoformat(row['date']),bn=True)
        facts.append({'fact_id':fid,'institution_id':row['bank_id'],'kind':'service','text_bn':card,'text_en':row['product'],'values':{'rate_percent':row['rate_percent'],'tenor_months':60 if row in data['top'] else row['comparison_months'],'monthly_example_bdt':1000,'maturity_estimate_bdt':row.get('maturity_estimate_bdt'),'status':row['status'],'calculation':data['calculation']},'source':{'source_url':row['source_url'],'source_title':row['product'],'published_at':row['date'],'page':row['page'],'quote':row['quote']}})
    answer=controls('compare',c,spoken[:-len(QUESTION)].rstrip(),QUESTION,['repeat','end']).model_copy(update={'used_fact_ids':[f['fact_id'] for f in facts]})
    result=render(answer,c,facts,trace,'template' if reason else 'code')
    result.update(dps_data_ready=True,dps_comparison_facts=spoken_facts(data),dps_comparison_data={key:data[key] for key in ['top','flagged','conditions','monthly_bdt','months','years','calculation','tie_break','cutoff_ties']},dps_model_fallback_reason=reason)
    return await finish(result,'[redacted]',id,memory,db,started)
