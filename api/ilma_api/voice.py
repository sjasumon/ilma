"""Short in-memory recordings -> Meta transcription -> released-bank matches."""
import io
import asyncio
import shutil
import json
import unicodedata
import wave

import httpx
from ilma_api import settings

MAX_AUDIO_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = MAX_AUDIO_BYTES + 16384
MAX_SECONDS = 15


class VoiceError(Exception):
    def __init__(self, code, status, bn, en):
        self.code, self.status, self.bn, self.en = code, status, bn, en
        super().__init__(code)  # Never include provider responses or credentials.


def validate_wav(audio: bytes):
    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError('audio_too_large', 413, 'রেকর্ডিংটি খুব বড়।', 'Recording is too large.')
    try:
        with wave.open(io.BytesIO(audio), 'rb') as recording:
            rate, frames = recording.getframerate(), recording.getnframes()
            if recording.getnchannels() != 1 or recording.getsampwidth() != 2 or rate not in (16000, 24000):
                raise ValueError('format')
            if not 0 < frames <= MAX_SECONDS * rate or recording.getcomptype() != 'NONE':
                raise ValueError('duration')
            if len(recording.readframes(frames)) != frames * 2:
                raise ValueError('truncated')
    except (wave.Error, EOFError, ValueError):
        raise VoiceError('invalid_audio', 400, 'সর্বোচ্চ ১৫ সেকেন্ডের রেকর্ডিং পাঠান।',
                         'Use a recording up to 15 seconds, mono 16-bit PCM WAV at 16 or 24 kHz.') from None


async def transcribe(audio: bytes, language: str, keywords: list[str], client=None) -> str:
    if not all((settings.MUSE_VOICE_API_KEY, settings.MUSE_VOICE_API_URL, settings.MUSE_VOICE_MODEL)):
        raise VoiceError('voice_unconfigured', 503, 'ভয়েস সেবা এখনও চালু হয়নি।', 'Voice service is not configured.')
    validate_wav(audio)
    if 'contributor' in settings.MUSE_VOICE_MODEL.lower():
        raise VoiceError('voice_unconfigured', 503, 'ভয়েস সেবার সেটিংস সঠিক নয়।', 'Contributor models cannot process user audio.')
    request = {
        'model': settings.MUSE_VOICE_MODEL, 'audioEncoding': 'WAV', 'mode': 'PUSH_TO_TALK',
        'languageBias': ['Bengali'] if language == 'bn' else ['Bengali', 'English'],
    }
    async def send(http):
        return await http.post(
            settings.MUSE_VOICE_API_URL,
            headers={'Authorization': f'Bearer {settings.MUSE_VOICE_API_KEY}', 'Accept': 'application/json'},
            files={'request': (None, json.dumps(request, ensure_ascii=False), 'application/json'),
                   'audio': ('recording.wav', audio, 'audio/wav')},
        )
    async def send_with_retry(http):
        for attempt in range(3):
            response = await asyncio.wait_for(send(http), 8)
            if response.status_code not in (429, 500) or attempt == 2:
                return response
            await asyncio.sleep(2 * (attempt + 1))
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8, connect=5), follow_redirects=False) as http:
                response = await send_with_retry(http)
        else:
            response = await send_with_retry(client)
    except (httpx.TimeoutException, asyncio.TimeoutError):
        raise VoiceError('voice_timeout', 504, 'ভয়েস সেবায় সময় বেশি লাগছে। আবার চেষ্টা করুন।', 'Transcription timed out. Try again.') from None
    except httpx.HTTPError:
        raise VoiceError('voice_unavailable', 502, 'ভয়েস সেবায় সংযোগ করা যায়নি।', 'Could not reach the transcription service.') from None
    if response.status_code == 429:
        raise VoiceError('voice_rate_limited', 429, 'একটু পরে আবার চেষ্টা করুন।', 'Voice service is busy. Try again shortly.')
    if response.status_code != 200:
        raise VoiceError('voice_unavailable', 502, 'ভয়েস সেবা রেকর্ডিংটি পড়তে পারেনি।', 'The transcription service could not process this recording.')
    try:
        text = response.json()['transcript']
        if not isinstance(text, str) or len(text) > 5000:
            raise ValueError('transcript')
    except (ValueError, KeyError, TypeError):
        raise VoiceError('voice_unavailable', 502, 'ভয়েস সেবার উত্তরটি পড়া যায়নি।', 'Invalid response from the transcription service.') from None
    text = unicodedata.normalize('NFC', text).strip()
    if not text:
        raise VoiceError('no_speech', 422, 'কথা শোনা যায়নি। আবার বলুন।', 'No speech was recognized. Please try again.')
    return text


def ffmpeg_executable():
    executable = shutil.which(settings.FFMPEG_BINARY)
    if not executable:
        try:
            import imageio_ffmpeg
            executable = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            raise VoiceError('voice_dependency_missing', 503, 'ভয়েস সেবা প্রস্তুত নয়।', 'ffmpeg is required for voice recording.') from None
    return executable


async def convert_audio(audio: bytes, mime: str) -> bytes:
    """Convert browser audio using pipes only; no audio file touches disk."""
    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError('audio_too_large', 413, 'রেকর্ডিংটি খুব বড়।', 'Recording is too large.')
    if mime not in {'audio/webm', 'audio/mp4', 'audio/wav', 'audio/x-wav'}:
        raise VoiceError('invalid_audio', 415, 'অডিওর ধরন সমর্থিত নয়।', 'Unsupported recording format.')
    executable = ffmpeg_executable()
    try:
        process = await asyncio.create_subprocess_exec(
            executable, '-hide_banner', '-loglevel', 'error', '-nostdin', '-protocol_whitelist', 'pipe',
            '-i', 'pipe:0', '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', '-map_metadata', '-1',
            '-t', '15', '-f', 's16le', 'pipe:1', stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    except OSError:
        raise VoiceError('voice_dependency_missing', 503, 'ভয়েস সেবা প্রস্তুত নয়।', 'The server could not start ffmpeg.') from None
    try:
        pcm, _ = await asyncio.wait_for(process.communicate(audio), 8)
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise VoiceError('invalid_audio', 400, 'অডিওটি পড়া যায়নি।', 'Audio conversion timed out.') from None
    if process.returncode or not pcm or len(pcm) > 24000 * 15 * 2:
        raise VoiceError('invalid_audio', 400, 'অডিওটি পড়া যায়নি।', 'Could not decode this recording.')
    output = io.BytesIO()
    with wave.open(output, 'wb') as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(24000)
        recording.writeframes(pcm)
    return output.getvalue()
