"""Public sourced TTS only. Expiring opaque tickets, persistent deduplicated cache.
No user recording, transcript, question or API key is written to this cache.
"""
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import time
import httpx
from fastapi import HTTPException,Request
from fastapi.responses import FileResponse,StreamingResponse
from ilma_api import settings
from ilma_api.http_clients import shared
from ilma_api.voice_numbers import pronounce

class AudioJob:
    def __init__(self):
        self.chunks=[];self.condition=asyncio.Condition();self.ready=asyncio.Event();self.done=asyncio.Event();self.failed=False;self.cache='miss'
    async def append(self,data):
        async with self.condition:self.chunks.append(data);self.ready.set();self.condition.notify_all()
    async def finish(self,failed=False):
        async with self.condition:self.failed=failed;self.done.set();self.ready.set();self.condition.notify_all()
    async def stream(self):
        index=0
        while True:
            async with self.condition:
                while index>=len(self.chunks) and not self.done.is_set():await self.condition.wait()
                chunks=self.chunks[index:];index=len(self.chunks);done=self.done.is_set()
            for chunk in chunks:yield chunk
            if done:return

class AudioStore:
    def __init__(self,directory=None,client=None):
        self.directory=Path(directory or settings.TTS_CACHE_DIR);self.client=client;self.jobs={};self.tasks=set();self.gate=asyncio.Semaphore(2)
    def key(self,text,language,short=False,policy='natural-speech-v5'):
        identity=[settings.ELEVENLABS_VOICE_ID,settings.ELEVENLABS_MODEL,settings.TTS_SPEED,language,pronounce(text,language)]
        if short:identity.append(policy)
        return hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest()
    def folders(self):
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);(self.directory/'tickets').mkdir(exist_ok=True,mode=0o700)
    def atomic(self,path,data):
        tmp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
        try:
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as output:output.write(data)
            os.replace(tmp,path)
        finally:
            tmp.unlink(missing_ok=True)
    def sweep(self):
        now=time.time()
        for path in (self.directory/'tickets').glob('*.json'):
            if now-path.stat().st_mtime>600:path.unlink(missing_ok=True)
        # Public source speech may be reused for a month; tickets expire in 10 min.
        files=sorted(self.directory.glob('*.mp3'),key=lambda p:p.stat().st_mtime)
        size=sum(p.stat().st_size for p in files)
        for path in files:
            length=path.stat().st_size
            if now-path.stat().st_mtime>30*86400 or size>128*1024*1024:
                path.unlink(missing_ok=True);path.with_suffix('.json').unlink(missing_ok=True);size-=length
    def valid_cache(self,key,short=False):
        path=self.directory/(key+'.mp3')
        try:
            measured=json.loads(path.with_suffix('.json').read_text())['duration_ms']
            return isinstance(measured,(int,float)) and not isinstance(measured,bool) and 0<measured and (not short or measured<=30000) and 0<path.stat().st_size<=2*1024*1024
        except (OSError,ValueError,KeyError,TypeError):return False
    async def register(self,texts,language,short=False):
        if not settings.ELEVENLABS_API_KEY or not re.fullmatch(r'[A-Za-z0-9_-]+',settings.ELEVENLABS_VOICE_ID):return None
        await asyncio.to_thread(self.folders)
        urls=[]
        for text in texts[:3]:
            if not text or len(text)>2000:continue
            token=secrets.token_urlsafe(24);key=self.key(text,language,short)
            descriptor={'key':key,'text':text,'language':language,'short':short,'expires':time.time()+600}
            await asyncio.to_thread(self.atomic,self.directory/'tickets'/(token+'.json'),json.dumps(descriptor,ensure_ascii=False).encode())
            urls.append('/v1/audio/'+token+'.mp3')
            if not await asyncio.to_thread(self.valid_cache,key,short):
                try:await self.job(key,text,language,short)
                except HTTPException as error:
                    if error.status_code!=503:raise
                    # Keep the ticket: its GET can retry when capacity opens.
        return {'audio_url':urls[0],'audio_urls':urls} if urls else None
    def ticket(self,token):
        if not re.fullmatch('[A-Za-z0-9_-]{32}',token):return None
        try:
            item=json.loads((self.directory/'tickets'/(token+'.json')).read_text())
            if item['expires']<time.time() or item['key']!=self.key(item['text'],item['language'],item.get('short',False)):return None
            return item
        except (OSError,ValueError,KeyError):return None
    def lock(self,key):
        fd=os.open(self.directory/(key+'.lock'),os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);os.utime(fd,None);return fd
        except BlockingIOError:os.close(fd);return None
    async def job(self,key,text,language,short=False):
        if key in self.jobs:return self.jobs[key]
        if len(self.jobs)>=2:raise HTTPException(503,{'code':'speech_busy','retry_after':1},headers={'Retry-After':'1'})
        job=AudioJob();self.jobs[key]=job
        task=asyncio.create_task(self.pump(key,text,language,job,short));self.tasks.add(task);task.add_done_callback(self.tasks.discard)
        return job
    async def follow(self,key,job,short=False):
        offset=0;deadline=time.monotonic()+45;path=self.directory/(key+'.mp3');partial=self.directory/(key+'.stream')
        def read():
            try:
                if partial.stat().st_mtime_ns<(self.directory/(key+'.lock')).stat().st_mtime_ns:return b''
                with partial.open('rb') as audio:audio.seek(offset);return audio.read(65536)
            except OSError:return b''
        while time.monotonic()<deadline:
            if await asyncio.to_thread(self.valid_cache,key,short):
                data=await asyncio.to_thread(path.read_bytes)
                if len(data)>offset:await job.append(data[offset:])
                await job.finish();return
            data=await asyncio.to_thread(read)
            if data:offset+=len(data);await job.append(data);continue
            def failed():
                try:return (self.directory/(key+'.error')).stat().st_mtime_ns>=(self.directory/(key+'.lock')).stat().st_mtime_ns
                except OSError:return False
            if await asyncio.to_thread(failed):raise ValueError('Speech unavailable')
            await asyncio.sleep(.03)
        raise TimeoutError()
    async def pump(self,key,text,language,job,short=False):
        lock=None;partial_fd=None;path=self.directory/(key+'.mp3')
        try:
            deadline=time.monotonic()+45
            while lock is None:
                if await asyncio.to_thread(self.valid_cache,key,short):
                    job.cache='shared-hit';await job.append(await asyncio.to_thread(path.read_bytes));await job.finish();return
                lock=await asyncio.to_thread(self.lock,key)
                if lock is None:
                    job.cache='shared-stream';await self.follow(key,job,short);return
            if await asyncio.to_thread(self.valid_cache,key,short):
                job.cache='shared-hit';await job.append(await asyncio.to_thread(path.read_bytes));await job.finish();return
            path.unlink(missing_ok=True);path.with_suffix('.json').unlink(missing_ok=True)
            (self.directory/(key+'.error')).unlink(missing_ok=True)
            partial_fd=os.open(self.directory/(key+'.stream'),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            async with self.gate:
                client=self.client or shared();owned=client is None
                if owned:client=httpx.AsyncClient(timeout=httpx.Timeout(25,connect=5),follow_redirects=False)
                try:
                    async def raw_chunks():
                        # Reuse identical existing public speech, not a second paid call.
                        if short:
                            candidates=[self.directory/(self.key(text,language)+'.mp3')]
                            for raw_path in candidates:
                                try:data=await asyncio.to_thread(raw_path.read_bytes)
                                except OSError:continue
                                if data:
                                    from ilma_api.agent_audio import duration_ms
                                    try:measured=await duration_ms(data)
                                    except (ValueError,OSError,asyncio.TimeoutError):continue
                                    if not 0<measured<=30000:continue
                                    yield data;return
                        async with client.stream('POST','https://api.elevenlabs.io/v1/text-to-speech/'+settings.ELEVENLABS_VOICE_ID+'/stream',headers={'xi-api-key':settings.ELEVENLABS_API_KEY,'Accept':'audio/mpeg'},json={'text':pronounce(text,language),'model_id':settings.ELEVENLABS_MODEL,'voice_settings':{'speed':settings.TTS_SPEED}},timeout=httpx.Timeout(25,connect=5)) as response:
                            if response.status_code!=200:raise ValueError('Speech provider unavailable')
                            length=0
                            async for chunk in response.aiter_bytes():
                                length+=len(chunk)
                                if length>2*1024*1024:raise ValueError('Speech exceeds limit')
                                if chunk:yield chunk
                            if not length:raise ValueError('Speech empty')
                    async def download():
                        from ilma_api.agent_audio import trim_long_pauses
                        chunks=trim_long_pauses(raw_chunks()) if short else raw_chunks()
                        async for chunk in chunks:
                            await asyncio.to_thread(os.write,partial_fd,chunk)
                            await job.append(chunk)
                    await asyncio.wait_for(download(),25)
                finally:
                    if owned:await client.aclose()
            data=b''.join(job.chunks)
            from ilma_api.agent_audio import duration_ms
            measured=await duration_ms(data)
            if not measured or measured<0 or (short and measured>30000):raise ValueError('Speech duration is invalid')
            await asyncio.to_thread(self.atomic,path.with_suffix('.json'),json.dumps({'duration_ms':measured,'created':time.time(),'short':short,'tempo':1.0}).encode())
            await asyncio.to_thread(self.atomic,path,data)
            await job.finish()
        except asyncio.CancelledError:
            await job.finish(True);raise
        except Exception:
            await asyncio.to_thread(self.atomic,self.directory/(key+'.error'),str(time.time()).encode())
            await job.finish(True)
        finally:
            if partial_fd is not None:os.close(partial_fd);(self.directory/(key+'.stream')).unlink(missing_ok=True)
            if lock is not None:os.close(lock)
            self.jobs.pop(key,None)
    async def wait(self,ticket):
        descriptors=[await asyncio.to_thread(self.ticket,url.rsplit('/',1)[-1][:-4]) for url in ticket['audio_urls']]
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            ready=True
            for item in descriptors:
                if not item:return False
                key=item['key']
                if await asyncio.to_thread(self.valid_cache,key,item.get('short',False)):continue
                ready=False
                job=self.jobs.get(key)
                if job is not None and job.done.is_set() and job.failed:return False
                if job is None and await asyncio.to_thread((self.directory/(key+'.error')).is_file):return False
            if ready:return True
            await asyncio.sleep(.05)
        return False
    async def failed(self,ticket):
        for url in ticket['audio_urls']:
            item=await asyncio.to_thread(self.ticket,url.rsplit('/',1)[-1][:-4])
            if not item:return True
            key=item['key'];job=self.jobs.get(key)
            if job and job.done.is_set() and job.failed:return True
            if job is None and await asyncio.to_thread((self.directory/(key+'.error')).is_file):return True
        return False
    async def response(self,token):
        item=await asyncio.to_thread(self.ticket,token)
        if item is None:raise HTTPException(404,'Audio ticket expired or unavailable')
        path=self.directory/(item['key']+'.mp3')
        headers={'Cache-Control':'no-store, no-transform','X-Accel-Buffering':'no','X-ILMA-Cache':'hit'}
        if await asyncio.to_thread(self.valid_cache,item['key'],item.get('short',False)):return FileResponse(path,media_type='audio/mpeg',headers=headers)
        job=await self.job(item['key'],item['text'],item['language'],item.get('short',False));await job.ready.wait()
        if job.failed and not job.chunks:raise HTTPException(503,'Speech unavailable')
        headers['X-ILMA-Cache']=job.cache
        return StreamingResponse(job.stream(),media_type='audio/mpeg',headers=headers)
    async def close(self):
        for task in self.tasks:task.cancel()
        await asyncio.gather(*list(self.tasks),return_exceptions=True)

_store=None
def get_store():
    global _store
    if _store is None:_store=AudioStore()
    return _store
async def register_speech(texts,language,short=False):
    try:return await get_store().register(texts,language,short)
    except (OSError,HTTPException):return None
async def audio_response(token):return await get_store().response(token)
