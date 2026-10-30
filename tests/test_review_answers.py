"""Manual answer review of 30 Oct, on tiny synthetic rows: answer shape, not stored values."""
import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import pytest
from test_voice_agent import db,BANKS
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_resolver import resolve
from ilma_api.human_tokens import fact_clause,term,product
from ilma_api.human_turn import deposit_order,date_once,fit_overview,paginate,profit_tokens,recommended,run,service_lines
from ilma_api.human_tokens import FactToken
from ilma_api.db import Fact,Source
from ilma_api.human_facts import annual_profit_change
from ilma_api import awards

@pytest.fixture(autouse=True)
def contextual_mode(isolate_voice_mode,monkeypatch):
    from ilma_api import settings
    monkeypatch.setattr(settings,'HUMAN_VOICE_ENABLED',True)

def ask(db,text,language='bn',model=None):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock(side_effect=model or AssertionError('no model'))):
            return await run(text,VoiceContext(agent=True,ui_lang=language,speak=False,conversation=Conversation(institution_id=1,language=language)),BANKS,db)
    return asyncio.run(scenario())

def rate(id,name,months,value,kind='dps',**extra):
    return dict(fact_id=id,institution_id=1,kind='service',source={'condition':extra.pop('condition','')},values={'product':name,'product_type':kind,'rate':value,'unit':'pct_year','tenor_min_months':months,'tenor_max_months':months,'tenor_options':[months],'selected_tenor':None,'basis':'conventional','doc_date':str(date.today()),**extra})

def context(language='bn'):
    return Conversation(institution_id=1,language=language,product='dps')

def registry():
    return {'bank:1':FactToken('টেস্ট ব্যাংক',(),1,'bank')}

@pytest.mark.parametrize('text',['ব্র্যাক ব্যাংকের ডিপিএস সম্বন্ধে বলবেন','ডিপিএস সম্পর্কে বলুন'])
def test_about_a_dps_is_not_a_protection_question(text):
    r=resolve(text,Conversation(institution_id=1),BANKS)
    assert r.intent=='service_detail' and not r.direct_protection

@pytest.mark.parametrize('text',['ব্যাংক বন্ধ হলে টাকা কী হবে','আমানত বীমা কত'])
def test_real_protection_questions_stay_protection(text):
    assert resolve(text,Conversation(institution_id=1),BANKS).intent=='insurance'

@pytest.mark.parametrize('text,metric',[('মূলধন কেমন?','crar'),('মূলধন পর্যাপ্ত আছে কি?','crar'),('How strong is its capital ratio?','crar'),('খেলাপি ঋণ কত?','npl_ratio')])
def test_metric_questions_are_figures(text,metric):
    r=resolve(text,Conversation(institution_id=1),BANKS)
    assert (r.intent,r.requested_metric)==('bank_figures',metric)

@pytest.mark.parametrize('text',['ফিক্সড ডিপোজিটের রেট জানতে চাই','স্থায়ী আমানতের সুদ কত'])
def test_bangla_names_for_fixed_deposit(text):
    assert resolve(text,Conversation(institution_id=1),BANKS).product=='fdr'

def test_both_platinum_spellings_set_the_tier():
    for word in ('প্লাটিনাম','প্ল্যাটিনাম'):
        assert resolve(f'ভিসা {word} কার্ডের ফি কত',Conversation(institution_id=1),BANKS).tier=='Platinum'

def test_deposit_rows_read_shortest_term_first_and_general_before_special():
    rows=[rate('a','Plain 12',12,7),rate('b','Plain 1',1,3),rate('c','Plain 3',3,6),rate('d','Senior 36',36,8),rate('e','General 36',36,7)]
    assert [r['fact_id'] for r in sorted(rows,key=deposit_order)]==['b','c','a','e','d']

def test_whole_year_terms_share_one_unit():
    assert term({'tenor_options':[36,60,84,120]},True)=='3, 5, 7 বা 10 বছর'
    assert term({'tenor_options':[36,60]},False)=='3 or 5 years'
    assert term({'tenor_min_months':12,'tenor_max_months':72},False)=='1 to 6 years'

