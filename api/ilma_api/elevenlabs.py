"""Ordered speech accounts with sanitized failures and a fifteen-minute cooldown."""
import asyncio,hashlib,logging,re,time
from contextlib import asynccontextmanager
import httpx
from ilma_api import settings
STATUSES={401,402,403,429,500,502,503,504}
CODES={'quota_exceeded','too_many_concurrent_requests','system_busy','invalid_api_key','voice_not_found'}
_failed={}
log=logging.getLogger(__name__)
class SpeechFailure(ValueError):
    def __init__(self,failures):
        self.failures=failures
        super().__init__('; '.join(name+': '+reason for name,reason in failures) or 'No configured speech accounts')
def accounts():
    result=[]
    for index,name in enumerate(('primary','secondary','tertiary'),1):
        key=getattr(settings,f'ELEVENLABS_API_KEY_{index}','');voice=getattr(settings,f'ELEVENLABS_VOICE_ID_{index}','')
        if key and re.fullmatch(r'[A-Za-z0-9_-]+',voice):result.append((name,key,voice))
    # Existing installations keep working until numbered accounts are configured.
    if not result and settings.ELEVENLABS_API_KEY and re.fullmatch(r'[A-Za-z0-9_-]+',settings.ELEVENLABS_VOICE_ID):
        result=[('primary',settings.ELEVENLABS_API_KEY,settings.ELEVENLABS_VOICE_ID)]
    return result
def identity(key,voice):return hashlib.sha256((key+'\0'+voice).encode()).hexdigest()
def reason(response):
    try:
        data=response.json();detail=data.get('detail',data.get('error',data))
        code=detail.get('status',detail.get('code','')) if isinstance(detail,dict) else ''
    except (ValueError,TypeError,AttributeError):code=''
    code=code if code in CODES else ''
    return 'http_'+str(response.status_code)+(('/'+code) if code else ''),code
@asynccontextmanager
async def deadline(seconds):
    task=asyncio.current_task();expired=False
    def cancel():
        nonlocal expired
        expired=True;task.cancel()
    timer=asyncio.get_running_loop().call_later(seconds,cancel)
    try:
        yield
    except asyncio.CancelledError:
        if expired:raise TimeoutError() from None
        raise
    finally:timer.cancel()
async def chunks(client,text,*,stream=True,voice_settings=None,used=None):
    failures=[]
    for name,key,voice in accounts():
        token=identity(key,voice)
        if _failed.get(token,0)>time.monotonic():failures.append((name,'cooldown'));continue
        sent=False
        try:
            async with deadline(25):
                async with client.stream('POST','https://api.elevenlabs.io/v1/text-to-speech/'+voice+('/stream' if stream else ''),headers={'xi-api-key':key,'Accept':'audio/mpeg'},json={'text':text,'model_id':settings.ELEVENLABS_MODEL,**({'voice_settings':voice_settings} if voice_settings else {})},timeout=httpx.Timeout(25,connect=5)) as response:
                    if response.status_code!=200:
                        await response.aread();why,code=reason(response)
                        failures.append((name,why))
                        if response.status_code in {400,422} or (response.status_code not in STATUSES and code not in CODES):raise SpeechFailure(failures)
                        _failed[token]=time.monotonic()+900
                        log.warning('speech_account_failed account=%s reason=%s',name,why);continue
                    if not stream:
                        audio=await response.aread()
                        if not audio or len(audio)>2*1024*1024:raise SpeechFailure([(name,'invalid_audio')])
                        if used is not None:used.update(key_name_used=name,voice_id=voice)
                        yield audio;return
                    length=0
                    async for chunk in response.aiter_bytes():
                        if not chunk:continue
                        length+=len(chunk)
                        if length>2*1024*1024:raise SpeechFailure([(name,'audio_too_large')])
                        if used is not None:used.update(key_name_used=name,voice_id=voice)
                        sent=True;yield chunk
                    if not length:raise SpeechFailure([(name,'empty_audio')])
                    return
        except (TimeoutError,httpx.TimeoutException):
            failures.append((name,'timeout'));_failed[token]=time.monotonic()+900
            log.warning('speech_account_failed account=%s reason=timeout',name)
            # Never concatenate another account's recording after audible bytes.
            if sent:raise SpeechFailure(failures) from None
        except httpx.HTTPError:
            raise SpeechFailure(failures+[(name,'transport_error')]) from None
    raise SpeechFailure(failures)
async def synthesize(client,text,*,voice_settings=None):
    used={};data=b''.join([part async for part in chunks(client,text,stream=False,voice_settings=voice_settings,used=used)])
    return data,used
