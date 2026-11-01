"""Handwritten synthetic scripts validate complete bilingual batch integrity."""
import hashlib,importlib.util,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('reviewed_answer_clips',Path(__file__).resolve().parents[1]/'scripts/build_reviewed_answer_clips.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

def fixture(tmp_path):
    rows=[]
    for lang,text in [('bn','পরীক্ষার উত্তর।'),('en','Synthetic answer.')]:
        for n in range(1,94):rows.append(dict(key=f'{lang}:q{n:03d}',language=lang,text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),chars=len(text),file=f'{lang}/q{n:03d}.mp3'))
    data=dict(approved=True,review_sha256='a'*64,clips=rows,total_chars=sum(r['chars'] for r in rows));p=tmp_path/'approved.json';p.write_text(json.dumps(data));return p,data

def test_all_186_scripts_are_retained_without_transform(tmp_path):
    p,data=fixture(tmp_path);items=builder.approved(p)
    assert len(items)==186 and [i['text'] for i in items]==[i['text'] for i in data['clips']]
    assert items[0]['file']=='bn/q001.mp3' and items[-1]['file']=='en/q093.mp3'

@pytest.mark.parametrize('problem',['missing','duplicate','edited','path','unapproved','language'])
def test_incomplete_edited_or_unapproved_batch_is_rejected(tmp_path,problem):
    p,d=fixture(tmp_path)
    if problem=='missing':d['clips'].pop()
    elif problem=='duplicate':d['clips'][-1]=d['clips'][0]
    elif problem=='edited':d['clips'][0]['text']='Changed answer'
    elif problem=='path':d['clips'][0]['file']='../outside.mp3'
    elif problem=='unapproved':d['approved']=False
    elif problem=='language':d['clips'][0]['language']='en'
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError):builder.approved(p)
