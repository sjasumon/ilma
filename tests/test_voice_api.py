import io
import json
import unittest
import wave
from unittest.mock import patch, AsyncMock

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from ilma_api import voice, settings
from ilma_api.db import Base, Institution, InstitutionAlias
from ilma_api.main import voice_input


def wav(seconds=1, rate=24000, channels=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as recording:
        recording.setnchannels(channels)
        recording.setsampwidth(2)
        recording.setframerate(rate)
        recording.writeframes(b'\x01\x00' * int(seconds * rate) * channels)
    return output.getvalue()


def multipart(audio, language='bn'):
    request = httpx.Request('POST', 'http://test/v1/ask', files={
        'audio': ('recording.wav', audio, 'audio/wav'),
        'language': (None, language),
    })
    return request.headers['content-type'], request.read()


def incoming(audio, language='bn'):
    request = httpx.Request('POST', 'http://test/v1/voice', files={
        'audio': ('recording.wav', audio, 'audio/wav'),
        'context': (None, json.dumps({'ui_lang': language, 'speak': False})),
    })
    content_type, body = request.headers['content-type'], request.read()
    sent = False
    async def receive():
        nonlocal sent
        if sent: return {'type': 'http.disconnect'}
        sent = True
        return {'type': 'http.request', 'body': body, 'more_body': False}
    return Request({'type': 'http', 'method': 'POST', 'path': '/v1/voice',
                    'headers': [(b'content-type', content_type.encode())]}, receive)


BANKS = [
    {'id': 101, 'slug': 'eastern-bank', 'name_bn': 'ইস্টার্ন ব্যাংক পিএলসি', 'name_en': 'Eastern Bank PLC',
     'type': 'bank', 'coverage': 'full', 'aliases': ['ইস্টার্ন ব্যাংক', 'EBL']},
    {'id': 102, 'slug': 'pubali-bank', 'name_bn': 'পূবালী ব্যাংক পিএলসি', 'name_en': 'Pubali Bank PLC',
     'type': 'bank', 'coverage': 'full', 'aliases': ['পূবালী ব্যাংক', 'Pubali']},
    {'id': 103, 'slug': 'dutch-bangla-bank', 'name_bn': 'ডাচ-বাংলা ব্যাংক পিএলসি', 'name_en': 'Dutch-Bangla Bank PLC',
     'type': 'bank', 'coverage': 'full', 'aliases': ['ডাচ বাংলা ব্যাংক', 'DBBL']},
]


class TestVoiceValidation(unittest.TestCase):
    def test_bank_matches_input_never_defaults(self):
        for text, expected in [('How is Pubali Bank?', [102]), ('Pubali', [102]), ('পূবালী ব্যাংকের অবস্থা কী?', [102]), ('পূবালী ব্যাংক কেমন আছে?', [102]),
                               ('DBBL', [103]), ('ডাচ বাংলা ব্যাংক', [103]), ('EBL', [101]),
                               ('Eastern Bank and Pubali Bank', [101, 102]), ('unknown bank', []),
                               ('a bank please', []), ('', []), ('eblast', [])]:
            with self.subTest(text=text):
                self.assertEqual([bank['id'] for bank in __import__('ilma_api.voice_text', fromlist=['match_candidates']).match_candidates(text, BANKS, scorer=lambda a, b: 100 if a == b else 0)], expected)

    def test_multipart_stays_in_memory_and_validates(self):
        audio = wav()
        from ilma_api.voice_pipeline import parse_request
        request = httpx.Request('POST', 'http://test/v1/voice', files={'audio': ('recording.wav', audio, 'audio/wav'), 'context': (None, '{"ui_lang":"en"}')})
        result = parse_request(request.headers['content-type'], request.read(), 'voice')
        self.assertEqual(result[0], audio)
        self.assertEqual(result[3].ui_lang, 'en')
        for invalid in [b'not wav', wav(16), wav(channels=2), wav(rate=48000), audio[:-20]]:
            with self.subTest(length=len(invalid)), self.assertRaises(voice.VoiceError):
                voice.validate_wav(invalid)
        with self.assertRaises(voice.VoiceError):
            parse_request(*multipart(audio, 'invalid'), 'voice')
        with self.assertRaises(voice.VoiceError):
            parse_request('multipart/form-data', b'x' * (voice.MAX_UPLOAD_BYTES + 1), 'voice')


class TestMetaVoice(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        sleep = patch("ilma_api.voice.asyncio.sleep", new_callable=AsyncMock)
        sleep.start(); self.addCleanup(sleep.stop)
        self.key = patch.object(settings, 'MUSE_VOICE_API_KEY', 'test-key-do-not-leak')
        self.url = patch.object(settings, 'MUSE_VOICE_API_URL', 'https://api.meta.ai/v1/asr/transcribe')
        self.model = patch.object(settings, 'MUSE_VOICE_MODEL', 'muse-voice-transcribe-1.0')
        for item in (self.key, self.url, self.model):
            item.start()
            self.addCleanup(item.stop)

    async def test_meta_wire_format(self):
        def respond(request):
            self.assertEqual(str(request.url), 'https://api.meta.ai/v1/asr/transcribe')
            self.assertEqual(request.headers['authorization'], 'Bearer test-key-do-not-leak')
            # Standard MIME parser inspects request fields without writing a file.
            from email.parser import BytesParser
            from email import policy
            message = BytesParser(policy=policy.default).parsebytes(
                b'Content-Type: ' + request.headers['content-type'].encode() + b'\r\n\r\n' + request.read())
            parts = {part.get_param('name', header='content-disposition'): part.get_payload(decode=True)
                     for part in message.iter_parts()}
            config = json.loads(parts['request'])
            self.assertEqual(config['model'], 'muse-voice-transcribe-1.0')
            self.assertEqual(config['audioEncoding'], 'WAV')
            self.assertEqual(config['languageBias'], ['Bengali'])
            self.assertEqual(config['mode'], 'PUSH_TO_TALK')
            self.assertNotIn('keywords', config)
            self.assertEqual(parts['audio'], wav())
            return httpx.Response(200, json={'transcript': 'পূবালী ব্যাংক'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            self.assertEqual(await voice.transcribe(wav(), 'bn', ['Pubali'], client), 'পূবালী ব্যাংক')

    async def test_retry_schedule_and_english_bias(self):
        calls = []
        def respond(request):
            calls.append(request)
            if len(calls) < 3: return httpx.Response(429 if len(calls) == 1 else 500)
            self.assertIn(b'Bengali', request.read())
            self.assertIn(b'English', request.read())
            self.assertNotIn(b'keywords', request.read())
            return httpx.Response(200, json={'transcript':'Sample Bank'})
        with patch('ilma_api.voice.asyncio.sleep', new_callable=AsyncMock) as sleep:
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                self.assertEqual(await voice.transcribe(wav(), 'en', [], client), 'Sample Bank')
            self.assertEqual([call.args[0] for call in sleep.await_args_list], [2, 4])
        self.assertEqual(len(calls), 3)

    async def test_upstream_errors_do_not_expose_key_or_response(self):
        for status, expected in [(401, 'voice_unavailable'), (500, 'voice_unavailable'), (429, 'voice_rate_limited')]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, text='secret-provider-detail'))) as client:
                with self.assertRaises(voice.VoiceError) as caught:
                    await voice.transcribe(wav(), 'en', [], client)
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn('secret', str(caught.exception))
        for payload, expected in [({'transcript': ''}, 'no_speech'), ({'unexpected': 'value'}, 'voice_unavailable')]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))) as client:
                with self.assertRaises(voice.VoiceError) as caught:
                    await voice.transcribe(wav(), 'en', [], client)
                self.assertEqual(caught.exception.code, expected)

    async def test_timeout_and_missing_config(self):
        def timeout(request):
            raise httpx.ReadTimeout('private details')
        async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
            with self.assertRaises(voice.VoiceError) as caught:
                await voice.transcribe(wav(), 'bn', [], client)
            self.assertEqual(caught.exception.code, 'voice_timeout')
        with patch.object(settings, 'MUSE_VOICE_API_KEY', ''):
            with self.assertRaises(voice.VoiceError) as caught:
                await voice.transcribe(wav(), 'bn', [])
            self.assertEqual(caught.exception.status, 503)

    async def test_upload_meta_and_actual_database_search(self):
        engine = create_engine('sqlite://', poolclass=StaticPool)
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)
        original_client = httpx.AsyncClient
        try:
            with sessions() as db:
                for bank in BANKS:
                    db.add(Institution(**{key: value for key, value in bank.items() if key != 'aliases'}))
                    for alias in bank['aliases']:
                        db.add(InstitutionAlias(institution_id=bank['id'], alias=alias, lang='en'))
                db.commit()
                from functools import partial
                from ilma_api.voice_text import match_candidates
                for text, expected in [('Pubali Bank', [102]), ('ডাচ বাংলা ব্যাংক', [103]), ('unknown bank', []),
                                       ('Eastern Bank and Pubali Bank', [101, 102])]:
                    def respond(request):
                        if str(request.url).endswith('/asr/transcribe'):
                            return httpx.Response(200, json={'transcript': text})
                        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'intent':'unclear', 'institution_ids':[]})}}]})
                    def factory(**kwargs):
                        return original_client(transport=httpx.MockTransport(respond))
                    scorer = lambda a, b: 100 if a == b else 0
                    with patch('ilma_api.voice.httpx.AsyncClient', side_effect=factory), patch('ilma_api.voice_pipeline.convert_audio', new=AsyncMock(return_value=wav())), patch('ilma_api.voice_pipeline.match_candidates', new=partial(match_candidates, scorer=scorer)):
                        response = await voice_input(incoming(wav()), db)
                        events = [part async for part in response.body_iterator]
                    parsed = [(part.split('\n')[0], json.loads(part.split('data: ', 1)[1])) for part in events]
                    self.assertEqual(parsed[0][1]['text'], text)
                    matched = next(data['institution_ids'] for event, data in parsed if event == 'event: match')
                    self.assertEqual(matched, expected)
                from sqlalchemy.exc import OperationalError
                with patch('ilma_api.main.get_institution_index', side_effect=OperationalError('private details', {}, Exception())):
                    unavailable = await voice_input(incoming(wav()), db)
                self.assertEqual(unavailable.status_code, 503)
                self.assertNotIn('private details', unavailable.body.decode())

        finally:
            engine.dispose()
