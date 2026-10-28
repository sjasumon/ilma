"""Synthetic latency/stream isolation tests; no provider or real recording."""
import asyncio
import json
from unittest.mock import AsyncMock,patch
import httpx
import pytest
from fastapi import HTTPException
from test_voice_agent import db,BANKS
from ilma_api import settings
from ilma_api.audio_cache import AudioStore
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.voice_pipeline import run_pipeline


def test_result_is_available_before_audio_generation_finishes(db):
    async def run():
        waiting=asyncio.Event()
        store=type('Store',(),{'wait':lambda self,ticket:waiting.wait()})()
        context=VoiceContext(agent=True,ui_lang='en',speak=True,choice='services',conversation=Conversation(state='BANK',institution_id=1))
        with patch('ilma_api.audio_cache.register_speech',new=AsyncMock(return_value={'audio_url':'/v1/audio/'+'a'*32+'.mp3','audio_urls':['/v1/audio/'+'a'*32+'.mp3']})),patch('ilma_api.audio_cache.get_store',return_value=store):
            pipeline=run_pipeline(None,'','',context,BANKS,db,mode='text')
            result=None
            while result is None:
                frame=await pipeline.__anext__()
                if frame.startswith('event: result'):result=json.loads(frame.split('data: ',1)[1])
            assert result['type']=='agent_turn' and result['audio_pending']
            assert result['speech']==result['text'] and result['speech_format']=='paragraph'
            assert (await pipeline.__anext__()).startswith('event: speech')
            task=asyncio.create_task(pipeline.__anext__());await asyncio.sleep(.01)
            assert not task.done(),'audio completion must remain independent from the delivered result'
            waiting.set()
            with pytest.raises(StopAsyncIteration):await task
    asyncio.run(run())


def test_stream_first_chunk_cache_dedup_expiry_and_permissions(tmp_path):
    async def run():
        release=asyncio.Event();calls=[]
        class Chunks(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'synthetic-first';await release.wait();yield b'-second'
        async def handler(request):calls.append(request);return httpx.Response(200,stream=Chunks())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            store=AudioStore(tmp_path,client)
            with patch.object(settings,'ELEVENLABS_API_KEY','synthetic-key'),patch.object(settings,'ELEVENLABS_VOICE_ID','synthetic-voice'),patch('ilma_api.agent_audio.duration_ms',new=AsyncMock(return_value=1000)):
                first=await store.register(['Synthetic public status'],'en');second=await store.register(['Synthetic public status'],'en')
                token=first['audio_url'].rsplit('/',1)[-1][:-4]
                response=await store.response(token);body=response.body_iterator
                assert await body.__anext__()==b'synthetic-first'
                assert len(calls)==1
                assert not next(iter(store.jobs.values())).done.is_set()
                release.set();assert await body.__anext__()==b'-second'
                with pytest.raises(StopAsyncIteration):await body.__anext__()
                assert await store.wait(first)
                cached=await store.response(second['audio_url'].rsplit('/',1)[-1][:-4])
                assert cached.headers['x-ilma-cache']=='hit'
                assert len(calls)==1
                assert all(path.stat().st_mode & 0o077==0 for path in tmp_path.glob('*.mp3'))
                path=tmp_path/'tickets'/(token+'.json');item=json.loads(path.read_text());item['expires']=0;path.write_text(json.dumps(item))
                with pytest.raises(HTTPException) as error:await store.response(token)
                assert error.value.status_code==404
                await store.close()
    asyncio.run(run())


def test_slow_database_call_does_not_block_loop_and_owns_its_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from ilma_api.database_tasks import call
    import threading,time
    engine=create_engine('sqlite://')
    engine.dialect.name='mysql'  # No SQL is executed: exercise only task ownership.
    async def run():
        with Session(engine) as original:
            main_thread=threading.get_ident();started=time.monotonic()
            def slow(owned):
                assert owned is not original and threading.get_ident()!=main_thread
                time.sleep(.1);return 'done'
            task=asyncio.create_task(call(original,slow))
            await asyncio.sleep(.01)
            assert time.monotonic()-started<.08 and not task.done()
            assert await task=='done'
    asyncio.run(run());engine.dispose()


def test_shared_admission_fails_closed_without_breaking_pages():
    from ilma_api.admission import ProviderAdmissionMiddleware
    class Broken:
        shared=True
        def enter(self,address):raise RuntimeError('private database failure')
    async def run():
        async def app(scope,receive,send):
            await send({'type':'http.response.start','status':200,'headers':[]});await send({'type':'http.response.body','body':b'page'})
        gate=ProviderAdmissionMiddleware(app,Broken())
        async def receive():return {'type':'http.request','body':b''}
        for method,path,status in [('POST','/v1/ask',503),('GET','/',200)]:
            result=[]
            async def send(message):result.append(message)
            await gate({'type':'http','method':method,'path':path,'headers':[],'client':('synthetic',1)},receive,send)
            assert result[0]['status']==status
            assert b'private database failure' not in result[-1]['body']
    asyncio.run(run())


def test_streaming_audio_is_not_gzipped():
    from ilma_api.compression import StreamingSafeGZipMiddleware
    async def run():
        async def app(scope,receive,send):
            await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'audio/mpeg')]})
            await send({'type':'http.response.body','body':b'synthetic audio','more_body':True})
            await send({'type':'http.response.body','body':b'end','more_body':False})
        result=[]
        async def send(message):result.append(message)
        await StreamingSafeGZipMiddleware(app)({'type':'http','path':'/v1/audio/'+'a'*32+'.mp3','headers':[(b'accept-encoding',b'gzip')]},lambda:None,send)
        assert b'content-encoding' not in dict(result[0]['headers'])
        assert result[1]['body']==b'synthetic audio' and result[1]['more_body']
    asyncio.run(run())


