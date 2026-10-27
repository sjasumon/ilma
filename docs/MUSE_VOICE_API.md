# Voice setup — APP_SPEC_02

Authoritative behavior: [APP_SPEC_02_voice.md](../APP_SPEC_02_voice.md).

## Private configuration

Keep all credentials in the ignored `.env` (permissions 600). No credentials are
sent to the frontend. Required:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=
DB_USERNAME=
DB_PASSWORD=''
META_MODEL_API_KEY=
MUSE_VOICE_API_URL=https://api.meta.ai/v1/asr/transcribe
MUSE_VOICE_MODEL=muse-voice-transcribe-1.0
MUSE_SPARK_API_URL=https://api.meta.ai/v1/chat/completions
MUSE_SPARK_MODEL=muse-spark-1.3
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL=eleven_v3
VOICE_SILENCE_MS=1500
FFMPEG_BINARY=ffmpeg
```

Enter the database password directly; no URL encoding is needed. Separate
DB_NAME/DB_USERNAME fields take precedence over DATABASE_URL. DB_USER/DB_PASS
and mixed-case names such as DB_username/db_pass are also accepted.

The existing MUSE_VOICE_API_KEY is accepted as an alias for META_MODEL_API_KEY.
Contributor models are rejected for user input. All runtime persistence is MySQL;
SQLite engines are used only by isolated tests. Client language preferences and
last-three-exchange context remain device-side as APP_SPEC_02 specifies.

## Install and migrate

```sh
export ILMA_VENV_PATH=/home/ubuntu/venv  # use your existing venv path
"$ILMA_VENV_PATH/bin/python" -m pip install -r requirements.txt
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.migrate_voice
PYTHONPATH=api "$ILMA_VENV_PATH/bin/uvicorn" ilma_api.main:app --host 0.0.0.0 --port 8001
```

Install system ffmpeg or use the binary supplied by imageio-ffmpeg. RapidFuzz is
required for fuzzy scoring. The migration adds the alias provenance column, voice
log/counter tables and specified mishearing aliases for existing banks only. It
never creates invented bank facts or loads demonstration values into MySQL.

## Contract

- `GET /v1/voice/config`: silence/no-speech/max-duration recording settings.
- `POST /v1/voice`: multipart `audio` (WebM/Opus or MP4) and `context` JSON.
- `POST /v1/ask`: multipart `text` and the same `context` JSON.
- `POST /v1/speech`: JSON `kind` (report_card, insurance, news), optional
  institution_id, language. Reads bank data from MySQL before calling ElevenLabs.

Context: tab (home/bank/services), optional bank_id, ui_lang (bn/en), last three
history exchanges, speak flag. Voice/text responses use SSE events: transcript,
match, result, speech. Errors use an error event or the shared JSON error envelope
if detected before streaming starts. Audio conversion uses ffmpeg pipes in memory;
no recording is written to disk. Meta receives mono 24kHz signed 16-bit PCM WAV,
PUSH_TO_TALK, Bengali bias in BN and Bengali+English in EN, and no keywords.
429/500 retry twice (2s/4s); ASR calls have an eight-second deadline.

Transcript cleanup, bilingual alias scoring and the 70% Latin language rule run
server-side. Strong matches route to that actual bank; uncertain short names and
close matches ask for confirmation. Missing matches never default to EBL and are
not falsely labelled unlicensed merely because ASR could not match them.

Spark classifies intent only; IDs must come from matched/contextual banks. Bank
names alone skip Spark. Sourced templates read report cards, rates and insurance
from MySQL. Missing products/data return the no-data answer. Amounts are used
transiently for calculator prefills and never stored. Voice logs omit the user's
text/history entirely; only intent, fact/source IDs, outcome, latency and a monthly
salted anonymous hash are retained. Old log rows are deleted during request
logging. Production should also schedule a daily retention cleanup.

## Verification limits

Automated tests use SQLite fixtures and mocked providers/processes, not production
MySQL. The real RapidFuzz test skips if its dependency cannot be installed. Actual
ffmpeg conversion, MySQL migration and provider calls must also pass on the host.
The supplied H:\Projects\ilma-test recordings are not present here, so the replay
accuracy/latency targets and 20 real-person phone recordings remain unverified.
Fixed offline audio clips still need generating and native-speaker review.


Full requirement matrix, replay commands, native audio review and host acceptance:
[VOICE_ACCEPTANCE.md](VOICE_ACCEPTANCE.md). The asset version is
voice-complete-20261027-20.