def test_named_products_keep_their_names_in_both_languages():
    assert product({'product':'DPS for Women – আঁচল','product_type':'dps'},True)=='আঁচল ডিপিএস'
    assert product({'product':'DPS for Women – আঁচল','product_type':'dps'},False)=='DPS for Women'
    assert product({'product':'DPS+','product_type':'dps'},True)=='ডিপিএস প্লাস'

def line(row,text='একটি হার।'):
    return (text,[row['fact_id']])

def test_rate_question_opens_with_how_rates_vary():
    rows=[rate('a','Plain',12,7),rate('b','Plain',36,7.5)];facts={r['fact_id']:r for r in rows}
    r=SimpleNamespace(product='dps',tenor=None)
    out=service_lines('ডিপিএসের সুদ কত',[line(rows[0]),line(rows[1])],context(),r,registry(),facts)
    assert out[0][0]=='টেস্ট ব্যাংকের ডিপিএসের সুদ মেয়াদের ওপর নির্ভর করে।' and len(out)==3

def test_range_comes_from_the_stored_rows_never_a_wider_market_range():
    rows=[rate('a','General DPS',12,7.25),rate('b','Insurance Backed DPS',60,8)];facts={r['fact_id']:r for r in rows}
    out=service_lines('ডিপিএসের সুদ কত',[line(rows[0]),line(rows[1])],context(),SimpleNamespace(product='dps',tenor=None),registry(),facts)
    assert '7.25% থেকে 8%' in out[0][0]

def test_opinion_question_declines_advice_and_still_gives_the_rates():
    rows=[rate('a','Plain',12,7),rate('b','Plain',36,7.5)];facts={r['fact_id']:r for r in rows}
    out=service_lines('City Bank DPS, is it a good option',[line(rows[0]),line(rows[1])],context('en'),SimpleNamespace(product='dps',tenor=None),{'bank:1':FactToken('Test Bank',(),1,'bank')},facts)
    assert out[0][0].startswith('That decision is yours') and len(out)>=3

def test_one_rate_across_products_is_said_once_in_either_language():
    rows=[rate('a','EBL Confidence DPS',12,8),rate('b','EBL Child Future Plan DPS',36,8)];facts={r['fact_id']:r for r in rows}
    out=service_lines('DPS rate',[line(rows[0]),line(rows[1])],context('en'),SimpleNamespace(product='dps',tenor=None),{'bank:1':FactToken('Test Bank',(),1,'bank')},facts)
    assert out==[('Test Bank pays 8% on its EBL Confidence DPS for 1 year, EBL Child Future Plan DPS for 3 years.',['a','b'])]

def test_vat_is_said_only_when_every_row_stores_it():
    fee=lambda id,condition,tier:rate(id,'Card',12,1500,kind='card',condition=condition,tier=tier,network='Visa',attribute='annual_fee')
    both=[fee('a','plus 15% VAT','Gold'),fee('b','plus 15% VAT','Classic')];one=[fee('a','plus 15% VAT','Gold'),fee('b','','Classic')]
    answer=lambda rows:service_lines('কার্ডের ফি কত',[line(r) for r in rows],Conversation(institution_id=1,language='bn',product='card'),SimpleNamespace(product='card',tenor=None),registry(),{r['fact_id']:r for r in rows})
    assert 'ভ্যাট' in ' '.join(s for s,_ in answer(both)) and 'ভ্যাট' not in ' '.join(s for s,_ in answer(one))

def test_a_shared_sheet_date_is_said_once():
    text=', ১১ জুন ২০২৬-এর তালিকা অনুযায়ী।'
    assert [s for s,_ in date_once([('এক'+text,[]),('দুই'+text,[])])]==['এক।','দুই'+text]