def test_simple_status_insurance_and_figures_never_use_spark(db):
    from ilma_api.voice_agent import run_agent_turn
    from ilma_api.voice_text import match_candidates
    async def run():
        with patch('ilma_api.voice_agent.model_call',new=AsyncMock(side_effect=AssertionError('Simple turns cannot use Spark'))):
            for text,tool in [('BRAC Bank','bank_summary'),('BRAC Bank কেমন আছে','bank_summary'),('BRAC Bank নিরাপদ','bank_summary'),('BRAC Bank টাকা রাখা যাবে','bank_summary'),('বীমা','insurance'),('২ লাখ','insurance'),('ব্যাংক বন্ধ হলে','insurance'),('BRAC Bank NPL কত','bank_figures')]:
                result=await run_agent_turn(text,VoiceContext(agent=True,ui_lang='bn',speak=False),BANKS,db,match_candidates(text,BANKS))
                assert next(s for s in result['trace']['steps'] if s['stage']=='ACT')['tool']==tool
                assert result['checked']=='template'
    asyncio.run(run())


def test_two_workers_share_first_chunks_without_duplicate_provider_call(tmp_path):
    async def run():
        release=asyncio.Event();calls=[]
        class Chunks(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'first';await release.wait();yield b'last'
        async def handler(request):calls.append(request);return httpx.Response(200,stream=Chunks())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            owner=AudioStore(tmp_path,client);follower=AudioStore(tmp_path,client)
            with patch.object(settings,'ELEVENLABS_API_KEY','synthetic-key'),patch.object(settings,'ELEVENLABS_VOICE_ID','synthetic-voice'),patch('ilma_api.agent_audio.duration_ms',new=AsyncMock(return_value=1000)):
                ticket=await owner.register(['Synthetic public sentence'],'en')
                token=ticket['audio_url'].rsplit('/',1)[-1][:-4]
                first=await owner.response(token)
                assert await first.body_iterator.__anext__()==b'first'
                second=await follower.response(token)
                assert await asyncio.wait_for(second.body_iterator.__anext__(),1)==b'first'
                assert len(calls)==1
                release.set()
                assert b''.join([chunk async for chunk in second.body_iterator])==b'last'
                assert await owner.wait(ticket)
                await owner.close();await follower.close()
    asyncio.run(run())
