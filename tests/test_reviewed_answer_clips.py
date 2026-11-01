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


def test_tts_change_invalidates_old_audio_even_when_display_text_is_same(tmp_path,monkeypatch):
    import asyncio,sys
    from unittest.mock import AsyncMock
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from build_approved_card_clips import generate
    from ilma_api import elevenlabs
    text='৭%';speech='সাত শতাংশ';audio=tmp_path/'bn/q001.mp3';audio.parent.mkdir();audio.write_bytes(b'old numeric audio')
    item=dict(key='bn:q001',file='bn/q001.mp3',text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest(),tts_text=speech,tts_sha256=hashlib.sha256(speech.encode()).hexdigest())
    old={**item,'tts_sha256':item['text_sha256'],'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest()}
    (tmp_path/'manifest.json').write_text(json.dumps({'clips':{item['key']:old}}))
    monkeypatch.setattr(elevenlabs,'accounts',lambda:[('a','synthetic','v')]*3)
    synth=AsyncMock(return_value=(b'new spoken words',{'key_name_used':'primary','voice_id':'synthetic'}));monkeypatch.setattr(elevenlabs,'synthesize',synth)
    result=asyncio.run(generate([item],tmp_path,None,120))
    assert synth.await_args.args[1]==speech and result['batch_complete']
    assert result['clips'][item['key']]['text']==text and audio.read_bytes()==b'new spoken words'


def test_failed_replacement_never_marks_stale_clip_batch_complete(tmp_path,monkeypatch):
    import asyncio,sys
    from unittest.mock import AsyncMock
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from build_approved_card_clips import generate
    from ilma_api import elevenlabs
    item=dict(key='bn:q001',file='bn/q001.mp3',text='৭%',text_sha256='a'*64,tts_text='সাত শতাংশ',tts_sha256='b'*64)
    audio=tmp_path/item['file'];audio.parent.mkdir();audio.write_bytes(b'old')
    (tmp_path/'manifest.json').write_text(json.dumps({'clips':{item['key']:{**item,'tts_sha256':'a'*64,'audio_sha256':hashlib.sha256(b'old').hexdigest()}}}))
    monkeypatch.setattr(elevenlabs,'accounts',lambda:[('a','synthetic','v')]*3)
    monkeypatch.setattr(elevenlabs,'synthesize',AsyncMock(side_effect=ValueError('synthetic failure')))
    with pytest.raises(ValueError):asyncio.run(generate([item],tmp_path,None,120))
    saved=json.loads((tmp_path/'manifest.json').read_text());assert saved['batch_complete'] is False and saved['remaining_clips']==1


def test_explicit_extension_requires_both_languages_and_all_ids(tmp_path):
    p,data=fixture(tmp_path)
    data.update(question_start=94,question_end=95)
    data['clips']=[{**r,'key':r['key'].replace('q001','q094').replace('q002','q095'),'file':r['file'].replace('q001','q094').replace('q002','q095')} for r in data['clips'] if r['key'].endswith(('q001','q002'))]
    data['total_chars']=sum(r['chars'] for r in data['clips']);p.write_text(json.dumps(data))
    assert len(builder.approved(p))==4
    data['clips'].pop();p.write_text(json.dumps(data))
    with pytest.raises(ValueError):builder.approved(p)
