"""Narrow best-rate comparison (five-year DPS, one-year FDR): code owns selection, money and validation."""
import asyncio,json,random,re,time
from datetime import date
from decimal import Decimal,ROUND_HALF_UP,localcontext
import httpx
from ilma_api import settings
from ilma_api.db import ServiceOffer,Institution
from ilma_api.service_terms import terms
from ilma_api.report_card import get_institution_report_card
from ilma_api.database_tasks import call
from ilma_api.voice_numbers import pronounce,NUMBERS,SCALES

# Never ask for an amount: the closing question offers detail, not a calculation.
QUESTION='আপনি কোনটার বিস্তারিত শুনবেন?'
QUESTIONS=(QUESTION,QUESTION,QUESTION)
# Each product's comparison term; only DPS gets the monthly-saving illustration.
PRODUCTS={'dps':{'word':'ডিপিএস','months':60},'fdr':{'word':'এফডিআর','months':12}}
# Full spoken names (never "প্রাইম" or "এনসিসি" alone).
SPOKEN={'primebank':'প্রাইম ব্যাংক','nccbank':'এনসিসি ব্যাংক','bracbank':'ব্র্যাক ব্যাংক','ebl':'ইস্টার্ন ব্যাংক','citybank':'সিটি ব্যাংক','sbacbank':'সাউথ বাংলা ব্যাংক','bankasia':'ব্যাংক এশিয়া','mtb':'মিউচুয়াল ট্রাস্ট ব্যাংক','dbbl':'ডাচ বাংলা ব্যাংক','pubalibank':'পূবালী ব্যাংক','nbl':'ন্যাশনাল ব্যাংক','islamibank':'ইসলামী ব্যাংক'}

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

def inventory(db,product='dps'):
    rows=db.query(ServiceOffer).filter_by(product_type=product,attribute='rate',hidden=False).order_by(ServiceOffer.institution_id,ServiceOffer.offer_id).all()
    output=[];cards={}
    for row in rows:
        value=rate(row)
        if value is None or row.unit!='pct_year':continue
        bank=db.get(Institution,row.institution_id)
        if bank.id not in cards:cards[bank.id]=get_institution_report_card(db,bank.id) or {}
        card=cards[bank.id]
        output.append({'offer_id':row.offer_id,'bank_id':bank.id,'slug':bank.slug,'bank_bn':bank.name_bn,
          'name_bn':SPOKEN.get(bank.slug,re.sub(r'\s*(?:পিএলসি|লিমিটেড)$','',bank.name_bn)),
          'name_en':re.sub(r'\s*(?:PLC\.?|Limited|Ltd\.?)$','',bank.name_en or bank.slug,flags=re.I),
          'status':(card.get('status') or {}).get('code','no_data'),
          'rate_percent':format(value.normalize(),'f'),'terms':terms(row),'date':str(row.doc_date),
          'basis':row.basis,'stale':row.stale or (date.today()-row.doc_date).days>365,
          'future':row.doc_date>date.today(),'product':row.product,'condition':row.condition,
          'source_url':row.source_url,'page':row.page,'quote':row.quote})
    return output

