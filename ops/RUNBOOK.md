# ILMA operations

Runtime database is **ilma**. Never use another project's database. Current host:
`/home/ubuntu/shared/all_projects/ilma`, venv `/home/ubuntu/venv`, app port 8001 on
loopback, public HTTPS through `cloudflared-app.service`. Use the versioned speed drop-in for two workers with shared MySQL admission;
process-local admission is restricted to a single development worker.

## Check and recover

```sh
systemctl status ilma-app.service
systemctl list-timers 'ilma-*'
journalctl -u ilma-app.service --since '15 minutes ago'
journalctl -t ilma-ops --since today
curl --fail http://127.0.0.1:8001/v1/health
curl --fail https://app.sumon.me/v1/health
```

Check the JSON `ok` field as well as HTTP status. The local monitor does both.
If local health succeeds but public health fails, inspect the Cloudflare tunnel.
If DB is unavailable, restore connection/access to **ilma**, not another database.
Do not paste `.env`, connection strings, provider bodies or recordings into logs.

After a tested code update: `sudo systemctl restart ilma-app.service`, check local
and public health, then test one typed request and one consented voice request.
Browser assets require a new index/service-worker version when changed.

## Backups and isolated restore

```sh
sudo systemctl start ilma-backup.service
sudo journalctl -u ilma-backup.service -n 10
```

Backups live outside the web root at `/var/lib/ilma-backups` (0700/0600). Seven
snapshots are kept. The dump selects only `ilma` and ignores unrelated MySQL
defaults. Retained diagnostic data is included while diagnostic capture is active.
These are local, unencrypted backups: configure an encrypted off-host destination
before claiming disaster recovery. Do not upload them to GitHub.

For an isolated drill, run the module with `PYTHONPATH` set to this project's api
and `DB_NAME=ilma`; supply `restore-check --file <private snapshot>`. It requires
permission to create/drop its newly generated `ilma_restore_check_<uuid>` database.
Keep those privileges out of the app account. On this host, the explicit
`--admin-socket /var/run/mysqld/mysqld.sock` option may be run as local root for the
drill. It never accepts the live database as a restore target and never drops a
pre-existing target. A drill is not authorization to restore over live data.

## Retention and failure signals

`ilma-voice-cleanup.timer` expires ordinary logs after 30 days and diagnostics
after seven days, including when capture is disabled or no requests arrive. A
200-sample diagnostic maximum also applies. Check its unit Result and journal.
Exported files and historical backups require separate deletion decisions.

`ilma-monitor.timer` runs every two minutes; failing jobs emit a local journal
error via `ilma-ops-alert@.service`. Configure an explicitly authorized external
alert destination before relying on unattended production response.

## Rollback and release gates

Record the deployed commit, retain a clean previous checkout and verify it on a
separate loopback port against the current schema before changing public traffic.
Keep secrets outside release archives. Do not use destructive Git resets or
directory synchronization that can delete `.env`. Do not roll back schema/data
blindly: imports and private diagnostic writes are not code changes.

The 27 October canary validated `26f729e` against the current schema. Public
traffic switching and off-host restore remain to rehearse. Production switch and
outstanding acceptance are tracked in `docs/RELEASE_HARDENING.md`.

## Guided voice-agent audit schema

Before serving the voice-agent backend, run the additive migration with the
existing private environment and project virtualenv:

```sh
PYTHONPATH=api python -m ilma_api.migrate_agent
```

It creates only `app_model_call`, checks that MySQL database name is `ilma`,
and leaves financial, incident, service and watch records unchanged. Restart
the existing application system service after backend updates. Keep `.env`
ignored and mode 0600. The current agent uses one PLAN call at most and local template validation;
`MUSE_CHECK_MODEL` is reserved legacy configuration. Never print provider keys or database credentials.

For a model-off acceptance run, use an isolated preview with
`META_MODEL_API_KEY=` and `MUSE_VOICE_API_KEY=`; tap choices must traverse the
script with templates and no Muse model calls. TTS, if configured, remains a
separate paid provider call. Never disable model credentials on the shared
live service just to test this path.


## Voice latency service configuration

Install the versioned `ops/ilma-speed.conf` as a systemd drop-in for the existing
application service, then daemon-reload and restart. It runs two uvicorn workers,
enables background public speech warmup and selects shared MySQL admission.
Keep the existing private environment and restrict the database to `ilma`.
A stable private VOICE_LOG_SALT is mandatory for shared admission. Verify a
second limiter instance rejects a simultaneous client lease before enabling
multiple workers. Never run multiple production workers with process admission.

CacheDirectory creates private `/var/cache/ilma`; speech is under `tts/`, separate
from the repository, diagnostic recordings and static assets. Opaque tickets
expire after ten minutes. Maintenance bounds reusable public speech to thirty
days / 128 MiB. Cache identity includes voice/model/speed/text/language, so
updated facts produce new speech. Warmup acquires one cross-worker lock, runs in
the background, and skips existing clips. Set TTS_PREWARM=false to suppress new
warmup provider calls; normal speech still works. Keep ownership/modes private.
Never copy this cache or the private environment into Git.

