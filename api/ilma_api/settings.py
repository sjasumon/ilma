import os
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
VOICE_SILENCE_MS = max(1500, min(4000, int(os.getenv("VOICE_SILENCE_MS", "1500"))))
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_v3")
SPEECH_TIMEOUT_SECONDS = max(5, min(25, int(os.getenv("SPEECH_TIMEOUT_SECONDS", "25"))))

VOICE_LOG_SALT = os.getenv("VOICE_LOG_SALT") or __import__("secrets").token_hex(32)

# Diagnostic recordings require BOTH switches; never enable on the live service.
ILMA_ENV = os.getenv("ILMA_ENV", "production")
VOICE_DIAGNOSTICS_ENABLED = os.getenv("VOICE_DIAGNOSTICS_ENABLED", "false").lower() == "true"

# Single-worker provider admission budgets. Restrict origins even during diagnostics.
CORS_ORIGINS = [value.strip().rstrip('/') for value in os.getenv(
    'CORS_ORIGINS', 'https://app.sumon.me,http://localhost:8001,http://127.0.0.1:8001').split(',') if value.strip()]
API_CLIENT_PER_MINUTE = max(1, int(os.getenv('API_CLIENT_PER_MINUTE', '12')))
API_GLOBAL_PER_MINUTE = max(1, int(os.getenv('API_GLOBAL_PER_MINUTE', '60')))
API_GLOBAL_PER_DAY = max(1, int(os.getenv('API_GLOBAL_PER_DAY', '1000')))
API_CLIENT_CONCURRENCY = max(1, int(os.getenv('API_CLIENT_CONCURRENCY', '2')))
API_GLOBAL_CONCURRENCY = max(1, int(os.getenv('API_GLOBAL_CONCURRENCY', '4')))
API_UPLOAD_TIMEOUT_SECONDS = max(1, min(60, int(os.getenv('API_UPLOAD_TIMEOUT_SECONDS', '20'))))
