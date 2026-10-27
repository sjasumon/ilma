import json
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ilma_api import settings
from ilma_api.db import VoiceDiagnostic
from ilma_api.voice_diagnostics import start_capture, capture_event, save_capture


class TestDiagnostics(unittest.TestCase):
    def test_production_never_captures_even_with_capture_switch(self):
        with patch.object(settings, 'ILMA_ENV', 'production'), patch.object(settings, 'VOICE_DIAGNOSTICS_ENABLED', True):
            self.assertIsNone(start_capture(b'private audio', 'audio/webm', 'bn'))

    def test_development_requires_explicit_switch(self):
        with patch.object(settings, 'ILMA_ENV', 'development'), patch.object(settings, 'VOICE_DIAGNOSTICS_ENABLED', False):
            self.assertIsNone(start_capture(b'private audio', 'audio/webm', 'bn'))

    def test_pairs_audio_raw_asr_and_errors_without_speech_payload(self):
        engine = create_engine('sqlite://')
        VoiceDiagnostic.__table__.create(engine)
        with patch.object(settings, 'ILMA_ENV', 'development'), patch.object(settings, 'VOICE_DIAGNOSTICS_ENABLED', True):
            capture = start_capture(b'original audio', 'audio/webm', 'bn')
            capture['meta_transcript'] = 'नमस्ते बैंक'
            capture_event(capture, 'event: error\ndata: {"code":"transcript_language_mismatch"}\n\n')
            capture_event(capture, 'event: speech\ndata: {"audio_url":"private-base64"}\n\n')
            save_capture(capture, engine)
            self.assertEqual(capture, {})
            with Session(engine) as db:
                row = db.scalars(select(VoiceDiagnostic)).one()
                self.assertEqual(row.audio, b'original audio')
                self.assertEqual(row.meta_transcript, 'नमस्ते बैंक')
                self.assertEqual(row.events[0]['data']['code'], 'transcript_language_mismatch')
                self.assertNotIn('private-base64', json.dumps(row.events))
        engine.dispose()
