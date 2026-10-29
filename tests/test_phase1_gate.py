"""Handwritten synthetic acceptance cases, never real exports or paid providers."""
import copy,importlib.util
from pathlib import Path
import pytest
from ilma_api.human_tokens import FactToken

spec=importlib.util.spec_from_file_location('phase1_gate',Path(__file__).resolve().parents[1]/'ops/phase1_gate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def complete():
    rows=[{'intent':'compare' if i<30 else 'correction' if i<60 else 'bank_overview','language':'bn' if i%2 else 'en','passed':True,'claim_audit':{'errors':[]}} for i in range(404)]
    return {'cases':rows,'accuracy':1,'bank_target_failures':0,'slot_failures':0,'required_fact_failures':0,'unsolicited_protection':0,'one_call_rate':1,'p95_ms':3000,'evaluated_commit':'1'*40,'runtime_source_unchanged':True}

@pytest.mark.parametrize('field,value',[
 ('accuracy',.899),('bank_target_failures',1),('slot_failures',1),('required_fact_failures',1),
 ('unsolicited_protection',1),('one_call_rate',.899),('p95_ms',6001),('sample',True),('partial',True),('evaluated_commit',''),('runtime_source_unchanged',False)])
def test_each_gate_is_required_even_with_good_overall_accuracy(field,value):
    report=complete();assert module.gate(report)['passed']
    report[field]=value;assert not module.gate(report)['passed']

@pytest.mark.parametrize('intent',['compare','correction'])
def test_bad_subgroup_cannot_hide_behind_overall_score(intent):
    report=complete()
    for row in [r for r in report['cases'] if r['intent']==intent][:4]:row['passed']=False
    assert not module.gate(report)['passed']

def test_missing_or_failing_audit_cannot_be_called_zero_factual_errors():
    report=complete();report['cases'][0].pop('claim_audit')
    assert not module.gate(report)['passed']
    report['cases'][0]['claim_audit']={'errors':['changed_source']}
    assert not module.gate(report)['passed']

def example():
    clause='offers a 12-month deposit at 8% as of January 2026'
    fact={'fact_id':'synthetic-offer','institution_id':1,'kind':'service','values':{'rate':8,'unit':'pct_year','tenor_months':12,'doc_date':'2026-01-01'},'text_en':clause,'text_bn':'পরীক্ষার তথ্য','source':{'source_url':'https://example.test/schedule','quote':'Synthetic deposit 12 months, 8% in January 2026'}}
    registry={'bank:1':FactToken('Example Bank',(),1,'bank'),'f:synthetic-offer':FactToken(clause,('synthetic-offer',),1,'service')}
    result={'intent':'service_detail','speech':'Example Bank '+clause+'. Would you like more?','next':{'question':'Would you like more?'},'facts':[copy.deepcopy(fact)],'speech_fact_ids':['synthetic-offer']}
    return fact,registry,result

def test_canonical_source_values_and_spoken_clause_are_audited():
    fact,registry,result=example()
    assert module.audit_answer(result,{fact['fact_id']:fact},registry)['errors']==[]

@pytest.mark.parametrize('replacement',['9%','2027','Other Bank','the highest rate'])
def test_false_rate_date_bank_and_rank_in_speech_are_rejected(replacement):
    fact,registry,result=example()
    old='8%' if replacement=='9%' else '2026' if replacement=='2027' else 'Example Bank' if replacement=='Other Bank' else 'deposit'
    result['speech']=result['speech'].replace(old,replacement)
    assert module.audit_answer(result,{fact['fact_id']:fact},registry)['errors']

@pytest.mark.parametrize('field',['source','values'])
def test_card_cannot_substitute_a_different_source_or_rate(field):
    fact,registry,result=example()
    result['facts'][0][field]={'source_url':'https://example.test/other'} if field=='source' else {'rate':99}
    assert module.audit_answer(result,{fact['fact_id']:fact},registry)['errors']

def test_unbacked_financial_reply_is_not_a_social_control():
    result={'intent':'bank_figures','speech':'The rate is 99%.','facts':[],'speech_fact_ids':[]}
    assert module.audit_answer(result,{}, {})['errors']
