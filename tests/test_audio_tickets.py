"""Synthetic provider fixtures: ticket polling never repeats paid synthesis."""
import asyncio
from unittest.mock import patch,AsyncMock
import httpx
from ilma_api import settings
from ilma_api.audio_cache import AudioStore

def test_parallel_identical_tickets_share_one_generation_and_status(tmp_path):
    async def scenario():
        release=asyncio.Event();calls=[]
        async def provider(request):
            calls.append(request);await release.wait()
            return httpx.Response(200,content=b'synthetic-mp3')
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            store=AudioStore(tmp_path,client)
            with patch.multiple(settings,ELEVENLABS_API_KEY='synthetic-key',ELEVENLABS_VOICE_ID='synthetic-voice'),patch('ilma_api.agent_audio.duration_ms',AsyncMock(return_value=1000)):
                first,second=await asyncio.gather(store.register(['A public sourced answer.'],'en',True),store.register(['A public sourced answer.'],'en',True))
                token=first['audio_url'].split('/')[-1][:-4]
                for _ in range(5):assert (await store.status(token))['state']=='pending'
                assert len(calls)==1
                release.set();assert await store.wait(first) and await store.wait(second)
                assert (await store.status(token))['state']=='ready'
                assert len(calls)==1
            await store.close()
    asyncio.run(scenario())

def test_rejected_text_is_negatively_cached_without_repeated_paid_calls(tmp_path):
    async def scenario():
        calls=[]
        async def provider(request):calls.append(request);return httpx.Response(422)
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            store=AudioStore(tmp_path,client)
            with patch.multiple(settings,ELEVENLABS_API_KEY='synthetic-key',ELEVENLABS_VOICE_ID='synthetic-voice'):
                first=await store.register(['Synthetic rejected text.'],'en',True)
                assert not await store.wait(first)
                await asyncio.gather(*list(store.tasks))
                second=await store.register(['Synthetic rejected text.'],'en',True)
                for ticket in (first,second):
                    state=await store.status(ticket['audio_url'].split('/')[-1][:-4])
                    assert state['state']=='unavailable' and state['code']=='speech_rejected'
                assert len(calls)==1
            await store.close()
    asyncio.run(scenario())

def test_acknowledgement_never_synthesizes_a_missing_cache(tmp_path):
    from ilma_api.voice_acknowledgements import cached
    async def scenario():
        store=AudioStore(tmp_path)
        with patch('ilma_api.audio_cache.get_store',return_value=store),patch.object(store,'register',AsyncMock()) as register:
            assert await cached('bn',{}) is None
            register.assert_not_awaited()
    asyncio.run(scenario())