def test_insurance_limit_wording_matches_in_both_languages():
    f=dict(kind='insurance',values={'limit':200000})
    assert 'সর্বোচ্চ 2 লাখ টাকা পর্যন্ত' in fact_clause(f,'bn')
    assert 'Tk 2 lakh (200,000) per depositor' in fact_clause(f,'en')

def test_a_very_large_bad_loan_share_is_not_called_a_part():
    f=lambda value:dict(kind='figure',values={'metric':'npl_ratio','value':value})
    assert 'বড় একটি অংশ' in fact_clause(f(.4966),'bn',True)
    assert 'বড় একটি অংশ' not in fact_clause(f(.0838),'bn',True)

def overview(status,*metrics):
    facts={'s':{'fact_id':'s','institution_id':1,'kind':'status','status':{'code':status},'values':{}}}
    for id,metric,value in metrics:facts[id]={'fact_id':id,'institution_id':1,'kind':'figure','values':{'metric':metric,'value':value,'minimum_percent':12.5}}
    return facts,{'bank:1':FactToken('টেস্ট ব্যাংক',(),1,'bank'),**{'f:'+id:FactToken('x',(id,),1,f['kind']) for id,f in facts.items()}}

def test_every_overview_recommends_loan_quality_with_capital():
    facts,tokens=overview('strong',('c','crar',.16),('n','npl_ratio',.02))
    assert recommended('bank_overview',Conversation(institution_id=1,language='bn'),tokens,facts,'k')==['f:s','f:c','f:n']

def test_a_weak_rating_does_not_replace_a_high_bad_loan_warning():
    facts,tokens=overview('strong',('c','crar',.16),('n','npl_ratio',.0838))
    facts['p']={'fact_id':'p','institution_id':1,'kind':'peer','values':{'metric':'rating','worse':True,'rank_high':9,'rank_low':1,'grade':'AA+'}}
    tokens['f:p']=FactToken('x',('p',),1,'peer')
    assert 'f:n' in recommended('bank_overview',Conversation(institution_id=1,language='bn'),tokens,facts,'k')

def test_award_opening_keeps_status_capital_and_loans_in_one_answer():
    facts,tokens=overview('strong',('c','crar',.16),('n','npl_ratio',.02))
    facts['a']={'fact_id':'a','institution_id':1,'kind':'award','values':{}}
    long='ব্যাংকের অবস্থা অনেক শব্দে বলা হলো '*2
    lines=[('টেস্ট ব্যাংককে ২০২৫ সালে একটি সংস্থা সেরা ব্যাংক বলেছে।',['a']),('টেস্ট ব্যাংকের '+long+'।',['s']),(long+'।',['c']),(long+'।',['n'])]
    c=Conversation(institution_id=1,language='bn',last_intent='bank_overview')
    out=fit_overview(lines,'আরও শুনবেন?',c,tokens,facts,'k')
    assert [ids for _,ids in out]==[['a'],['s'],['c'],['n']]
    assert 'ঋণের' in out[3][0] and paginate(out,'আরও শুনবেন?','bn')[1]==[]

def test_a_rate_list_breaks_between_terms_only():
    text='ডিপিএসে '+', '.join(f'{n} বছরে সুদ ৭.২৫%' for n in range(1,12))+'।'
    head,tail=paginate([('সুদ মেয়াদের ওপর নির্ভর করে।',[]),(text,['a'])],'আরও শুনবেন?','bn',split=True)
    assert tail and head[1][0].endswith('%।') and tail[0][0].endswith('%।')

def test_profit_answer_gives_year_and_change():
    found={'fact_id':'p','values':{'value':9647700000.0,'period_end':'2025-12-31'}}
    change={'fact_id':'c','institution_id':1,'kind':'figure','values':{'metric':'profit_change','value':103.76}}
    tokens=profit_tokens(found,{'c':change},1,True)
    assert tokens['asked:figure'].text=='নিট মুনাফা 2025 সালে প্রায় 965 কোটি টাকা'
    assert tokens['asked:change'].text=='আগের বছরের তুলনায় মুনাফা প্রায় 104% বেড়েছে'