def build(db,product='dps'):
    spec=PRODUCTS[product];months=spec['months']
    records=inventory(db,product);banks={row['bank_id'] for row in records}
    base={'ready':False,'inventory':records,'bank_count':len(banks),'product':product,'word':spec['word']}
    if len(banks)<3:return {**base,'reason':f'fewer_than_three_{product}_banks'}
    current=[r for r in records if not r['stale'] and not r['future'] and r['basis']=='conventional']
    def five(row):
        value=row['terms'];return months in value['tenor_options'] if value['tenor_options'] else value['tenor_min_months'] is not None and value['tenor_min_months']<=months<=value['tenor_max_months']
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
        item={**row,'maturity_estimate_bdt':maturity(row['rate_percent'])} if product=='dps' else dict(row);selected.append(item)
        if product=='dps' and re.search(r'initial\s+amount',row['quote'],re.I):
            amount=re.search(r'\b(\d{1,3}(?:,\d{3})+)\b',row['quote'])
            if amount:conditions.append({'bank_id':row['bank_id'],'name_bn':row['name_bn'],'initial_example_bdt':int(amount[1].replace(',','')),'not_in_illustration':True})
    flagged=[]
    for row in sorted(warnings.values(),key=lambda r:(-Decimal(r['rate_percent']),r['bank_id'])):
        value=row['terms'];row_months=months if five(row) else value['tenor_min_months']
        flagged.append({**row,'comparison_months':row_months,'matches_five_years':five(row)})
    return {**base,'ready':True,'top':selected,'flagged':flagged,'conditions':conditions,'monthly_bdt':1000,'months':months,'years':months//12,
      'calculation':'Monthly compounding; payments at month end; no upfront amount; before tax/fees. Illustration, not a bank maturity quote or eligibility promise.',
      'tie_break':'Equal rates use stable bank ID; excluded equal-rate banks are not worse.',
      'cutoff_ties':[{**r,'maturity_estimate_bdt':maturity(r['rate_percent'])} if product=='dps' else dict(r) for r in sorted(strongest.values(),key=lambda r:r['bank_id']) if r['bank_id'] not in {x['bank_id'] for x in top} and Decimal(r['rate_percent'])==Decimal(top[-1]['rate_percent'])]}

def groups(data):
    """Strong banks by rate, highest first; equal rates are spoken together."""
    output=[]
    for row in data['top']+data['cutoff_ties']:
        if output and Decimal(output[-1][0])==Decimal(row['rate_percent']):output[-1][1].append(row)
        else:output.append((row['rate_percent'],[row]))
    return output

def join_names(rows):
    names=[r['name_bn'] for r in rows]
    if len(names)>1 and all(n.endswith(' ব্যাংক') for n in names):names=[n[:-len(' ব্যাংক')] for n in names[:-1]]+[names[-1]]
    return names[0] if len(names)==1 else ', '.join(names[:-1])+' ও '+names[-1]

def warning(row):
    if row['status']=='no_data':return 'তবে ওই ব্যাংকের অবস্থা যাচাইয়ের তথ্য আমাদের কাছে কম'
    if row['status']=='high':return 'তবে ওই ব্যাংকের ঝুঁকি বেশি'
    return 'তবে ওই ব্যাংকে কিছু সতর্কতার লক্ষণ আছে'

def term_phrase(months,word='ডিপিএস'):
    if months is None:return f'মেয়াদ জানা নেই এমন {word}ে'
    return f"{months//12} বছরের {word}ে" if months%12==0 else f"{months} মাসের {word}ে"

def flagged_sentence(row,word='ডিপিএস'):
    if row['matches_five_years']:return f"{row['name_bn']} {row['rate_percent']}% দেয়, {warning(row)}।"
    return f"{row['name_bn']} {term_phrase(row['comparison_months'],word)} {row['rate_percent']}% দেয়, {warning(row)}।"

# Three wordings with the same facts, so repeat visits don't sound scripted.
OPENINGS=(
    lambda y,first,w:f"সুদের হিসাবে বললে, {y} বছরের {w}ে সবচেয়ে বেশি দেয় {first}।",
    lambda y,first,w:f"{y} বছরের {w}ের কথা ধরলে, সুদ সবচেয়ে বেশি দেয় {first}।",
    lambda y,first,w:f"সুদের হার দেখলে, {y} বছরের {w}ে এগিয়ে আছে {first}।")
CLOSINGS=('এদের সবার অবস্থা ভালো।','এই ব্যাংকগুলোর অবস্থা ভালো।','সবগুলোর অবস্থাই ভালো।')

