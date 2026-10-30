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

def test_cash_percentage_and_taka_floor_are_spoken_as_distinct_units():
    data=example()
    data['rows'][0]['facts']['cash_advance_fee']={'value_num':180,'value_text':'180','unit':'bdt','condition':'2.5% or BDT 180 whichever is higher','quote':'Synthetic cash fee: 2.5% or BDT 180 whichever is higher','stale':False}
    data['rows'][1]['facts']['cash_advance_fee']={'value_num':3,'value_text':'3%','unit':'text','condition':'cash advance fee 3%','quote':'Synthetic cash fee 3%','stale':False}
    text=narration(data)
    assert 'আড়াই শতাংশ অথবা একশো আশি টাকা, যেটি বেশি' in text
    assert 'এনসিসির নগদ তোলার ফি তিন শতাংশ।' in text
    assert 'একশো আশি শতাংশ' not in text
    assert 'সময়মতো পুরো বিল দিলে সুদ নেই' not in text

def test_only_one_late_fee_is_not_repeated_as_both_extremes():
    data=example();data['rows'][0]['facts']['late_fee']={'value_num':450,'value_text':'450','unit':'bdt','condition':'','quote':'Synthetic 450','stale':False}
    text=narration(data)
    assert 'বিলম্ব ফির যে তথ্য আছে, তাতে ব্র্যাক ব্যাংকের ফি চারশো পঞ্চাশ টাকা।' in text
    assert 'আর ব্র্যাক ব্যাংকে' not in text

def test_equal_annual_fees_are_not_described_as_a_higher_next_price():
    data=example();data['rows'][1]['facts']['annual_fee']['value_num']=1100
    text=narration(data)
    assert 'সবগুলোর প্রকাশিত বার্ষিক ফি একই' in text
    assert 'এরপর' not in text

def test_selected_cost_audio_never_reuses_overview_or_another_cost(tmp_path):
    from ilma_api.service_clips import selected_narration
    data=example();data['choice']['attribute']='late_fee'
    for bank in data['rows']:
        bank['name_en']='Synthetic Bank';bank['state']='published';bank['card']={'synthetic':True}
        for fact in bank['facts'].values():fact.update(offer_id='annual-'+bank['slug'],doc_date='2026-10-01',condition_bn='',condition_en='')
        bank['facts']['late_fee']={**bank['facts']['annual_fee'],'offer_id':'late-'+bank['slug'],'value_num':450,'value_text':'450'}
    text=selected_narration(data)
    assert 'চারশো পঞ্চাশ টাকা' in text and 'এক হাজার একশো টাকা' not in text
    assert '\n\n' in text and 'ডাচ্ বাংলা' not in text
    file='bn/card-visa-gold-late-fee.mp3';path=tmp_path/file;path.parent.mkdir();path.write_bytes(b'synthetic-cost-audio')
    item={'file':file,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed':True,'reviewer':'synthetic-review','reviewed_at':'synthetic-date'}
    (tmp_path/'manifest.json').write_text(json.dumps({'version':1,'clips':{key('Visa','Gold','late_fee'):item}}))
    assert readout(data,directory=tmp_path)['audio_url'].split('?')[0].endswith('late-fee.mp3')
    data['choice']['attribute']='annual_fee'
    assert readout(data,directory=tmp_path)['audio_url'] is None
    assert readout(data,directory=tmp_path)['text']!=text
