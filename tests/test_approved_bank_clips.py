"""Handwritten approved-clip shapes; no supplied narration or export fixture copies."""
import importlib.util,json,hashlib
from pathlib import Path
import pytest
SPEC=importlib.util.spec_from_file_location('approved_bank_builder',Path(__file__).resolve().parents[1]/'scripts/build_approved_bank_clips.py')
BUILDER=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BUILDER)

def inputs(tmp_path,brac_award=False):
    slugs=['bankasia','bracbank','citybank','dutchbangl','ebl','islamibank','mtb','nbl','nccbank','primebank','sbacbank'];clips=[];cards=[]
    for i,slug in enumerate(slugs):
        text=(BUILDER.OMISSION if slug=='bracbank' else '')+'পরীক্ষার পাঠ।';key='bank:bn:sample_'+str(i);name='Example Lender '+str(i)+' PLC';risk='high' if slug in ['islamibank','nbl'] else 'no_data' if slug=='sbacbank' else 'strong'
        clips.append(dict(key=key,bank_name_en=name,risk_code={'strong':'low','high':'high','no_data':'no_data'}[risk],file='static/audio/bank/bn/'+key.removeprefix('bank:bn:')+'.mp3',chars=len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest(),text=text))
        rank=['nccbank','bankasia'] if slug=='nccbank' else ['primebank','dutchbangl']
        cards.append(dict(institution=dict(slug=slug,name_en=name),status=dict(code=risk),reasons=[{},{}] if slug=='islamibank' else [{},{},{}],award=dict(awarder_confirmed='true',year='2024') if slug=='bracbank' and brac_award else None,comparison_facts=[dict(rows=[dict(bank_slug=s) for s in rank])],readout=dict(source_sha256='a'*64)))
    data=dict(total_chars=sum(c['chars'] for c in clips),clips=clips);a=tmp_path/'approved.json';b=tmp_path/'bindings.json';a.write_text(json.dumps(data,ensure_ascii=False));b.write_text(json.dumps(cards));return a,b,data,cards

def test_exact_text_hashes_filename_and_permitted_omission(tmp_path):
    a,b,d,c=inputs(tmp_path);items=BUILDER.plan(a,b)
    assert len(items)==11 and items[0]['file']=='bn/sample_0.mp3'
    assert items[0]['text']==d['clips'][0]['text']
    assert items[1]['text']=='পরীক্ষার পাঠ।' and items[1]['conditional_brac_award_omitted']
    assert all(i['source_sha256']=='a'*64 for i in items)

def test_confirmed_loaded_award_preserves_original_sentence(tmp_path):
    a,b,d,c=inputs(tmp_path,True);items=BUILDER.plan(a,b)
    assert items[1]['text']==d['clips'][1]['text'] and not items[1]['conditional_brac_award_omitted']

@pytest.mark.parametrize('field,value',[('text','পরিবর্তিত পাঠ।'),('file','static/audio/bank/bn/../../x.mp3'),('risk_code','high')])
def test_changed_text_path_or_risk_is_rejected(tmp_path,field,value):
    a,b,d,c=inputs(tmp_path);d['clips'][0][field]=value;a.write_text(json.dumps(d))
    with pytest.raises(ValueError):BUILDER.plan(a,b)

def test_ranking_and_islami_reason_guards(tmp_path):
    a,b,d,c=inputs(tmp_path);c[9]['comparison_facts'][0]['rows'].reverse();b.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='ranking'):BUILDER.plan(a,b)
    a,b,d,c=inputs(tmp_path);c[5]['reasons'].append({});b.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='two sourced reasons'):BUILDER.plan(a,b)