def template(data,variant=0):
    """Plain spoken answer: rates only; the calculation stays on the card."""
    parts=[f"{join_names(rows)}, {rate}%" for rate,rows in groups(data)]
    word=data.get('word','ডিপিএস');text=OPENINGS[variant%3](data['years'],parts[0],word)
    if len(parts)==2:text+=f" এরপর {parts[1]}।"
    elif len(parts)>2:text+=" এরপর "+', '.join(parts[1:-1])+f", আর {parts[-1]}।"
    text+=' '+CLOSINGS[variant%3]
    for row in data['flagged'][:2]:text+=' '+flagged_sentence(row,word)
    return text+' '+QUESTIONS[variant%3].format(word=word)

def fixed_bn(data):
    """The approved Bangla shape: a same-term flagged bank first, then the strong banks by rate."""
    word=data.get('word','ডিপিএস');head=f"সুদের হিসাবে {data['years']} বছরের {word}ে"
    same=[r for r in data['flagged'][:2] if r['matches_five_years']];later=[r for r in data['flagged'][:2] if not r['matches_five_years']]
    def said(rate,rows):
        names=[r['name_bn'] for r in rows]
        joined=names[0] if len(names)==1 else ', '.join(names[:-1])+' আর '+names[-1]
        return f"{joined} {rate}% দেয়" if len(rows)==1 else f"{joined} {rate}% করে দেয়"
    parts=[said(rate,rows) for rate,rows in groups(data)];sentences=[]
    for row in same:sentences.append(f"{row['name_bn']} {row['rate_percent']}% দেয়। {warning(row)}।")
    for index in range(0,len(parts),2):sentences.append(', '.join(parts[index:index+2])+'।')
    if same:
        names=[r['name_bn'].split()[0] for _,rows in groups(data) for r in rows]
        sentences.append((', '.join(names[:-1])+' আর '+names[-1] if len(names)>1 else names[0])+' ভালো অবস্থায় আছে।')
    else:sentences.append('এই ব্যাংকগুলো ভালো অবস্থায় আছে।')
    for row in later:sentences.append(flagged_sentence(row,word))
    return head+' '+' '.join(sentences)+' '+QUESTION

def template_en(data):
    """English answer for an English question: same code-selected facts, fixed wording."""
    word='DPS' if data.get('product','dps')=='dps' else 'FDR'
    def names(rows):
        names=[r['name_en'] for r in rows]
        return names[0] if len(names)==1 else ', '.join(names[:-1])+' and '+names[-1]
    parts=[f"{names(rows)} at {rate}%" for rate,rows in groups(data)]
    text=f"By interest rate, for a {data['years']}-year {word} the highest is {parts[0]}"
    text+=('.' if len(parts)==1 else f", then {parts[1]}." if len(parts)==2 else ', then '+', '.join(parts[1:-1])+f", and {parts[-1]}.")
    text+=' These banks are in good condition.'
    for row in data['flagged'][:2]:
        months=row['comparison_months'];term='' if row['matches_five_years'] else ' on a '+(f"{months//12}-year {word}" if months and months%12==0 else f"{months}-month {word}" if months else f"{word} of unknown term")
        caution='we have limited information to assess that bank' if row['status']=='no_data' else 'that bank carries high risk' if row['status']=='high' else 'that bank shows some warning signs'
        text+=f" {row['name_en']} offers {row['rate_percent']}%{term}, but {caution}."
    return text+' Which one would you like details on?'

def spoken_facts(data):
    """The only facts Meta may use; no calculation, upfront example or source dates."""
    word=data.get('word','ডিপিএস')
    facts=[{'id':'scope','text_bn':f"শুধু {data['years']} বছরের {word}ের সুদের হার, ভালো অবস্থার ব্যাংকগুলোর মধ্যে।"}]
    for rate,rows in groups(data):
        for row in rows:facts.append({'id':row['offer_id'],'text_bn':f"{row['name_bn']}: {rate}%, অবস্থা ভালো।"})
    for row in data['flagged'][:2]:facts.append({'id':'flag:'+row['offer_id'],'text_bn':flagged_sentence(row,word)})
    return facts

