"""Measure speech without changing natural pacing.
No truncation, silence gating, or post-synthesis tempo adjustment.
"""
import asyncio
import base64
import re
from ilma_api.voice import ffmpeg_executable, VoiceError

async def process(data,arguments):
    process=await asyncio.create_subprocess_exec(ffmpeg_executable(),'-hide_banner','-loglevel','error','-nostdin','-protocol_whitelist','pipe','-i','pipe:0',*arguments,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    try:
        output,_=await asyncio.wait_for(process.communicate(data),5)
    except (asyncio.TimeoutError,asyncio.CancelledError):
        if process.returncode is None:
            try:process.kill()
            except ProcessLookupError:pass
        await process.wait();raise
    if process.returncode:raise ValueError('Audio measurement unavailable')
    return output

async def duration_ms(data):
    output=await process(data,['-progress','pipe:1','-f','null','-'])
    matches=re.findall(rb'out_time_us=(\d+)',output)
    if not matches:raise ValueError('Audio duration unavailable')
    return round(int(matches[-1])/1000)

async def normalize_agent_audio(url):
    if not url:return url,{'status':'unavailable'}
    try:
        data=base64.b64decode(url.partition(',')[2],validate=True)
        original=await duration_ms(data)
        metadata={'duration_ms':original,'original_duration_ms':original,'tempo':1.0,'status':'ok'}
        if original>30000:metadata['status']='over_target'
        return url,metadata
    except (ValueError,OSError,VoiceError,asyncio.TimeoutError):
        return url,{'status':'measurement_unavailable'}


async def trim_long_pauses(chunks):
    """Compatibility entry point: preserve natural provider pacing unchanged."""
    length=0
    async for chunk in chunks:
        length+=len(chunk)
        if length>2*1024*1024:raise ValueError('Speech exceeds limit')
        yield chunk
