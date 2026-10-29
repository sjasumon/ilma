"""Small handwritten signal fixtures and source-backed wording constraints."""
import asyncio,io,json,wave
from unittest.mock import patch
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


def test_streaming_pause_removal_retains_quiet_speech_and_cleans_up_on_cancel():
    async def run():
        encoded=await synthetic_mp3();release=asyncio.Event()
        async def chunks():
            yield encoded[:int(len(encoded)*.8)]
            await release.wait();yield encoded[int(len(encoded)*.8):]
        stream=trim_long_pauses(chunks());first=await asyncio.wait_for(stream.__anext__(),3)
        assert first and not release.is_set(),'Must stream before provider completion'
        release.set();output=first+b''.join([c async for c in stream])
        measured=await duration_ms(output);assert 2100<=measured<=3000,measured
        decoded=np.frombuffer(await process(output,['-ac','1','-ar','24000','-f','s16le','pipe:1']),dtype='<i2').astype(float)/32768
        # Both the loud first and quiet final tone must survive at full length.
        assert np.count_nonzero(np.abs(decoded)>.001)/24000>1.7
        for sample,frequency in [(decoded[7200:16800],440),(decoded[-16800:-9600],660)]:
            spectrum=np.abs(np.fft.rfft(sample));peak=np.fft.rfftfreq(len(sample),1/24000)[spectrum.argmax()]
            assert abs(peak-frequency)<8,'Pace processing must retain pitch'
        handles=[];original=asyncio.create_subprocess_exec
        async def start(*a,**kw):
            child=await original(*a,**kw);handles.append(child);return child
        release.clear()
        with patch('ilma_api.agent_audio.asyncio.create_subprocess_exec',new=start):
            stream=trim_long_pauses(chunks());await asyncio.wait_for(stream.__anext__(),3);await stream.aclose()
        assert handles and all(h.returncode is not None for h in handles)
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
                assert json.loads(meta.read_text())['duration_ms']<3000
                item['short']=False;store.atomic(tmp_path/'tickets'/(token+'.json'),json.dumps(item).encode())
                assert store.ticket(token) is None
            await store.close()
    asyncio.run(run())


def test_word_sentence_and_actual_audio_duration_gates():
    validate_spoken_answer('A short answer. Hear more?','en',10000)
    for text,ms in [(' '.join(['word']*31),1000),('One. Two. Three. Four?',1000),('Short.',10001)]:
        with pytest.raises(ValueError):validate_spoken_answer(text,'en',ms)


def test_negative_ratio_keeps_half_percent_and_small_values_do_not_become_zero():
    assert spoken_percent('-5.48',True,negative=True)=='সাড়ে ৫%'
    assert spoken_percent('-5.48',False,negative=True)=='5.5%'
    assert spoken_percent('0.04',True)=='০.০৪%'
    assert spoken_percent('0.004',False)=='0.004%'
    assert rounded('0.04',True)=='০.০৪'