def card_line(row,data):
    """Exact figures for the visible card; the fixed example never uses the user's money."""
    if row in data['flagged']:
        label='অবস্থা যাচাইয়ের তথ্য কম' if row['status']=='no_data' else 'উচ্চ ঝুঁকি' if row['status']=='high' else 'সতর্কতার লক্ষণ'
        months=row['comparison_months'];term='মেয়াদ জানা নেই' if months is None else f"{months//12} বছর" if months%12==0 else f"{months} মাস"
        return f"{row['name_bn']}: {row['rate_percent']}% বার্ষিক, {term}; {label}।"+('' if row['matches_five_years'] else f" {data['years']} বছরের হার প্রকাশিত নেই।")
    if data.get('product','dps')!='dps':return f"{data['years']} বছরের {data['word']}, {row['name_bn']}: {row['rate_percent']}% বার্ষিক।"
    text=f"{data['years']} বছরের ডিপিএস, {row['name_bn']}: {row['rate_percent']}% বার্ষিক। উদাহরণ: মাসে {data['monthly_bdt']:,} টাকা করে জমালে {data['years']} বছরে আনুমানিক {row['maturity_estimate_bdt']:,} টাকা (মাসিক চক্রবৃদ্ধি, কর ও ফি কাটার আগে; ব্যাংকের নিজের হিসাব আলাদা হতে পারে)।"
    for condition in data['conditions']:
        if condition['bank_id']==row['bank_id']:text+=f" ব্যাংকের উদাহরণে শুরুতে {condition['initial_example_bdt']:,} টাকা জমার কথা আছে; এই হিসাবে তা ধরা হয়নি।"
    return text

