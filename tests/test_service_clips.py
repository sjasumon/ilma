"""Synthetic narration/audio fixtures; no paid requests or bank source exports."""
import asyncio,hashlib,importlib.util,json
from pathlib import Path
from unittest.mock import patch,AsyncMock
import httpx
from ilma_api.service_clips import narration,readout,key

def example():
    rows=[]
    for id,slug,fee,old in [(1,'bracbank',1100,False),(2,'nccbank',1600,False),(3,'dutchbangl',500,True)]:
        annual={'value_num':fee,'value_text':str(fee),'condition':'','quote':str(fee),'unit':'bdt','stale':old}
        rows.append({'id':id,'slug':slug,'name_bn':'পরীক্ষা ব্যাংক','status':{'code':'strong'},'facts':{'annual_fee':annual},'offer':annual})
    return {'choice':{'product_type':'card','network':'Visa','tier':'Gold'},'rows':rows}

def test_narration_excludes_stale_banks_without_recommending():
    text=narration(example())
    assert 'ডাচ্ বাংলা' not in text and 'সেরা' not in text
    assert 'ভিসা গোল্ড' in text and 'সূত্র স্ক্রিনে' in text
    assert 'একটি ব্যাংকের তথ্য পুরনো' in text

def test_readout_is_text_only_until_exact_audio_is_reviewed(tmp_path):
    data=example();text=narration(data);file='bn/card-visa-gold.mp3';path=tmp_path/file;path.parent.mkdir();path.write_bytes(b'synthetic-audio')
    item={'file':file,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed':False,'reviewer':'synthetic-review','reviewed_at':'synthetic-date'}
    manifest={'version':1,'clips':{key('Visa','Gold'):item}}
    def save():(tmp_path/'manifest.json').write_text(json.dumps(manifest))
    save();assert readout(data,directory=tmp_path)=={'audio_url':None,'text':text}
    item['reviewed']=True;save();assert readout(data,directory=tmp_path)['audio_url']=='/static/audio/services/'+file+'?v='+item['audio_sha256'][:16]
    path.write_bytes(b'changed');assert readout(data,directory=tmp_path)['audio_url'] is None
    path.write_bytes(b'synthetic-audio');data['rows'][0]['facts']['annual_fee']['value_num']=1200
    assert readout(data,directory=tmp_path)['audio_url'] is None

def test_generator_calls_fake_provider_once_and_skips_unchanged_text(tmp_path):
    spec=importlib.util.spec_from_file_location('build_service_clips',Path(__file__).resolve().parents[1]/'scripts/build_service_clips.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    text='শুধু পরীক্ষার বর্ণনা।';item={'key':'bn:card-visa-gold','file':'bn/card-visa-gold.mp3','text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'data_version':'synthetic'};calls=[]
    async def run():
        def fake(request):calls.append(request);return httpx.Response(200,content=b'synthetic-audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
            await module.generate([item],tmp_path,client,'synthetic-voice','synthetic-key','synthetic-model')
            await module.generate([item],tmp_path,client,'synthetic-voice','synthetic-key','synthetic-model')
    asyncio.run(run());assert len(calls)==1
    manifest=json.loads((tmp_path/'manifest.json').read_text());assert manifest['clips'][item['key']]['reviewed'] is False
