"""Failure boundaries around the contextual voice pipeline."""
import asyncio
from unittest.mock import AsyncMock,patch,MagicMock
import pytest
from fastapi import Response,HTTPException
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from test_voice_agent import db,BANKS
from ilma_api import settings
from ilma_api.voice import convert_audio,VoiceError
from ilma_api.voice_agent import Conversation
from ilma_api.voice_text import VoiceContext
from ilma_api.human_agent import run
from ilma_api.voice_pipeline import run_pipeline
from ilma_api.audio_cache import AudioStore

def test_production_requires_stable_salt_and_ilma_database():
    with patch.multiple(settings,ILMA_ENV='production',VOICE_LOG_SALT_CONFIGURED=False):
        with pytest.raises(RuntimeError,match='stable VOICE_LOG_SALT'):settings.validate_environment()
    with patch.multiple(settings,ILMA_ENV='production',VOICE_LOG_SALT_CONFIGURED=True,VOICE_LOG_SALT='x'*32,VOICE_DIAGNOSTICS_ENABLED=False,DATABASE_URL=make_url('mysql+pymysql://localhost/ilma')):
        settings.validate_environment()
        with patch.object(settings,'DATABASE_URL',make_url('mysql+pymysql://localhost/project_db')):
            with pytest.raises(RuntimeError,match='only the ilma'):settings.validate_environment()

def test_database_down_health_sets_503():
    from ilma_api.main import health_check
    database=MagicMock();database.query.side_effect=SQLAlchemyError('synthetic')
    response=Response()
    body=health_check(database,response)
    assert response.status_code==503 and body['ok'] is False

def test_empty_audio_is_no_speech():
    with pytest.raises(VoiceError) as caught:asyncio.run(convert_audio(b'','audio/webm'))
    assert caught.value.code=='no_speech'

def test_truncated_capture_asks_again_without_a_model_or_user_miss(db):
    async def scenario():
        with patch('ilma_api.human_turn.generate',AsyncMock()) as model:
            result=await run('Partial question',VoiceContext(agent=True,speak=False,ui_lang='en',audio_truncated=True,conversation=Conversation(institution_id=1,language='en')),BANKS,db)
        model.assert_not_awaited()
        assert result['audio_truncated'] and result['conversation']['misses']==0
        assert 'shorter question' in result['text']
    asyncio.run(scenario())

def test_post_result_speech_error_does_not_replace_the_answer(db):
    # Use the actual context rather than a simulated result, so all result fields
    # used by the streaming path are exercised.
    async def check_frames():
        with patch.object(settings,'META_MODEL_API_KEY',''),patch('ilma_api.audio_cache.register_speech',AsyncMock(side_effect=VoiceError('speech_unavailable',503,'',''))):
            return [f async for f in run_pipeline(None,'BRAC Bank','',VoiceContext(agent=True,speak=True,ui_lang='en'),BANKS,db,mode='text')]
    frames=asyncio.run(check_frames())
    assert any(f.startswith('event: result') for f in frames)
    assert any(f.startswith('event: speech_unavailable') for f in frames)
    assert not any(f.startswith('event: error') for f in frames)

def test_busy_speech_retains_a_retryable_ticket(tmp_path):
    async def scenario():
        store=AudioStore(tmp_path)
        busy=HTTPException(503,{'code':'speech_busy','retry_after':1},headers={'Retry-After':'1'})
        with patch.multiple(settings,ELEVENLABS_API_KEY='synthetic',ELEVENLABS_VOICE_ID='synthetic-voice'),patch.object(store,'job',AsyncMock(side_effect=busy)):
            ticket=await store.register(['A synthetic public fact.'],'en')
            assert ticket and ticket['audio_url']
            token=ticket['audio_url'].rsplit('/',1)[1][:-4]
            assert store.ticket(token)
            with pytest.raises(HTTPException) as caught:await store.response(token)
            assert caught.value.detail['code']=='speech_busy' and caught.value.headers['Retry-After']=='1'
    asyncio.run(scenario())
