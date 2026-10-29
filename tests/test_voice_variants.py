"""Handwritten synthetic protocol; no exported source rows or provider calls."""
from test_voice_agent import db
from ilma_api.human_stream import Draft,Header
from ilma_api.human_tokens import FactToken
from ilma_api.human_variants import fingerprint,checked,store,choose

def test_cached_introductions_rotate_and_changed_sources_do_not_replay(db):
    registry={'bank:1':FactToken('Example Bank',(),1,'bank'),
      'f:s':FactToken('shows good condition based on its current published financial indicators',('s',),1,'status'),
      'f:c':FactToken('holds additional capital above the minimum requirement, providing some room to absorb losses',('c',),1,'figure'),
      'f:p':FactToken('reports an established branch network',('p',),1,'profile')}
    lines=['⟨bank:1⟩ ⟨f:s⟩.','⟨f:c⟩.','⟨f:p⟩.'];question='Would you like another detail?'
    payload={'language':'en','intent_hint':'bank_overview','slots':{'bank':1},'tokens':[],
             'line_choices':lines,'question_choices':[question],'required_intro_facts':['s','c'],'fact_revision':'synthetic-v1'}
    decode=lambda value:(value,{'s':'s','c':'c','p':'p'})
    first=Draft(Header(intent='bank_overview',used=['s','c','p']),lines,question)
    second=Draft(first.header,[lines[0],lines[2],lines[1]],question)
    assert checked(first,payload,decode,registry) and checked(second,payload,decode,registry)
    key=fingerprint(payload,registry)
    for ordinal,draft in enumerate((first,second)):store(db,key,ordinal,1,'en','bank_overview',draft,'synthetic')
    memory={}
    a=choose(db,key,memory,payload,decode,registry);b=choose(db,key,memory,payload,decode,registry)
    assert a.lines!=b.lines
    changed=fingerprint({**payload,'fact_revision':'synthetic-v2'},registry)
    assert choose(db,changed,memory,payload,decode,registry) is None

def test_cached_variant_with_missing_mandatory_reason_is_rejected():
    registry={'f:s':FactToken('shows good condition',('s',),1,'status')}
    payload={'language':'en','intent_hint':'bank_condition','line_choices':['⟨f:s⟩.'],
             'question_choices':['More?'],'required_intro_facts':['c']}
    assert not checked(Draft(Header(intent='bank_condition',used=['s']),['⟨f:s⟩.'],'More?'),payload,lambda v:(v,{}),registry)
