import asyncio
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from ilma_api import settings
from ilma_api.db import Base, AppContent, AppQuestionLog, AppRateCounter
from ilma_api.voice_assets import CATALOG, load_approved, digest
from ilma_api.voice_answers import GroundedAnswer, verified, write_answer
from ilma_api.voice_numbers import normalize_numbers, pronounce, WORDS
from ilma_api.voice_pipeline import build_result
from ilma_api.voice_text import VoiceIntent
from ilma_api.voice_maintenance import cleanup
from ilma_api.replay_voice import read_manifest, summarize, public_transcript


class TestVoiceCompletion(unittest.TestCase):
    def test_empty_grounded_provider_choices_fall_back_to_facts(self):
        async def check():
            facts = [{'fact_id': 'npl', 'text': 'Bad loans 2.24%.'}]
            with patch.object(settings, 'META_MODEL_API_KEY', 'test-only'):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'choices': []}))) as client:
                    return await write_answer('What is NPL?', facts, 'en', client)
        self.assertEqual(asyncio.run(check()), 'Bad loans 2.24%.')

    def test_compound_numbers_and_full_speech_lexicon(self):
        self.assertEqual(len(WORDS), 100)
        for text, expected in [('দুই লাখ পঞ্চাশ হাজার', '250000 taka'), ('দেড় বছর', '18 months'),
                               ('৫,০০,০০০ টাকা', '500000 টাকা'), ('ছয় মাস', '6 months'),
                               ('two lakh', '200000 taka')]:
            self.assertEqual(normalize_numbers(text), expected)
        self.assertEqual(pronounce('১,০৯,০০০', 'bn'), 'এক লাখ নয় হাজার')
        self.assertIn('সাড়ে দশ শতাংশ', pronounce('FDR 10.5% PLC', 'bn'))
        self.assertEqual(pronounce('২২ অক্টোবর ২০২৬', 'bn'), 'বাইশে অক্টোবর দুই হাজার ছাব্বিশ')

    def test_grounded_answer_rejects_unsupported_claims(self):
        facts = [{'fact_id':'npl', 'text':'Bad loans 2.24% (2025)'}]
        for text, ids, expected in [('Bad loans 2.24%.', ['npl'], True), ('Bad loans 9%.', ['npl'], False),
                                     ('Bad loans seven percent.', ['npl'], False), ('Guaranteed safe.', ['npl'], False),
                                     ('Bad loans 2.24%.', ['invented'], False)]:
            answer = GroundedAnswer(sentences=[{'text':text, 'fact_ids':ids}])
            self.assertEqual(verified(answer, facts), expected)
        reported = [{'fact_id':'event', 'text':'Reported, unconfirmed. Penalty 2025', 'unconfirmed':True}]
        self.assertFalse(verified(GroundedAnswer(sentences=[{'text':'Penalty 2025', 'fact_ids':['event']}]), reported))

    def test_unreviewed_assets_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'manifest.json').write_text(json.dumps({'clips': {}}))
            with self.assertRaises(ValueError): load_approved(path)
            clips = {}
            for language in ['bn', 'en']:
                for key in CATALOG:
                    filename = language + '-' + key + '.opus'
                    fallback = language + '-' + key + '.mp3'
                    (path / filename).write_bytes(b'opus'); (path / fallback).write_bytes(b'mp3')
                    clips[language + ':' + key] = dict(file=filename, fallback_file=fallback, text='approved text', text_sha256=digest(b'approved text'), audio_sha256=digest(b'opus'), fallback_sha256=digest(b'mp3'), reviewed=True, reviewer='Native reviewer', reviewed_at='2026-10-27')
            (path / 'manifest.json').write_text(json.dumps({'clips': clips}))
            self.assertEqual(len(load_approved(path)['clips']), len(CATALOG) * 2)
            clips['bn:hint']['text'] = 'changed after review'
            (path / 'manifest.json').write_text(json.dumps({'clips': clips}))
            with self.assertRaises(ValueError): load_approved(path)

    def test_replay_thresholds_no_invented_pass(self):
        good = [{'bank_ok':True, 'language_ok':True, 'result_ms':3000, 'error':None}] * 20
        self.assertTrue(summarize(good, 'clean_bn', [{}] * 20)['passed'])
        self.assertFalse(summarize(good, 'real', [{}] * 20)['passed'], 'missing real-voice coverage must fail')
        bad = [{'bank_ok':False, 'language_ok':True, 'result_ms':3000, 'error':None}]
        self.assertTrue(summarize(bad, 'real', [{'condition':'quiet'}])['requires_manual_review'])
        self.assertNotIn('123456', public_transcript('account 123456 পাঁচ লাখ টাকা'))
        self.assertNotIn('500000', public_transcript('account 123456 পাঁচ লাখ টাকা'))
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'references.csv'
            manifest.write_text('file,institution_id,language\nmissing.wav,1,bn\n')
            with self.assertRaises(ValueError): read_manifest(manifest, directory)

    def test_reviewed_glossary_and_retention(self):
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                db.add(AppContent(content_key='glossary:প্রভিশন', lang='bn', version=1, text='Reviewed explanation.', status='draft'))
                db.add(AppQuestionLog(input_mode='voice', intent='unclear', outcome='error', created_at=datetime.utcnow()-timedelta(days=31)))
                db.add(AppRateCounter(key='expired', count=1, expires_at=datetime.utcnow()-timedelta(days=1)))
                db.commit()
                intent = VoiceIntent(intent='explain_word')
                self.assertEqual(build_result(intent, [], 'bn', db, 'প্রভিশন মানে কী?')['type'], 'no_data')
                db.query(AppContent).one().status='live'; db.commit()
                self.assertEqual(build_result(intent, [], 'bn', db, 'প্রভিশন মানে কী?')['type'], 'ask_answer')
                self.assertEqual(cleanup(db), (1, 1))
        finally: engine.dispose()


