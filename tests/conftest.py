"""Test startup explicitly uses the test environment; never production secrets."""
import os
os.environ['ILMA_ENV']='test'
os.environ['HUMAN_VOICE_ENABLED']='false'
os.environ['DB_NAME']='ilma'
os.environ['DB_USERNAME']='synthetic-test-user'
for key in ('META_MODEL_API_KEY','MUSE_VOICE_API_KEY','ELEVENLABS_API_KEY','ELEVENLABS_VOICE_ID'):
    os.environ[key]=''

import pytest

@pytest.fixture(autouse=True)
def isolate_voice_mode(monkeypatch):
    from ilma_api import settings
    monkeypatch.setattr(settings,'HUMAN_VOICE_ENABLED',False)
