"""No live provider calls: ordered accounts, cooldowns and exact approved text."""
import asyncio,importlib.util,json
from pathlib import Path
import httpx,pytest
from ilma_api import elevenlabs as el,settings
@pytest.fixture(autouse=True)
def accounts(monkeypatch):
    el._failed.clear()
    for i in range(1,4):
        monkeypatch.setattr(settings,f'ELEVENLABS_API_KEY_{i}',f'synthetic-key-{i}')
        monkeypatch.setattr(settings,f'ELEVENLABS_VOICE_ID_{i}',f'synthetic-voice-{i}')
    yield
    el._failed.clear()
def test_order_cooldown_and_exact_text():
    async def run():
        calls=[]
        def fake(request):
            calls.append((request.headers['xi-api-key'],json.loads(request.content)['text']))
            if request.headers['xi-api-key']=='synthetic-key-1':return httpx.Response(402,json={'detail':{'status':'quota_exceeded'}})
            return httpx.Response(200,content=b'synthetic-audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            text='অপরিবর্তিত ১২.৫% — ১,০০০ টাকা।'
            assert (await el.synthesize(c,text))[1]['key_name_used']=='secondary'
            await el.synthesize(c,text)
        assert calls==[('synthetic-key-1',text),('synthetic-key-2',text),('synthetic-key-2',text)]
    asyncio.run(run())
@pytest.mark.parametrize('status',[400,422])
def test_bad_input_never_tries_another_account(status):
    async def run():
        calls=[]
        def fake(r):calls.append(r);return httpx.Response(status,json={'detail':{'status':'quota_exceeded'}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            with pytest.raises(el.SpeechFailure):await el.synthesize(c,'test')
        assert len(calls)==1
    asyncio.run(run())
@pytest.mark.parametrize('status',[401,402,403,429,500,502,503,504])
def test_all_listed_statuses_fall_back(status):
    async def run():
        calls=[]
        def fake(r):calls.append(r);return httpx.Response(status if len(calls)==1 else 200,content=b'audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:assert (await el.synthesize(c,'test'))[1]['key_name_used']=='secondary'
    asyncio.run(run())
def test_timeout_and_exhaustion_are_sanitized():
    async def run():
        calls=[]
        def fake(r):calls.append(r);raise httpx.ReadTimeout('secret provider message',request=r)
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            with pytest.raises(el.SpeechFailure) as e:await el.synthesize(c,'test')
        assert len(calls)==3 and 'secret' not in str(e.value)
        assert all(reason=='timeout' for _,reason in e.value.failures)
    asyncio.run(run())
@pytest.mark.parametrize('failure',[httpx.ReadTimeout,httpx.ReadError,httpx.RemoteProtocolError])
def test_no_fallback_after_partial_stream(failure):
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):yield b'first';raise failure('synthetic')
    async def run():
        calls=[]
        def fake(r):calls.append(r);return httpx.Response(200,stream=Broken())
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            parts=[]
            with pytest.raises(el.SpeechFailure):
                async for part in el.chunks(c,'test'):parts.append(part)
        assert parts==[b'first'] and len(calls)==1
    asyncio.run(run())

@pytest.mark.parametrize('failure',[httpx.ConnectError,httpx.ReadError,httpx.RemoteProtocolError])
def test_transport_errors_try_remaining_accounts_and_cool_down(failure):
    async def run():
        calls=[]
        def fake(request):
            calls.append(request.headers['xi-api-key'])
            if calls[-1]!='synthetic-key-3':raise failure('private provider detail',request=request)
            return httpx.Response(200,content=b'synthetic-audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
            audio,used=await el.synthesize(client,'test')
            assert audio==b'synthetic-audio' and used['key_name_used']=='tertiary'
            await el.synthesize(client,'test')
        assert calls==['synthetic-key-1','synthetic-key-2','synthetic-key-3','synthetic-key-3']
    asyncio.run(run())

def test_transport_exhaustion_is_sanitized():
    async def run():
        calls=[]
        def fake(request):
            calls.append(request)
            raise httpx.ConnectError('private provider detail',request=request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as client:
            with pytest.raises(el.SpeechFailure) as result:await el.synthesize(client,'test')
        assert len(calls)==3 and result.value.failures==[(name,'transport_error') for name in ['primary','secondary','tertiary']]
        assert 'private provider detail' not in str(result.value)
    asyncio.run(run())

def test_no_fallback_after_buffered_audio_was_yielded():
    from contextlib import asynccontextmanager
    class Client:
        calls=0
        @asynccontextmanager
        async def stream(self,*args,**kwargs):
            self.calls+=1
            response=httpx.Response(200,content=b'first')
            try:yield response
            finally:raise httpx.ReadError('private cleanup error')
    async def run():
        client=Client();parts=[]
        with pytest.raises(el.SpeechFailure):
            async for part in el.chunks(client,'test',stream=False):parts.append(part)
        assert client.calls==1 and parts==[b'first']
    asyncio.run(run())
def test_batch_preserves_finished_clips_and_skips_unchanged(tmp_path):
    spec=importlib.util.spec_from_file_location('approved_builder',Path('scripts/build_approved_card_clips.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    import hashlib
    text='অপরিবর্তিত ১২.৫%';item={'key':'bn:card-synthetic-annual-fee','file':'bn/card-synthetic-annual-fee.mp3','text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest()}
    async def run():
        calls=[]
        def fake(r):calls.append(r);assert json.loads(r.content)['text']==text;return httpx.Response(200,content=b'synthetic-audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            await m.generate([item],tmp_path,c);await m.generate([item],tmp_path,c)
        assert len(calls)==1
        manifest=json.loads((tmp_path/'manifest.json').read_text());assert manifest['clips'][item['key']]['key_name_used']=='primary'
        assert manifest['batch_complete'] and manifest['remaining_clips']==0
    asyncio.run(run())

@pytest.mark.parametrize('code',sorted(el.CODES))
def test_listed_provider_codes_fall_back_even_on_other_status(code):
    async def run():
        calls=[]
        def fake(r):
            calls.append(r)
            return httpx.Response(409,json={'detail':{'status':code}}) if len(calls)==1 else httpx.Response(200,content=b'audio')
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake)) as c:
            assert (await el.synthesize(c,'test'))[1]['key_name_used']=='secondary'
    asyncio.run(run())

def test_cooldown_expires_after_fifteen_minutes(monkeypatch):
    clock=[1000];monkeypatch.setattr(el.time,'monotonic',lambda:clock[0])
    token=el.identity('synthetic-key-1','synthetic-voice-1');el._failed[token]=1900
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'audio'))) as c:
            assert (await el.synthesize(c,'test'))[1]['key_name_used']=='secondary'
            clock[0]=1901
            assert (await el.synthesize(c,'test'))[1]['key_name_used']=='primary'
    asyncio.run(run())

def test_batch_timeout_override_leaves_runtime_default_unchanged(monkeypatch):
    from unittest.mock import patch
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'audio'))) as c:
            with patch.object(el,'deadline',wraps=el.deadline) as bounded:
                await el.synthesize(c,'offline',timeout_seconds=120)
                await el.synthesize(c,'runtime')
            assert [call.args[0] for call in bounded.call_args_list]==[120,25]
    asyncio.run(run())