class TestGroundedProvider(unittest.IsolatedAsyncioTestCase):
    async def test_bad_model_numbers_retry_then_use_verified_template(self):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(200, json={'choices':[{'message':{'content':json.dumps({'sentences':[{'text':'Bad loans 99%', 'fact_ids':['npl']}]})}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with patch.object(settings, 'META_MODEL_API_KEY', 'test-only'), patch.object(settings, 'MUSE_SPARK_MODEL', 'muse-spark-1.3'):
                answer = await write_answer('NPL?', [{'fact_id':'npl','text':'Bad loans 2.24%'}], 'en', client)
        self.assertEqual(answer, 'Bad loans 2.24%')
        self.assertEqual(len(calls), 2)


class TestIntentProvider(unittest.IsolatedAsyncioTestCase):
    async def test_intent_schema_and_institution_whitelist(self):
        from ilma_api.voice_pipeline import understand
        from ilma_api.voice_text import VoiceContext
        candidate = {'id': 7, 'alias': 'Sample Bank', 'confidence': 1}
        for requested, should_pass in [([7], True), ([999], False)]:
            def respond(request):
                payload = json.loads(request.content)
                self.assertEqual(payload['temperature'], 0)
                self.assertEqual(payload['response_format']['type'], 'json_schema')
                question = json.loads(payload['messages'][1]['content'])['question']
                self.assertIn('200000', question)
                self.assertIn('12 months', question)
                return httpx.Response(200, json={'choices':[{'message':{'content':json.dumps({'intent':'service_compare', 'institution_ids':requested, 'product':'fdr', 'card_tier':None, 'amount_bdt':200000, 'period_months':12})}}]})
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                with patch.object(settings, 'META_MODEL_API_KEY', 'test-only'):
                    if should_pass:
                        result = await understand('দুই লাখ এক বছর FDR', [candidate], VoiceContext(), client)
                        self.assertEqual(result.institution_ids, [7])
                    else:
                        from ilma_api.voice import VoiceError
                        with self.assertRaises(VoiceError): await understand('দুই লাখ এক বছর FDR', [candidate], VoiceContext(), client)
