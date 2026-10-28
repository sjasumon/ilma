"""Synthetic guided-command and sourced-readout checks."""
import asyncio
import json
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from ilma_api.ivr import match_ivr_action
from ilma_api.voice_text import VoiceContext
from ilma_api.voice_pipeline import run_pipeline, readout
from ilma_api.voice_assets import CATALOG

@pytest.mark.parametrize('text,action', [('আবার।','again'),('Again!','again'),('কারণ','reasons'),('insurance','insurance'),('উৎস','sources'),('নতুন ব্যাংক','name'),('থামুন','stop'),('হ্যাঁ','one'),('না','two'),('এক','one'),('দুই','two')])
def test_commands(text, action):
    assert match_ivr_action(text, 'next') == action
    assert match_ivr_action(text, None) is None

@pytest.mark.parametrize('text', ['Islami Bank insurance', 'নতুন ব্যাংক কেমন আছে', 'কারণ কী ইস্টার্ন ব্যাংক', 'someone', 'stop loan interest'])
def test_no_partial_command_match(text):
    assert match_ivr_action(text, 'menu') is None

def test_language_scope_and_context_validation():
    assert match_ivr_action('English', 'language') == 'en'
    assert match_ivr_action('বাংলা', 'language') == 'bn'
    assert match_ivr_action('English', 'name') is None
    with pytest.raises(ValidationError): VoiceContext(ivr_step='unbounded')

def test_command_does_not_need_bank_index_or_intent():
    async def run():
        with patch('ilma_api.voice_pipeline.log_outcome'), patch('ilma_api.voice_pipeline.understand') as intent:
            events=[x async for x in run_pipeline(None,'কারণ','',VoiceContext(ivr_step='next'),lambda: (_ for _ in ()).throw(AssertionError('No DB index needed')),None,mode='text')]
        assert any('"ivr_action": "reasons"' in e or '"ivr_action":"reasons"' in e for e in events)
        intent.assert_not_called()
    asyncio.run(run())

def test_dynamic_confirmation_and_sources_no_urls():
    card={'institution':{'name_bn':'পরীক্ষা ব্যাংক','name_en':'Example Bank'},'reasons':[{'text_bn':'পরীক্ষার কারণ','text_en':'Example reason','publisher':'বাংলাদেশ ব্যাংক','published_at':'2026-10-12','source_url':'https://example.test/raw'}]}
    async def run():
        async def speech(text,language): return 'data:audio/mpeg;base64,AA=='
        with patch('ilma_api.voice_pipeline.get_institution_report_card',return_value=card),patch('ilma_api.voice_pipeline.speech',side_effect=speech):
            confirm=await readout('ivr',1,'bn',None,'ivr_confirm')
            assert 'পরীক্ষা ব্যাংক' in confirm['text'] and '{bank}' not in confirm['text']
            source=await readout('sources',1,'bn',None)
            assert 'বাংলাদেশ ব্যাংক' in source['text'] and '১২ অক্টোবর' in source['text'] and 'http' not in source['text']
            reasons=await readout('reasons',1,'en',None)
            assert reasons['text']=='Example reason'
        assert all(CATALOG[key][0] and CATALOG[key][1] for key in CATALOG if key.startswith('ivr_'))
    asyncio.run(run())


def test_voice_commands_run_after_transcription():
    import io
    import wave
    from unittest.mock import AsyncMock
    data=io.BytesIO()
    with wave.open(data,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000)
        output.writeframes(b'\x00\x00'*1600)
    async def run():
        with patch('ilma_api.voice_pipeline.convert_audio',new=AsyncMock(return_value=data.getvalue())), patch('ilma_api.voice_pipeline.transcribe',new=AsyncMock(return_value='আবার।')) as transcribe, patch('ilma_api.voice_pipeline.log_outcome'):
            events=[x async for x in run_pipeline(b'synthetic','', 'audio/webm',VoiceContext(ivr_step='next'),[],None)]
            transcribe.assert_awaited_once()
        assert 'transcript' in events[0] and any('ivr_action' in event and 'again' in event for event in events)
    asyncio.run(run())

def test_readout_request_scope():
    from ilma_api.main import ReadoutRequest
    assert ReadoutRequest(kind='ivr',prompt='ivr_name').prompt=='ivr_name'
    with pytest.raises(ValidationError):ReadoutRequest(kind='ivr')
    with pytest.raises(ValidationError):ReadoutRequest(kind='news',prompt='ivr_open')
    with pytest.raises(ValidationError):ReadoutRequest(kind='ivr',prompt='arbitrary text')

def test_reviewed_base_bundle_remains_available(tmp_path):
    from ilma_api.voice_assets import load_approved,digest
    clips={}
    for lang in ('bn','en'):
        for key in CATALOG:
            if key.startswith('ivr_'):continue
            name=lang+'-'+key
            (tmp_path/(name+'.opus')).write_bytes(b'synthetic opus')
            (tmp_path/(name+'.mp3')).write_bytes(b'synthetic mp3')
            clips[lang+':'+key]={'file':name+'.opus','fallback_file':name+'.mp3','audio_sha256':digest(b'synthetic opus'),'fallback_sha256':digest(b'synthetic mp3'),'text':'Synthetic review fixture','text_sha256':digest(b'Synthetic review fixture'),'reviewed':True,'reviewer':'Example reviewer','reviewed_at':'2026-10-28'}
    (tmp_path/'manifest.json').write_text(json.dumps({'clips':clips}))
    assert load_approved(tmp_path,allow_legacy=True)['clips']==clips
    with pytest.raises(ValueError):load_approved(tmp_path)
    clips['bn:welcome']['reviewed']=False
    (tmp_path/'manifest.json').write_text(json.dumps({'clips':clips}))
    with pytest.raises(ValueError):load_approved(tmp_path,allow_legacy=True)