def fact(db,id,year,value,quote,source):
    db.add(Fact(fact_id=id,institution_id=1,metric='net_profit',value=value,unit='bdt',period=str(year),period_end=date(year,12,31),source_id=source,quote=quote,basis='unknown',checked_by='agent',checked_on=date(2026,1,1)))

def sources(db):
    existing=db.query(Source).first()
    for id in ('rev-a','rev-b'):
        values={c.name:getattr(existing,c.name) for c in Source.__table__.columns}
        db.add(Source(**{**values,'source_id':id,'url':'https://example.test/'+id}))

def test_profit_change_across_sources_needs_the_quote_to_state_it(db):
    db.query(Fact).filter_by(institution_id=1,metric='net_profit').delete()
    sources(db);fact(db,'rev-1',2025,200,'Net profit 200 (+100.0%)','rev-a');fact(db,'rev-2',2024,100,'Net profit 100','rev-b');db.flush()
    assert annual_profit_change(db,1)['values']['value']==100
    db.query(Fact).filter_by(fact_id='rev-1').update({'quote':'Net profit 200'});db.flush()
    assert annual_profit_change(db,1) is None

def test_award_short_name_replaces_a_stiff_translation():
    award=SimpleNamespace(award_year=2024,medal='',award_name_bn='পরীক্ষা: সর্বাধিক অসামান্য ইসলামী ব্যাংক',short_name_bn='সেরা ইসলামী ব্যাংক সম্মাননা')
    assert awards.phrase(award,SimpleNamespace(name_bn='পরীক্ষা'),'bn','টেস্ট ব্যাংক')=='টেস্ট ব্যাংককে ২০২৪ সালে পরীক্ষা সেরা ইসলামী ব্যাংক সম্মাননা দিয়েছে।'

def test_product_answers_are_code_owned_and_repeat_exactly(db):
    first=ask(db,'এফডিআরের সুদ কত?');second=ask(db,'এফডিআরের হার বলুন')
    assert first['speech']==second['speech'] and first['checked']=='code'

@pytest.mark.parametrize('value,code',[(.0838,'strong'),(.0999,'strong'),(.10,'watch'),(.2499,'watch'),(.25,'high')])
def test_bad_loan_share_sets_the_status_word(value,code):
    from ilma_api.rules.status import evaluate
    facts={'crar':{'fact_id':'c','value':.16,'period':'2025','period_end':date(2025,12,31),'source_info':{}},'npl_ratio':{'fact_id':'n','value':value,'period':'2025','period_end':date(2025,12,31),'basis':'solo','source_info':{}}}
    result=evaluate({'id':1,'slug':'t','type':'bank','coverage':'full'},{'facts':facts,'ratings':[{'fact_id':'r','agency':'CRISL','long_term':'AA','rated_on':date(2026,8,25),'outlook':'stable','source_info':{}}],'events':[],'rates':{},'median_12m_fdr':.08},as_of=date(2026,10,27))
    assert result.code==code

def test_a_strong_bank_with_raised_bad_loans_keeps_the_warning():
    f=dict(kind='figure',values={'metric':'npl_ratio','value':.0838})
    assert 'নজরে রাখা দরকার' in fact_clause(f,'bn',True) and 'deserve attention' in fact_clause(f,'en',True)
    assert 'সামান্য' not in fact_clause(f,'bn',True)

def test_watch_wording_uses_the_status_word_in_both_languages():
    f=dict(kind='status',status={'code':'watch'},values={})
    assert 'সতর্ক থাকুন' in fact_clause(f,'bn') and 'ভালো' not in fact_clause(f,'bn')
    assert 'Watch' in fact_clause(f,'en') and 'good' not in fact_clause(f,'en')

