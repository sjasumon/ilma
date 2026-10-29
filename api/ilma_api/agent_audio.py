"""Measure short agent speech; trim small duration overruns with bounded tempo.
No truncation, user audio storage, or aggressive acceleration of long answers.
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
        if original>20000:
            tempo=original/19000
            if tempo<=1.15:
                encoded=await process(data,['-map_metadata','-1','-af',f'atempo={tempo:.6f}','-c:a','libmp3lame','-b:a','96k','-f','mp3','pipe:1'])
                measured=await duration_ms(encoded)
                if measured<original:
                    url='data:audio/mpeg;base64,'+base64.b64encode(encoded).decode()
                    metadata.update(duration_ms=measured,tempo=round(tempo,4))
            if metadata['duration_ms']>20000:metadata['status']='over_target'
        return url,metadata
    except (ValueError,OSError,VoiceError,asyncio.TimeoutError):
        return url,{'status':'measurement_unavailable'}


async def trim_long_pauses(chunks):
    """Stream MP3 through a conservative silence filter; retain voiced samples.
    Gaps below 150 ms stay intact; longer digital pauses retain a short break.
    A 3% pitch-preserving pace adjustment gives the ten-second budget headroom.
    Voiced samples stay complete; processing remains a streaming pipe.
    """
    process=await asyncio.create_subprocess_exec(ffmpeg_executable(),'-hide_banner','-loglevel','error','-nostdin','-protocol_whitelist','pipe','-f','mp3','-probesize','32','-analyzeduration','0','-i','pipe:0','-af','silenceremove=stop_periods=-1:stop_duration=0.15:stop_threshold=-60dB:stop_silence=0.05:detection=peak,atempo=1.03','-map_metadata','-1','-ac','1','-ar','24000','-c:a','libmp3lame','-b:a','96k','-flush_packets','1','-f','mp3','pipe:1',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    async def feed():
        try:
            async for chunk in chunks:
                process.stdin.write(chunk);await process.stdin.drain()
        finally:process.stdin.close()
    feeder=asyncio.create_task(feed());length=0
    try:
        while chunk:=await process.stdout.read(16384):
            length+=len(chunk)
            if length>2*1024*1024:raise ValueError('Speech exceeds limit')
            yield chunk
        await feeder
        if await process.wait() or not length:raise ValueError('Speech normalization failed')
    finally:
        if not feeder.done():feeder.cancel()
        await asyncio.gather(feeder,return_exceptions=True)
        if process.returncode is None:
            try:process.kill()
            except ProcessLookupError:pass
            await process.wait()
