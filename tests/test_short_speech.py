"""Small handwritten signal fixtures and source-backed wording constraints."""
import asyncio,io,json,wave
from unittest.mock import patch,AsyncMock
import numpy as np
import httpx
import pytest
from ilma_api import settings
from ilma_api.agent_audio import process,duration_ms,trim_long_pauses
from ilma_api.answer_wording import validate_spoken_answer,spoken_percent,rounded

async def synthetic_mp3():
    rate=24000;t=np.arange(rate)/rate
    pcm=np.concatenate([np.zeros(rate//10),.2*np.sin(2*np.pi*440*t),np.zeros(int(rate*1.2)),.004*np.sin(2*np.pi*660*t),np.zeros(rate*2)])
    wav=io.BytesIO()
    with wave.open(wav,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((pcm*32767).astype('<i2').tobytes())
    return await process(wav.getvalue(),['-c:a','libmp3lame','-b:a','96k','-f','mp3','pipe:1'])


def test_streaming_preserves_natural_pauses_and_quiet_speech():
    async def run():
        encoded=await synthetic_mp3();release=asyncio.Event()
        async def chunks():
            yield encoded[:int(len(encoded)*.8)]
            await release.wait();yield encoded[int(len(encoded)*.8):]
        stream=trim_long_pauses(chunks());first=await asyncio.wait_for(stream.__anext__(),3)
        assert first and not release.is_set(),'Must stream before provider completion'
        release.set();output=first+b''.join([c async for c in stream])
        measured=await duration_ms(output);assert 5200<=measured<=5600,measured
        decoded=np.frombuffer(await process(output,['-ac','1','-ar','24000','-f','s16le','pipe:1']),dtype='<i2').astype(float)/32768
        # Both the loud first and quiet final tone must survive at full length.
        assert np.count_nonzero(np.abs(decoded)>.001)/24000>1.7
        assert output==encoded,'Natural TTS must not be accelerated or silence gated'
        release.clear();stream=trim_long_pauses(chunks())
        await stream.__anext__();await stream.aclose()
    asyncio.run(run())


def test_short_cache_reuses_identical_raw_public_speech_with_separate_policy(tmp_path):
    from ilma_api.audio_cache import AudioStore
    async def run():
        async def provider(request):raise AssertionError('Existing public speech must not be billed again')
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            store=AudioStore(tmp_path,client);store.folders()
            with patch.object(settings,'ELEVENLABS_API_KEY','synthetic-key'),patch.object(settings,'ELEVENLABS_VOICE_ID','synthetic-voice'):
                text='Synthetic public speech';oldkey=store.key(text,'en');store.atomic(tmp_path/(oldkey+'.mp3'),await synthetic_mp3())
                ticket=await store.register([text],'en',short=True);assert await store.wait(ticket)
                token=ticket['audio_url'].split('/')[-1][:-4];item=store.ticket(token)
                assert item['short'] and item['key']!=oldkey
                meta=tmp_path/(item['key']+'.json')
                for _ in range(40):
                    if meta.exists():break
                    await asyncio.sleep(.05)
                assert json.loads(meta.read_text())['duration_ms']>5000
                item['short']=False;store.atomic(tmp_path/'tickets'/(token+'.json'),json.dumps(item).encode())
                assert store.ticket(token) is None
            await store.close()
    asyncio.run(run())


def test_word_and_actual_audio_duration_gates():
    validate_spoken_answer('A natural answer. Hear more?','en',30000)
    validate_spoken_answer(' '.join(['word']*45),'en',first=True)
    validate_spoken_answer(' '.join(['word']*70),'en')
    for text,ms,first in [(' '.join(['word']*46),1000,True),(' '.join(['word']*71),1000,False),('Short.',30001,False)]:
        with pytest.raises(ValueError):validate_spoken_answer(text,'en',ms,first=first)


def test_negative_ratio_keeps_half_percent_and_small_values_do_not_become_zero():
    assert spoken_percent('-5.48',True,negative=True)=='সাড়ে ৫%'
    assert spoken_percent('-5.48',False,negative=True)=='5.5%'
    assert spoken_percent('0.04',True)=='০.০৪%'
    assert spoken_percent('0.004',False)=='0.004%'
    assert rounded('0.04',True)=='০.০৪'


def test_provider_receives_normalized_words_with_one_consistent_voice_and_model(tmp_path):
    from ilma_api.audio_cache import AudioStore
    from ilma_api.voice_numbers import pronounce
    async def run():
        requests=[]
        async def provider(request):
            requests.append(request);return httpx.Response(200,content=b'synthetic-provider-audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            store=AudioStore(tmp_path,client)
            with patch.object(settings,'ELEVENLABS_API_KEY','synthetic-key'),patch.object(settings,'ELEVENLABS_VOICE_ID','synthetic-voice'),patch('ilma_api.agent_audio.duration_ms',new=AsyncMock(return_value=1000)):
                for display,lang in [('CRAB AAA ১৮%','bn'),('FDR ৭.৭৫%','bn'),('AAA earns 7.75%','en')]:
                    ticket=await store.register([display],lang,short=True);assert await store.wait(ticket)
                    payload=json.loads(requests[-1].content)
                    assert payload['text']==pronounce(display,lang)
                    assert payload['model_id']==settings.ELEVENLABS_MODEL
                    assert requests[-1].url.path.endswith('/synthetic-voice/stream')
                assert len(requests)==3
            await store.close()
    asyncio.run(run())