def quantities(text):
    value=text.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    value=re.sub(r'(?<=\d),(?=\d)','',value)
    return [Decimal(n) for n in re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?',value)]

ADVICE=re.compile(r'নিরাপদ|সেরা|সবচেয়ে ভালো|সবথেকে ভালো|রাখুন|রাখা উচিত|বিনিয়োগ করুন|নিশ্চিত|গ্যারান্টি|পরামর্শ দিচ্ছি|কত টাকা')

def key(name):
    return name[:-len(' ব্যাংক')] if name.endswith(' ব্যাংক') else name

MAX_SPOKEN_WORDS=70  # Three rates plus two flagged banks must all be said.
def validate(answer,data):
    """Checks what matters: right rate with the right bank, warnings kept, nothing invented."""
    normalized=answer.translate(str.maketrans('০১২৩৪৫৬৭৮৯','0123456789'))
    if not answer.rstrip().endswith('?'):return 'closing_question'
    if len(pronounce(answer,'bn').split())>MAX_SPOKEN_WORDS:return 'word_limit'
    if re.search('[A-Za-z]',answer):return 'non_bangla'
    if ADVICE.search(answer):return 'advice_or_amount'
    spoken=[r for _,rows in groups(data) for r in rows]+data['flagged'][:2]
    allowed={Decimal(r['rate_percent']) for r in spoken}|{Decimal(data['years'])}
    allowed|={Decimal(r['comparison_months']//12 if r['comparison_months']%12==0 else r['comparison_months']) for r in data['flagged'][:2] if r['comparison_months']}
    if any(number not in allowed for number in quantities(answer)):return 'unknown_number'
    # The term is the comparison: it must be said, and a shorter-term rate keeps its own term.
    if not re.search(rf"{data['years']}\s*বছর",normalized):return 'missing_term'
    if len(re.findall(r'[।?]',answer))<3:return 'run_on_sentence'
    others={key(r['name_bn']) for r in data['inventory']}-{key(r['name_bn']) for r in spoken}
    if any(name in normalized for name in others):return 'unknown_bank'
    # Each bank's first rate after its name must be its own rate.
    marks=sorted((m.start(),m.end(),r) for r in spoken for m in re.finditer(re.escape(key(r['name_bn'])),normalized))
    for row in spoken:
        found=[m for m in marks if m[2] is row]
        if not found:return 'missing_bank'
        rate=re.search(r'(\d+(?:\.\d+)?)\s*(?:%|শতাংশ)',normalized[found[0][1]:])
        if not rate or Decimal(rate[1])!=Decimal(row['rate_percent']):return 'swapped_rate'
    for row in data['flagged'][:2]:
        after=normalized[[m for m in marks if m[2] is row][0][0]:]
        if not re.search(r'তথ্য[^।?]*কম' if row['status']=='no_data' else r'ঝুঁকি' if row['status']=='high' else r'সতর্ক',after):return 'missing_warning'
        months=row['comparison_months']
        if not row['matches_five_years'] and months:
            term=months//12 if months%12==0 else months
            if not re.search(rf"(?<![\d.]){term}\s*(?:বছর|মাস)",after.split('।')[0]):return 'missing_flagged_term'
    # "অবস্থা ভালো", "ভালো অবস্থায় আছে" and similar: both words in one sentence.
    if not re.search(r'অবস্থা[^।?]*ভালো|ভালো[^।?]*অবস্থা',answer):return 'missing_status'
    return None

SYSTEM='''You are Ilma, a warm, plain-spoken Bangladeshi woman who explains banks
like a knowledgeable relative. Someone asked which bank's DPS is best. Answer in
natural spoken Bangla, 40-55 words, using ONLY the supplied facts:
- Frame it as interest rates ("সুদের হিসাবে"), never as "best" or "safe".
- Say the term ("5 বছরের ডিপিএসে") and name every bank in the facts with its full
  name and its own rate, highest first. Banks with the same rate can be said together.
- A warned bank with a different term keeps its own term in the same sentence
  (for example "1 বছরের ডিপিএসে 10%").
- Use 3 to 5 short sentences, not one long sentence.
- Say once that these banks are in good condition.
- Keep each warning sentence's meaning for any bank marked with a warning.
- Write every number as digits with % (for example 8.75%); code pronounces them.
- No calculations, no money amounts, no dates, no advice, no other banks or facts.
- End with one short question offering details, such as "আপনি কোনটার বিস্তারিত শুনবেন?"
Return JSON {"answer": "..."}.'''

async def compose(data,trace,client=None,variant=0):
    started=time.monotonic();fallback=template(data,variant)
    system=SYSTEM if data.get('product','dps')=='dps' else SYSTEM.replace('ডিপিএস',data['word']).replace('DPS','FDR').replace('5 বছরের',str(data['years'])+' বছরের')
    if validate(fallback,data):raise ValueError('The fixed DPS template does not fit the response constraints')
    if not settings.META_MODEL_API_KEY and client is None:return fallback,'unconfigured'
    from ilma_api.http_clients import shared
    http=client or shared();owned=http is None
    if owned:http=httpx.AsyncClient(follow_redirects=False)
    body={'model':settings.MUSE_SPARK_MODEL,'temperature':.7,'reasoning_effort':'minimal','max_tokens':1600,
      'response_format':{'type':'json_schema','json_schema':{'name':data.get('product','dps')+'_comparison','strict':True,'schema':{'type':'object','additionalProperties':False,'properties':{'answer':{'type':'string'}},'required':['answer']}}},
      'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(spoken_facts(data),ensure_ascii=False)}]}
    reason=None
    try:
        response=await asyncio.wait_for(http.post(settings.MUSE_SPARK_API_URL,headers={'Authorization':'Bearer '+settings.META_MODEL_API_KEY},json=body,timeout=httpx.Timeout(settings.HUMAN_MODEL_TIMEOUT_SECONDS,connect=2)),settings.HUMAN_MODEL_TIMEOUT_SECONDS)
        if response.status_code!=200:reason='http_'+str(response.status_code);answer=fallback
        else:
            answer=' '.join(json.loads(response.json()['choices'][0]['message']['content'])['answer'].split())
            reason=validate(answer,data)
            if reason:answer=fallback
    except (httpx.HTTPError,asyncio.TimeoutError,ValueError,KeyError,TypeError,IndexError):reason='provider_or_schema';answer=fallback
    finally:
        if owned:await http.aclose()
    trace.append({'stage':'PLAN','model':settings.MUSE_SPARK_MODEL,'ms':round((time.monotonic()-started)*1000),'status':'fallback' if reason else 'ok','reason':reason or data.get('product','dps')+'_fact_list_only'})
    return answer,reason

def split_question(answer):
    """The last question sentence becomes the next question; the rest is the reply."""
    parts=re.split(r'(?<=[।.!])\s+',answer.strip())
    return (' '.join(parts[:-1]),parts[-1]) if len(parts)>1 and parts[-1].endswith('?') else (answer,'')

async def run_question(text,context,banks,db,watch_identity=None,client=None,device_hash=None,on_sentence=None,product='dps'):
    from ilma_api.human_agent import controls,render,finish
    from ilma_api.human_memory import load
    from ilma_api.voice_agent import Conversation
    from ilma_api.voice_pipeline import consume_question
    started=time.monotonic();initial=context.conversation or Conversation()
    id,memory=await call(db,lambda session:load(session,initial.conversation_token))
    from ilma_api.voice_text import turn_language
    language='en' if turn_language(text,context)=='en' else 'bn'
    c=Conversation.model_validate(memory.get('conversation') or initial.model_dump()).model_copy(update={'institution_id':None,'product':product,'tenor':PRODUCTS[product]['months'],'basis':'conventional','network':None,'tier':None,'language':language})
    memory['protocol']=2;trace=[{'stage':'RESOLVER','model':'code','ms':0,'status':'ok','reason':'best_'+product+'_comparison'}]
    data=await call(db,lambda session:build(session,product))
    if not data['ready']:
        answer=controls('compare',c,PRODUCTS[product]['word']+' তুলনার জন্য যথেষ্ট প্রকাশিত তথ্য নেই।' if language=='bn' else 'There is not enough published information to compare '+product.upper()+' rates.','',['repeat','end'])
        result=render(answer,c,[],trace,'template');result['dps_data_ready']=False;result['reason']=data['reason']
        return await finish(result,'[redacted]',id,memory,db,started)
    await call(db,lambda session:consume_question(session,watch_identity or device_hash or product+'-comparison'))
    if language=='en':
        spoken,reason=template_en(data),None
        trace.append({'stage':'PLAN','model':'code','ms':0,'status':'ok','reason':'english_fact_template'})
    else:
        spoken,reason=fixed_bn(data),None
        trace.append({'stage':'PLAN','model':'code','ms':0,'status':'ok','reason':'approved_bangla_template'})
    from ilma_api.rules.reasons import format_date
    facts=[]
    for row in data['top']+data['cutoff_ties']+data['flagged']:
        card=card_line(row,data)+' হারতালিকা '+format_date(date.fromisoformat(row['date']),bn=True)
        facts.append({'fact_id':product+'-compare:'+row['offer_id'],'institution_id':row['bank_id'],'kind':'service','text_bn':card,'text_en':row['product'],'values':{'rate_percent':row['rate_percent'],'tenor_months':data['months'] if row not in data['flagged'] else row['comparison_months'],'monthly_example_bdt':data['monthly_bdt'],'maturity_estimate_bdt':row.get('maturity_estimate_bdt'),'status':row['status'],'calculation':data['calculation']},'source':{'source_url':row['source_url'],'source_title':row['product'],'published_at':row['date'],'page':row['page'],'quote':row['quote']}})
    reply,question=split_question(spoken)
    if re.search(r'[\u0980-\u09ff]',question):question=QUESTION
    answer=controls('compare',c,reply,question,['repeat','end']).model_copy(update={'used_fact_ids':[f['fact_id'] for f in facts]})
    result=render(answer,c,facts,trace,'template' if reason else 'code')
    result.update(comparison_product=product,dps_data_ready=True,dps_comparison_facts=spoken_facts(data),dps_comparison_data={key:data[key] for key in ['top','flagged','conditions','monthly_bdt','months','years','calculation','tie_break','cutoff_ties']},dps_model_fallback_reason=reason)
    return await finish(result,'[redacted]',id,memory,db,started)
