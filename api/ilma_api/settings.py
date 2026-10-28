import logging
import os
import secrets
from ilma_api.database_config import build_database_url
from pathlib import Path
from dotenv import load_dotenv

# Local development secrets; deployed environment variables take precedence.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

# Supply production credentials through the environment, never source control.
DATABASE_URL = build_database_url(os.environ)
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8001"))

META_MODEL_API_KEY = os.getenv("META_MODEL_API_KEY") or os.getenv("MUSE_VOICE_API_KEY", "")
MUSE_VOICE_API_KEY = META_MODEL_API_KEY
MUSE_VOICE_API_URL = os.getenv("MUSE_VOICE_API_URL", "")
MUSE_VOICE_MODEL = os.getenv("MUSE_VOICE_MODEL", "")

MUSE_SPARK_API_URL = os.getenv("MUSE_SPARK_API_URL", "https://api.meta.ai/v1/chat/completions")
MUSE_SPARK_MODEL = os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3")
MUSE_CHECK_MODEL = os.getenv("MUSE_CHECK_MODEL") or MUSE_SPARK_MODEL
VOICE_SILENCE_MS = max(1500, min(4000, int(os.getenv("VOICE_SILENCE_MS", "1500"))))
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_v3")
SPEECH_TIMEOUT_SECONDS = max(5, min(25, int(os.getenv("SPEECH_TIMEOUT_SECONDS", "25"))))

VOICE_LOG_SALT = os.getenv("VOICE_LOG_SALT", "")
VOICE_LOG_SALT_CONFIGURED = bool(VOICE_LOG_SALT)
if not VOICE_LOG_SALT:
    # Watch-list identities and voice rate buckets are HMACs under this salt.
    # A fallback keeps CI/test runs working, but production must pin a stable
    # value in the private .env or every restart wipes users' watch lists.
    VOICE_LOG_SALT = secrets.token_hex(32)
    if os.getenv("ILMA_ENV", "production") == "production":
        logging.getLogger(__name__).warning(
            "VOICE_LOG_SALT is not set; generated an ephemeral salt — "
            "watch lists and rate buckets will reset on restart.")

# Diagnostic recordings require BOTH switches; never enable in production.
ILMA_ENV = os.getenv("ILMA_ENV", "production")
VOICE_DIAGNOSTICS_ENABLED = os.getenv("VOICE_DIAGNOSTICS_ENABLED", "false").lower() == "true"
# The /voice-test acceptance page is only served when explicitly enabled.
VOICE_TEST_PAGE_ENABLED = os.getenv("VOICE_TEST_PAGE_ENABLED", "false").lower() == "true"

# Provider admission budgets (shared MySQL backend in production). Restrict origins even during diagnostics.
CORS_ORIGINS = [value.strip().rstrip('/') for value in os.getenv(
    'CORS_ORIGINS', 'https://app.sumon.me,http://localhost:8001,http://127.0.0.1:8001').split(',') if value.strip()]
API_CLIENT_PER_MINUTE = max(1, int(os.getenv('API_CLIENT_PER_MINUTE', '12')))
API_GLOBAL_PER_MINUTE = max(1, int(os.getenv('API_GLOBAL_PER_MINUTE', '60')))
API_GLOBAL_PER_DAY = max(1, int(os.getenv('API_GLOBAL_PER_DAY', '1000')))
API_CLIENT_CONCURRENCY = max(1, int(os.getenv('API_CLIENT_CONCURRENCY', '2')))
API_GLOBAL_CONCURRENCY = max(1, int(os.getenv('API_GLOBAL_CONCURRENCY', '4')))
API_UPLOAD_TIMEOUT_SECONDS = max(1, min(60, int(os.getenv('API_UPLOAD_TIMEOUT_SECONDS', '20'))))

TTS_CACHE_DIR = os.getenv('TTS_CACHE_DIR', '/var/cache/ilma/tts')
TTS_PREWARM = os.getenv('TTS_PREWARM','false').lower() == 'true'

TTS_SPEED = max(.7,min(1.2,float(os.getenv('TTS_SPEED','1.1'))))

API_ADMISSION_BACKEND = os.getenv('API_ADMISSION_BACKEND','process')
