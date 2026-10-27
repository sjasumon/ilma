import io
import json
import unittest
import importlib.util
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql
from pydantic import ValidationError
from ilma_api.db import Base, AppQuestionLog, AppRateCounter, Institution
from ilma_api.voice import VoiceError, convert_audio
from ilma_api.voice_text import clean_transcript, decide_language, normalize_numbers, normalize_alias, match_candidates, VoiceIntent, VoiceContext
from ilma_api.voice_pipeline import consume_question, log_outcome, understand, pronounce
from ilma_api.migrate_voice import add_aliases


def bank(id, en, bn, aliases=()):
    return dict(id=id, slug=en.lower().replace(' ', '-'), name_en=en, name_bn=bn, type='bank', coverage='licence_only', aliases=list(aliases))

BANKS = [bank(1, 'Pubali Bank', 'পূবালী ব্যাংক', ['উবালি', 'কুবালি', 'ভ্যালি']),
         bank(2, 'Eastern Bank', 'ইস্টার্ন ব্যাংক', ['EBL']),
         bank(3, 'IFIC Bank', 'আইএফআইসি ব্যাংক', ['IFIC']),
         bank(4, 'Janata Bank', 'জনতা ব্যাংক'),
         bank(5, 'Mercantile Bank', 'মার্কেন্টাইল ব্যাংক', ['arcantile']),
         bank(6, 'Al-Arafah Islami Bank', 'আল আরাফাহ ইসলামী ব্যাংক', ['আল-আরাফাহ Islami Bank']),
         bank(7, 'Prime Bank', 'প্রাইম ব্যাংক'), bank(8, 'City Bank', 'সিটি ব্যাংক'),
         bank(9, 'NCC Bank', 'এনসিসি ব্যাংক'), bank(10, 'Sonali Bank', 'সোনালী ব্যাংক')]


def exact_score(left, right):
    # Injection tests normalization/alias routing independently of optional library.
    return 100 if left == right else 0


class TestVoiceText(unittest.TestCase):
    def test_cleaner_examples(self):
        for before, after in [('সোনালীসোনালী', 'সোনালী'), ('IFICIFIC', 'IFIC'), ('সমস্যা সমস্যা', 'সমস্যা'),
                              ('টাকা টাকা??.:!', 'টাকা'), ('जनता बैंक', 'জনতা ব্যাংক'), ('  Eastern Bank?? ', 'Eastern Bank')]:
            self.assertEqual(clean_transcript(before), after)
        with self.assertRaises(VoiceError): clean_transcript('नमस्ते बैंक')

    def test_all_test_mishearings(self):
        for text, id in [('উবালি', 1), ('কুবালি', 1), ('ভ্যালি', 1), ('arcantile', 5),
                         ('আল-আরাফাহ Islami Bank', 6), ('Eastern Bank কি নিরাপদ?', 2),
                         ('IFIC Bank-এর FDR rate কত?', 3), ('जनता बैंक', 4)]:
            with self.subTest(text=text):
                found = match_candidates(clean_transcript(text), BANKS, scorer=exact_score)
                self.assertEqual(found[0]['id'], id)
        self.assertEqual(match_candidates('unknown institution', BANKS, scorer=exact_score), [])

    def test_language_rule(self):
        for text, expected in [('Eastern Bank কি নিরাপদ?', 'bn'), ('IFIC Bank-এর FDR rate কত?', 'bn'),
                               ('is জনতা ব্যাংক safe?', 'en'), ('Is Sonali Bank safe?', 'en')]:
            candidates = match_candidates(text, BANKS, scorer=exact_score)
            self.assertEqual(decide_language(text, candidates, 'bn'), expected)

    def test_short_names_require_bank_or_confirmation(self):
        for text, confirm in [('Prime', True), ('Prime Bank', False), ('Is City Bank safe?', False), ('NCC', True)]:
            self.assertEqual(match_candidates(text, BANKS, scorer=exact_score)[0]['confirm'], confirm)

    def test_number_normalizer_and_schema(self):
        self.assertEqual(normalize_numbers('দুই লাখ'), '200000 taka')
        self.assertEqual(normalize_numbers('এক বছর'), '12 months')
        self.assertEqual(normalize_numbers('৫০০০০০'), '500000')
        with self.assertRaises(ValidationError): VoiceIntent(intent='invented')
        with self.assertRaises(ValidationError): VoiceIntent(intent='rates', product='crypto')
        with self.assertRaises(ValidationError): VoiceContext(ui_lang='unknown')
        self.assertEqual(normalize_alias('IFIC Bank-এর PLC'), 'ific')
        self.assertEqual(pronounce('২,০০,০০০ PLC 10.5%', 'bn').strip(), 'দুই লাখ  সাড়ে দশ শতাংশ')

    @unittest.skipUnless(importlib.util.find_spec('rapidfuzz'), 'RapidFuzz cannot be installed in this restricted workspace')
    def test_actual_rapidfuzz_scoring(self):
        self.assertEqual(match_candidates('Eastrn Bank', BANKS)[0]['id'], 2)

    def test_mysql_schema_and_private_logs(self):
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                import time
                log_outcome(db, 'voice', 'rates', 1, 'answered', time.monotonic(), 'anonymous')
                log = db.query(AppQuestionLog).one()
                self.assertEqual(log.text_redacted, '[input omitted]')
                self.assertEqual(log.fact_ids, [])
                for _ in range(20): consume_question(db, 'test-device')
                with self.assertRaises(VoiceError): consume_question(db, 'test-device')
                self.assertEqual(db.query(AppRateCounter).one().count, 20)
                db.add(Institution(id=1, slug='pubali', name_bn='পূবালী ব্যাংক', name_en='Pubali Bank', type='bank', coverage='licence_only'))
                db.commit()
                self.assertGreater(add_aliases(db), 0); db.commit()
                self.assertEqual(add_aliases(db), 0)
            ddl = str(CreateTable(AppQuestionLog.__table__).compile(dialect=mysql.dialect()))
            self.assertIn('utf8mb4', ddl)
            self.assertNotIn('account_number', ddl)
            self.assertNotIn('amount_bdt', ddl)
        finally: engine.dispose()


class TestVoiceProviders(unittest.IsolatedAsyncioTestCase):
    async def test_bank_name_skips_spark(self):
        matches = match_candidates('Eastern Bank', BANKS, scorer=exact_score)
        with patch('ilma_api.voice_pipeline.httpx.AsyncClient') as client:
            result = await understand('Eastern Bank', matches, VoiceContext())
            client.assert_not_called()
        self.assertEqual(result.institution_ids, [2])

    async def test_ffmpeg_uses_memory_pipes(self):
        pcm = b'\0\0' * 24000
        process = AsyncMock()
        process.returncode = 0
        process.communicate.return_value = (pcm, None)
        with patch('ilma_api.voice.shutil.which', return_value='/usr/bin/ffmpeg'), patch('ilma_api.voice.asyncio.create_subprocess_exec', return_value=process) as start:
            result = await convert_audio(b'webm', 'audio/webm')
            args = start.call_args.args
            self.assertIn('pipe:0', args); self.assertIn('pipe:1', args)
            self.assertIn('-map_metadata', args)
            self.assertNotIn('output.wav', args)
        import wave
        with wave.open(io.BytesIO(result)) as audio:
            self.assertEqual(audio.getframerate(), 24000)
            self.assertEqual(audio.getnchannels(), 1)
