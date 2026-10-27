# ILMA · ইলমা

ILMA is a Bangla and English banking information app designed for blind and
low-vision users. Speak a bank name or ask a question to find bank reports,
services and sourced answers. The interface uses a teal and gold theme, a living
waveform and four tabs: Home, Bank Services, Bank Details and News.

## Features

- Voice input with Meta Muse transcription and Spark intent classification.
- Bilingual bank-name matching with confirmation for ambiguous names; unmatched
  input never defaults to a bank.
- Bank reports, available deposit rates, insurance information and financial
  terminology backed by database records.
- ElevenLabs spoken answers, playback controls and slower playback settings.
- EN/BN language selection, optional left-swipe language switching and settings.
- Single tap on Home to record; while recording, double-tap to stop and search.
  An explicit **Stop and search** button and typing fallback are also available.
- Offline caching of previously viewed public reports. Offline voice prompts
  require a generated and reviewed audio bundle.

## Stack

The frontend uses HTML, CSS and JavaScript with a service worker. FastAPI serves
the app and API; SQLAlchemy and PyMySQL provide MySQL persistence. RapidFuzz
matches bank aliases, and ffmpeg converts audio in memory. No Node build step is
required; Node.js is used for frontend regression tests.

## Getting started

Requirements: Python 3.10+, a reachable MySQL database, provider credentials and
an existing Python virtual environment. Node.js 20+ is needed to run frontend
tests. Use system ffmpeg or the binary supplied by `imageio-ffmpeg`.

```sh
git clone https://github.com/sjasumon/ilma.git
cd ilma
export ILMA_VENV_PATH=/path/to/your/existing/venv
"$ILMA_VENV_PATH/bin/python" -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Edit `.env` with your own values:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=your_database
DB_USERNAME=your_database_user
DB_PASSWORD='your_database_password'
META_MODEL_API_KEY=your_meta_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
VOICE_LOG_SALT=your_random_private_salt
```

Keep the provider URLs and model settings from `.env.example`, adjusting them
to your provider access if needed. `MUSE_VOICE_API_KEY` is also accepted for Meta
authentication. Separate database name/user fields take precedence over
`DATABASE_URL`; passwords do not need URL encoding.

### Database setup

Provision the verified institution schema and bank data using
[the database specification](docs/APP_SPEC_01_database_and_status.md). A fresh
clone does not include a production database dump. The voice migration requires
the existing `institution` and `institution_alias` tables; it adds voice tables,
aliases and authored glossary entries without inserting bank financial facts.
Do not run the legacy sample seed loader against production.

```sh
export PYTHONPATH="$PWD/api"
"$ILMA_VENV_PATH/bin/python" -m ilma_api.migrate_voice
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_doctor --live
"$ILMA_VENV_PATH/bin/uvicorn" ilma_api.main:app --host 0.0.0.0 --port 8001
```

Open `http://localhost:8001`; API documentation is at `/docs`. Phone microphone
access requires HTTPS. The live doctor contacts configured providers and exits
nonzero when any readiness gate is incomplete, even if connectivity succeeds.

`bash ops/bootstrap_voice.sh` can install dependencies and run the migration
using `ILMA_VENV_PATH` or the activated environment. It reuses an existing venv.

### Current server service

The current host runs `ilma-app.service` as `ubuntu`, using
`/home/ubuntu/venv/bin/python3 -m uvicorn ilma_api.main:app` from this project's
directory. It listens on `127.0.0.1:8001` behind the public HTTPS endpoint. The
service is enabled at boot and uses `Restart=always` for process recovery.
The service uses the `ilma` database. Its bank dataset still needs loading;
records from unrelated databases must not be used. The database override is documented in
[the voice pipeline audit](docs/VOICE_PIPELINE_AUDIT.md).
Restart it after deploying Python changes; updating static files does not reload
the running backend:

```sh
sudo systemctl restart ilma-app.service
systemctl status ilma-app.service --no-pager
journalctl -u ilma-app.service -n 50 --no-pager
curl --fail https://app.sumon.me/v1/voice/config
```

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /v1/health` | Database/release health |
| `GET /v1/institutions?q=...` | Search institutions |
| `GET /v1/institutions/index` | Institution names and aliases |
| `GET /v1/institutions/{id_or_slug}/report-card` | Bank report |
| `GET /v1/news` | Banking events/news |
| `POST /v1/voice` | Multipart audio and context; streaming response |
| `POST /v1/ask` | Multipart text and context; streaming response |
| `POST /v1/speech` | Spoken readout of database-backed content |

Voice/text responses use server-sent events for transcript, matching, results and
speech. See [voice setup and contract](docs/MUSE_VOICE_API.md) for details.

## Tests

From the project root:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m unittest discover -s tests -q
node tests/test_frontend.cjs
node tests/test_greeting_cycle.cjs
node tests/test_voice_search.cjs
node tests/test_audio_recorder.cjs
node tests/test_offline.cjs
```

SQLite is used only for isolated test fixtures; runtime persistence uses MySQL.
Provider mocks do not establish real speech accuracy or pronunciation quality.

## Privacy and deployment

Credentials stay server-side in the ignored `.env`. Runtime audio is processed
in memory and sent through the backend to the transcription provider; it is not
saved to local disk. Users should avoid speaking PINs or account numbers. MySQL
voice logs omit input text and audio, retaining operational metadata and a salted
anonymous identifier. Recent conversation context is held client-side.

Private recordings, database dumps, audio drafts and evaluation reports are
excluded from Git. Schedule daily retention cleanup using the templates in
`ops/`, after adjusting their installation path and service account.

For development tests only, [audio diagnostics](docs/VOICE_DIAGNOSTICS.md) can
pair original recordings and raw Meta transcripts in a separate MySQL table.
This requires two explicit development switches and remains disabled on the
live service. No diagnostic recordings or transcripts are pushed to GitHub.

## Acceptance status

The latest recorded checks include 50 passing Python tests, five passing
frontend suites, successful MySQL voice migration, Meta authentication and
ElevenLabs configured-voice access. Full acceptance is still pending:

- Load the verified bank dataset into `ilma`; it currently has no institution records.
- Fixed offline audio generation, native-speaker review and publication.
- Synthetic and real-person speech accuracy/latency measurements.
- Physical phone, TalkBack, 200% text and offline validation.
- Final HTTPS deployment and retention timer verification.

Track current evidence and procedures in
[VOICE_ACCEPTANCE.md](docs/VOICE_ACCEPTANCE.md).

## Project documents

- [Functional requirements](docs/FRD%20ILma.md)
- [Build plan](docs/BUILD_PLAN.md)
- [Accessible design checklist](docs/ILMA_design_build_checklist.md)
- [Database and status specification](docs/APP_SPEC_01_database_and_status.md)
- [Voice engine specification](APP_SPEC_02_voice.md)
- [Design tokens](docs/tokens.css) and [Home design reference](design/S01-Home.html)

Source code is provided without a declared project license at this time.