Inspect metadata-only `voice_timings` service log entries by request ID. Each
contains stage duration/elapsed values and skipped stages; no transcript or raw
provider body is logged. `sent` records answer text delivery. tts_done records
server cache/generation completion, not device playback. Cache hits are visible
in X-ILMA-Cache on the private no-store audio response. Do not gzip or buffer
`/v1/audio/` or SSE at the reverse proxy. Audio tickets are intentionally omitted
from API docs and must not be cached by the service worker or Cloudflare.

After restart, verify two worker processes, page/API docs headers on the live
Cloudflare host, a streaming audio response and a simultaneous page GET. Follow
[VOICE_SPEED.md](../docs/VOICE_SPEED.md) for measurement definitions and remaining
phone/ASR acceptance. Run the documented full Python/frontend suites, policy and
full-history redacted secrets checks before every fast-forward push.

Spark PLAN uses minimal reasoning and a 1,000-total-token cap because internal
reasoning shares that budget with the visible plan; the initial 300-token cap
returned no JSON. The strict 4.5-second overall deadline remains authoritative.


## Local conversation browser preview

For `tests/check_conversation_browser.py`, use a temporary loopback preview with
DB_NAME=ilma, META_MODEL_API_KEY=, MUSE_VOICE_API_KEY=, ELEVENLABS_API_KEY=,
TTS_PREWARM=false and API_ADMISSION_BACKEND=process. Set CORS_ORIGINS to that
preview's exact loopback origin (for example http://127.0.0.1:8018). These
provider-disabled overrides belong only to the preview; never clear credentials
or weaken origins on the live service. Stop the temporary preview after checks.
The script performs read-only public bank queries and no microphone capture.


## BRAC ASR alias update

With the existing private environment, DB_NAME=ilma and the project virtualenv,
run `PYTHONPATH=api python -m ilma_api.migrate_brac_aliases`. This idempotent
migration adds only the three user-approved spellings to the existing bracbank
institution. It does not create banks or change facts/source names. The standard
voice migration also applies them, so they can be restored after a seed reload.
Only the ilma MySQL database is permitted. Restart the application after backend
updates; verify both spellings route to BRAC and scripted replies retain language.


## Connected speech cache and review

The current warmup builds whole first-answer paragraphs for eleven covered banks
in both languages, plus full questions and guided prompts. It runs in the
background and skips existing text/voice/model/speed cache entries. It can take
several minutes after a wording/data change; service readiness does not imply
warmup completion. The same private cache limits and shared generation locks
apply. Do not publish audio files or raw review artifacts.

For full read-only source checks, run `tests/check_answer_wording.py` against a
loopback preview with Meta/ASR/TTS disabled and its exact origin allowed. It writes
review paragraphs under /tmp, outside the published tree. For actual one-clip
playback, enable TTS only on that preview and run
`tests/check_answer_playback_browser.py`; it uses a synthetic recorder, can incur
TTS on a cache miss, and must not be described as real microphone acceptance.
Stop the temporary preview after verification. Never change live credentials
just to run these checks.

For generated-input full voice checks, `tests/check_voice_roundtrip_browser.py`
requires a private WAV, bank slug, language and provider-enabled target. It uses
Chromium's fake microphone with real MediaRecorder/upload/Meta/TTS. No transcript
or audio is printed or committed; normal target diagnostic settings still apply.
Run other browser/matrix checks sequentially to avoid competing admission leases.
`docs/VOICE_PIPELINE_CHECKS.md` records scope and outstanding native/human gates.

## Short speech acceptance

`tests/check_answer_wording.py` writes a private source-backed review artifact.
With the existing private environment, run
`PYTHONPATH=api python tests/check_short_answer_audio.py` to synthesize/reuse those
public paragraphs and fail any clip over 10,000 ms or over the word budget.
The tool can incur TTS calls; generated audio and its metadata remain private.
Short-answer cache identity now has a processing-policy version. Its normalizer
streams through ffmpeg, retains quiet voiced content, and terminates the child
process on cancellation. Ordinary short answers and explicit full-report
readouts use different policies. Do not publish the cache or review artifact.

Keep the deployed source tree stable during review. Prefer a preview checkout
with its private configuration loaded outside the published tree, then copy the
tested release and restart the service together. Poll health before browser
checks; systemctl returning does not establish that the HTTP listener is ready.


### Natural-speech release checks

Use `check_answer_wording.py` to create a private source-backed review artifact,
then `check_short_answer_audio.py --review /tmp/<review>.json --output /tmp/<metrics>.json`
with the deployment configuration loaded privately. Names remain historical;
the current ordinary-answer gate is 30 seconds, with a 45-word introduction
budget. Record introduction target misses honestly. Use
`check_speech_interrupt_browser.py` for real playback stop timing with synthetic
microphone handoff. Native listening and physical echo rejection are separate.
The natural-speech cache policy regenerates changed pronunciation without
removing private historical cache data or altering published history.
