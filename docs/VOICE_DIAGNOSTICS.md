# Development-only audio diagnostics

This optional mode pairs original browser audio with the raw Meta transcript
(before cleanup), selected language, match/result events and error codes in
MySQL's `voice_diagnostic` table. It has no public playback/download endpoint.
It is disabled by default. At the user's explicit request, the current
`app.sumon.me` instance was temporarily switched to development diagnostics on
2026-10-27, its diagnostic table created, and `ilma-app.service` restarted.
New voice requests on that instance are now retained for this diagnostic test.
Verified capture through the public `/v1/voice` endpoint using synthetic silence;
the host-side diagnostic list confirmed a saved `no_speech` sample. No human
recording was used for that activation check. Setup/listing must run against the
same MySQL instance as the service; the managed agent's initial setup was not
visible to the host service, so host-context setup was used.
Disable capture when testing finishes; do not carry these switches into the
production configuration.
Normal production requests continue to discard audio and omit transcripts from
operational logs.

Use a separate local development process and preferably a separate MySQL
database. Configure its private `.env`, then in that development terminal only:

```sh
export ILMA_ENV=development
export VOICE_DIAGNOSTICS_ENABLED=true
export PYTHONPATH="$PWD/api"
export ILMA_VENV_PATH=/home/ubuntu/venv
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_diagnostics setup
"$ILMA_VENV_PATH/bin/uvicorn" ilma_api.main:app --host 127.0.0.1 --port 8002
```

Keep these enabled values out of the eventual production service configuration.
Both the development environment and explicit switch are required. No table is
created automatically by a normal voice request. Failed capture writes produce
a fixed warning and do not break the normal answer flow.

Open the development app on localhost, record test questions, then inspect the
paired samples from the same configured terminal:

```sh
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_diagnostics list
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_diagnostics label --id SAMPLE_ID --expected 'ইস্টার্ন ব্যাংক কেমন আছে?'
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_diagnostics export --id SAMPLE_ID --directory voice-diagnostics
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_diagnostics prune
```

Exports contain the original WebM/MP4/WAV plus matching JSON. Compare the audio,
intended question, raw ASR transcript and final match/error to locate capture,
recognition and routing problems. Exported files are private and Git-ignored;
do not serve them from a web directory. The CLI rejects this project's `static/`.

Capture and CLI operations prune samples older than seven days and retain at
most 200 samples. For an idle development instance, schedule the `prune` command
daily or run it manually; no background expiration job is installed by this
feature. Exported files require separate manual deletion. Avoid real customer
secrets in diagnostic questions. Turn the switch off and restart the development
process when finished.

To end the current diagnostic session, set `VOICE_DIAGNOSTICS_ENABLED=false` and
`ILMA_ENV=production` in the private `.env`, then restart `ilma-app.service`.
Disabling capture does not delete existing samples; prune/delete them separately.