@pytest.mark.parametrize('status,bn,en',[('watch','সতর্কতার লক্ষণ','warning signs'),('high','ঝুঁকি বেশি','high risk')])
def test_compare_rows_carry_the_bank_status(status,bn,en):
    from ilma_api.human_tokens import build_registry
    row=rate('a','Plain',12,7,status=status);row.update(bank_name_bn='টেস্ট',bank_name_en='Test')
    assert bn in build_registry([],[row],'bn')[0]['row:0.offer'].text
    assert en in build_registry([],[row],'en')[0]['row:0.offer'].text

def detail(field,value,as_of='2026-09-30'):
    return dict(fact_id='d:'+field,institution_id=1,kind='profile_detail',values={'field':field,'value':value,'as_of':as_of})

def test_interim_results_always_name_their_period():
    from ilma_api.human_turn import interim_line
    d={x['values']['field']:x for x in (detail('interim_net_profit','2121'),detail('interim_profit_change','38'),detail('interim_npl','2.03'))}
    assert interim_line(d,True)[0]=='2026 সালের প্রথম 9 মাসে সমন্বিত নিট মুনাফা 38% বেড়ে 2,121 কোটি টাকা, খেলাপি ঋণের হার 2.03%।'
    assert 'first 9 months of 2026' in interim_line(d,False)[0]
    del d['interim_npl'];assert interim_line(d,True) is None

def test_founding_date_and_founder_come_from_the_stored_row():
    from ilma_api.human_turn import founding_tokens
    d={x['values']['field']:x for x in (detail('founded_date','2001-07-04'),detail('founder_bn','পরীক্ষা নাম'),detail('founder','Test Name'))}
    assert 'প্রতিষ্ঠিত হয়' in founding_tokens(d,1,True)['asked:founded'].text
    assert founding_tokens(d,1,False)['asked:founder'].text=='Its founder is Test Name'
    assert founding_tokens({},1,True)=={}

def test_schemes_without_rates_say_the_rates_are_missing():
    from ilma_api.human_turn import note_tokens
    note=lambda name,bn,**v:dict(fact_id=name,values={'attribute':'scheme','product':name,'value_text':bn,**v})
    tokens=note_tokens([note('Plus Scheme','প্লাস স্কিম',tenor_options=[36,60]),note('Child Scheme','শিশু স্কিম')],'dps',1,False)
    assert tokens['note:product'].text=='DPS schemes: Plus Scheme for 3 or 5 years, Child Scheme'
    assert tokens['note:norate'].text=='We do not have their rates'

def test_a_stored_rate_range_is_said_as_a_range():
    from ilma_api.human_turn import note_tokens
    tokens=note_tokens([dict(fact_id='r',values={'attribute':'rate_range','value_text':'7.75-9.75'})],'fdr',1,True)
    assert tokens['note:product'].text=='এফডিআরের সুদ মেয়াদের ওপর ভিত্তি করে 7.75% থেকে 9.75%' and 'note:norate' not in tokens

def test_manual_profile_rows_need_wording_but_no_link():
    from ilma_api.profile_loader import validate
    row=dict(fact_id='x',bank_slug='t',field='founder',value='Name',as_of='2001-07-04',source_url='',page='manual_sumon',quote='Wording')
    assert validate(row)==row
    with pytest.raises(ValueError):validate({**row,'quote':''})
    with pytest.raises(ValueError):validate({**row,'page':'PDF 1'})

def test_vat_is_worded_as_may_apply():
    rows=[rate(i,'Card',12,1500,kind='card',condition=condition,tier='Gold',network='Visa',attribute='annual_fee') for i,condition in (('a','plus 15% VAT'),('b','15% VAT may apply'))]
    answer=lambda language:' '.join(s for s,_ in service_lines('card fee',[line(r) for r in rows],Conversation(institution_id=1,language=language,product='card'),SimpleNamespace(product='card',tenor=None),{'bank:1':FactToken('Test',(),1,'bank')},{r['fact_id']:r for r in rows}))
    assert '15% ভ্যাট যোগ হতে পারে' in answer('bn') and '15% VAT may apply' in answer('en')
