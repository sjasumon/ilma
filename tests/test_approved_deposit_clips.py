"""Handwritten clip plans; no supplied narration/source-export fixtures."""
import importlib.util,json,hashlib
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('approved_deposit_builder',Path(__file__).resolve().parents[1]/'scripts/build_approved_deposit_clips.py');builder=importlib.util.module_from_spec(s);s.loader.exec_module(builder)
def inputs(tmp_path):
    clips=[];readouts={}
    for p,m,a in builder.PLANS:
        slug=builder.key(p,m,a);text='পরীক্ষার অনুমোদিত পাঠ।';clips.append(dict(key='deposit:bn:'+slug,text=text,chars=len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest(),file='static/audio/services/bn/deposit_'+slug+'.mp3'))
        readouts[slug]=dict(source_sha256='a'*64,example_amount=5000 if p=='dps' else 100000,example_months=m,references=[dict(bank_slug='sbacbank',risk_code='no_data',offer=dict(source_url='https://example.example/rate'))])
    data=dict(clips=clips,total_chars=sum(c['chars'] for c in clips));a=tmp_path/'approved.json';b=tmp_path/'bindings.json';a.write_text(json.dumps(data));b.write_text(json.dumps(dict(readouts=readouts)));return a,b,data,readouts

def test_plan_retains_all_fourteen_exact_texts_and_requested_filenames(tmp_path):
    a,b,d,r=inputs(tmp_path);items=builder.plan(a,b)
    assert len(items)==14 and all(i['text']==d['clips'][n]['text'] for n,i in enumerate(items))
    assert items[0]['file']=='static/audio/services/bn/deposit_fdr-1-all.mp3' and items[0]['key']=='deposit:bn:fdr-1-all'
@pytest.mark.parametrize('field,value',[('text','পরিবর্তিত পাঠ।'),('file','static/audio/services/bn/../../x.mp3'),('text_sha256','b'*64)])
def test_edited_approved_content_or_path_is_rejected(tmp_path,field,value):
    a,b,d,r=inputs(tmp_path);d['clips'][0][field]=value;a.write_text(json.dumps(d))
    with pytest.raises(ValueError):builder.plan(a,b)

def test_missing_reference_and_changed_risk_stop_generation(tmp_path):
    a,b,d,r=inputs(tmp_path);r['fdr-1-all']['references'][0]['risk_code']='strong';b.write_text(json.dumps(dict(readouts=r)))
    with pytest.raises(ValueError,match='risk'):builder.plan(a,b)
