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


### Audio cache recovery and real-input smoke check

MP3 publication requires successful decoding and positive duration metadata.
Ordinary speech over 30 seconds is rejected rather than cached; full-report
readouts retain their separate contract. Existing invalid cache entries are
regenerated on the next request. Shared workers ignore partial/error files older
than the current lock, preserving first-byte streaming without inheriting an
earlier failed attempt. Do not manually delete cache data to bypass a test.

`check_voice_roundtrip_browser.py` uses a private generated WAV for the initial
native browser capture and quiet input for subsequent openings. This tests
normal completion separately from `check_speech_interrupt_browser.py`. A fake
input that continually replays its phrase simulates a person continually
interrupting; it cannot establish normal completion or physical echo rejection.
Always poll `/v1/health` after starting a preview or restarting the service before
browser checks. No recording or diagnostic export belongs in the published tree.
# Contextual voice preview

The 29 October deployment was explicitly authorized with
`HUMAN_VOICE_ENABLED=true` and `HUMAN_MODEL_TIMEOUT_SECONDS=8`, despite remaining
acceptance gates in `docs/specs/HUMAN_VOICE.md`. This deployment does not establish
that those gates passed. The implementation includes a source-safe
fallback; a fallback success does not validate Muse Spark wording.

Before enabling an isolated preview, run these against the private deployment
environment, with `DB_NAME=ilma` explicitly set:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.migrate_human_voice
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.profile_loader seed/bank_profile.csv
```

The migration is additive and derives term metadata without changing source
financial values. Profile imports preserve individual source quotations. Set
`HUMAN_VOICE_ENABLED=true` only for the preview while completing live acceptance.
An HTTP 402 from Spark requires resolving provider account/model access; changing
templates does not resolve that provider response. Do not paste credentials into
logs, issue descriptions or chat.

Provider access was restored during the 29 October validation. Keep activation
disabled until the complete evaluation meets its target; successful fallback
speech does not count as generated-answer acceptance. The model timeout defaults
to 4.5 seconds and can explicitly be set with `HUMAN_MODEL_TIMEOUT_SECONDS`
(2–8 seconds). Evaluate both response latency and fallback frequency before
changing this deployment setting.

Production startup rejects a missing/short stable `VOICE_LOG_SALT`, enabled audio
diagnostics or a database name other than `ilma`. Conversation tokens use the
stable salt, so changing it invalidates existing conversation tokens.

## Token-protocol preview checkpoint

The newer token engine remains a preview; do not copy this checkpoint into the
production working tree. The release instructions require Phase 2 acceptance
on two consecutive nights before proceeding with production hardening/release.
No two-night acceptance, physical-device acceptance or source sign-off is claimed.

Before starting a preview of this checkpoint, run the additive migration:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.migrate_human_voice
```

Offline introduction composition is explicit and paid (Spark only, no TTS).
Start with a specific bank and inspect its validated coverage before composing
all banks. Invalid or duplicate variants are not saved, and the command exits
nonzero if any requested variant was not completed:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" ops/compose_voice_variants.py --live --bank-id 19
```

Regenerate after approved fact changes. Cached variants are not a completed,
native-reviewed or prewarmed audio bundle. Keep `TTS_PREWARM=false` and omit TTS
credentials on automated evaluation previews. Never run paid TTS in automated
tests. The synthetic browser playback test uses generated tone audio:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" tests/check_voice_tokens_browser.py --base-url http://127.0.0.1:8018
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" ops/evaluate_human_voice.py --live --workers 2 --output /tmp/ilma-voice-evaluation.json
```

The complete corpus is 404 authored cases. Evaluation output stays private;
only measured aggregates belong in the public acceptance record. First streamed
text and complete-response timing are now separate; older reports measured only
completion. No nightly timer has been installed while the Phase 2 implementation
and audio/variety measurements are incomplete. External alerts also need a
private destination/configuration; they are not currently operational.

## Dedicated preview deployment

`preview.sumon.me` has a separate named Cloudflare tunnel and application checkout
at `/home/ubuntu/shared/all_projects/preview.sumon.me`. The production checkout,
port and services are not changed by preview deployment. Install the versioned
`ops/ilma-preview.service` and `ops/cloudflared-preview.service`, then enable them
so the preview resumes after a host restart. The app binds only to loopback port
8018; the tunnel provides public HTTPS.

The private tunnel directory is
`/home/ubuntu/.cloudflared/preview.sumon.me/`: `credentials.json` is the secret
Cloudflare credential, `config.yml` is the actual tunnel configuration, and
`deployment.json` / `deployment.xml` record nonsecret deployment metadata. Keep
this directory mode 0700 and its files mode 0600, outside the Git checkout.
Cloudflare consumes YAML, not XML; XML is a deployment manifest only.

The preview's ignored `.env` is mode 0600. Initially its Meta and ElevenLabs
credentials, endpoints, voice, model, speech speed and model deadline match the
production configuration. TTS is enabled, including normal operational prewarming;
automated tests still use synthetic audio/provider fixtures. To separate ElevenLabs
usage later, replace only the preview's `ELEVENLABS_API_KEY`, then restart
`ilma-preview.service`. Never print the environment or credentials into logs.

Both installations use only MySQL `ilma`. No seed reload or source-data replacement
is part of preview deployment. The preview uses its own signing salt, cache
`/var/cache/ilma-preview/tts`, and `API_ADMISSION_NAMESPACE=preview`. An empty
namespace preserves production's existing MySQL counter and lock names. The
namespace isolates preview budgets while retaining the same budget values and
two-worker configuration; it does not isolate physical server/provider resources.

Verify localhost health before routing the new hostname. Verify the public shell,
health, streaming responses and security headers through Cloudflare. Compare the
private environment's provider settings without printing their values. Keep a
commit-stamped deployment manifest and update it after each preview release.
A preview deployment does not constitute production acceptance or a completed
Phase 1 evaluation.

## Complete Phase 1 evaluation

Use a separate local service (for example port 8019), with the exact frozen
preview checkout, the same Meta model and 8-second deadline, TTS/prewarming off,
and its own admission namespace/signing salt. Raise only this test service's
admission/question quotas for the authored corpus; do not change public preview
limits or interfere with manual testing. The runner uses the preview's private
environment to read only `ilma` for response audits. It clears inherited database
variables before loading that file so another workspace's defaults cannot win.

```sh
"$ILMA_VENV_PATH/bin/python" ops/evaluate_phase1.py --live \
  --app-dir /home/ubuntu/shared/all_projects/preview.sumon.me \
  --base-url http://127.0.0.1:8019 --workers 2 \
  --output /tmp/ilma-phase1-evaluation.json
```

This makes paid Meta requests, never paid TTS requests. All 404 cases must finish
against unchanged code. Overall, comparison and correction acceptance must each
reach 90%, with at least 30 cases in each subgroup. Wrong banks, slots, required
fact coverage, unsolicited protection and response audit violations must all be
zero; every answer must be audited. At least 90% of turns use no more than one
Spark call, and send-to-first-checked-text p95 must be at most 6 seconds. Complete
response timing is retained separately and must not be called first-text latency.

The factual audit compares returned values, condition fields and source metadata
with the canonical database pack, then checks spoken whole clauses and numeric
support against that pack. This catches substituted numbers, dates, bank names,
ranks and sources; it does not independently validate the original financial
documents. Source sign-off remains a later human gate. Samples and partial runs
can diagnose failures but cannot close Phase 1. Stop the temporary evaluation
service after the run; keep the permanent public preview services running.

## Offline service comparison clips

Card readouts never synthesize audio at request time. First run the offline dry run and show its texts/character total to Sumon before spending credits:

```sh
PYTHONPATH=api /home/ubuntu/venv/bin/python scripts/build_service_clips.py --dry-run --json-output /tmp/ilma-service-clip-plan.json
```

After credit authorization, generation uses the explicitly selected private environment and writes drafts outside the checkout:

```sh
PYTHONPATH=api /home/ubuntu/venv/bin/python scripts/build_service_clips.py --generate --max-characters 1500 --env-file /home/ubuntu/shared/all_projects/preview.sumon.me/.env --output /tmp/ilma-service-audio-review-v2
```

There is one provider call per changed text/voice. No generator runs in CI. Review the actual clips, record truthful `reviewed`, `reviewer` and `reviewed_at` fields in the private manifest, then publish only unchanged reviewed audio:

```sh
PYTHONPATH=api /home/ubuntu/venv/bin/python scripts/build_service_clips.py --publish-reviewed --output /tmp/ilma-service-audio-review-v2
```

Review the exact staged manifest/audio list, run the documented suites and policy/secrets checks, and push normally. Deploy to preview first. Keep production unchanged until Sumon's phone acceptance. Confirm the visible text, immediate Listen/Stop behavior and the no-audio fallback; a generated file alone is not listening acceptance.

Before frontend release checks, run `python3 ops/version_assets.py`. Asset URLs contain content hashes to avoid collisions with old Cloudflare cache entries. The frontend suite checks that HTML and the service-worker precache point to the current file bytes. Never reuse a manual asset version label.

Saved service audio URLs also include the audio hash, so replacing a clip after a data update cannot reuse an old Cloudflare audio cache entry. Keep the manifest hash and runtime URL checks together.

The worker registration URL is versioned by worker bytes too. The services UI reads the audio manifest through `/v1/services/audio-manifest` with `Cache-Control: no-store`, so an old empty manifest cannot block newly reviewed clips.

Narration revisions must be dry-run reviewed again. For the complete-sentence revision, use a separate private output folder so earlier audio remains available for comparison. After approval of the revised credit total, a single-sample command can use `--key bn:card-visa-gold --max-characters 1500 --output /tmp/ilma-service-audio-review-v2`; omit `--key` only if all seven revised clips were authorized. Never infer approval of new paid generation from approval of an earlier text version.

Service audio range responses must stream directly to the player. A complete 206 representation is converted to 200 only for background CacheStorage storage; partial fragments are never stored as complete clips. Cache writes must not delay playback or turn a successful network response into an error.

Selected-cost audio acceptance: test each of the five dropdown options separately. The button, visible transcript, manifest key, text hash and file URL must match network + tier + cost. Never fall back to a saved full-card overview. Compare every spoken current amount/condition/date against its source-linked article, confirm old facts are excluded, and verify missing coverage is explicit. For the expanded complete-detail scripts, review the dry-run total and length range before any paid generation; use a new private output directory and explicit reviewed character limit. Preserve previously activated files until new recordings are authorized and verified. Runtime must remain free of provider calls.

## Ordered ElevenLabs accounts and approved card scripts

Configure `ELEVENLABS_API_KEY_1` / `ELEVENLABS_VOICE_ID_1`, then `_2`, then `_3` in the private preview environment. Each voice must be available to its account; a shared voice ID may be used when all accounts have access. `ELEVENLABS_MODEL` selects the model. Legacy unnumbered fields remain a compatibility option for runtime installations without numbered accounts; the approved batch requires all three numbered pairs.

The shared provider module is used by streamed audio tickets, pipeline speech and offline approved generation. Runtime accounts have a 25-second request deadline; the approved offline batch allows 120 seconds per account, with no same-key retry, and a worker-local 15-minute cooldown after the listed retryable statuses or provider codes. HTTP 400/422 stop immediately. Account names and sanitized reasons are logged, never keys or provider bodies. A streaming failure after audible bytes stops that stream rather than concatenating a different account's recording. Non-streamed synthesis is buffered before delivery. Three-account failure stops the batch nonzero and keeps completed files.

Use `scripts/build_approved_card_clips.py --approved-json /private/path/approved.json --env-file /private/path/.env --output /private/staging/folder --generate` only after explicit approval. It sends each text verbatim, without `pronounce()`. Completed manifest entries are persisted after every clip. Valid unchanged text/audio hashes skip further generation on an explicitly authorized resume. Decode and hash-check staged files before copying them to `static/audio/services/`. A partial manifest must state the expected count and incomplete status; do not deploy an incomplete batch silently. Tests use fake clients only.

The 30 October approved 31-script batch saved six files, then stopped on `bn:card-visa-classic-annual-fee`: primary, secondary and tertiary each timed out. Six completed files decode, match their text/audio hashes, and retain their account-name provenance. Twenty-five recordings remain. No new audio release is deployed from this partial batch.

The user subsequently approved 120 seconds per key for offline approved-card generation. The builder defaults to 120 seconds; runtime ticket/pipeline speech retains 25 seconds per key. Buffered offline requests use the streaming endpoint for prompt delivery without exposing partial clips. Always preserve completed files when resuming.

The completed resume now contains all 31 approved cost-specific card recordings (12,884 characters verbatim). All text and audio hashes match, each MP3 decodes, and the release manifest has `batch_complete: true` with zero remaining. Earlier completed files were retained without regeneration. Physical-device/native listening acceptance remains separate from these technical checks.

## Bank-tab preview acceptance

The bank module is separate from services. Deploy `screen/bank-tab-v2` to preview for review; do not merge into the services branch or production before phone acceptance. Check EBL, NBL and South Bangla, hidden empty sections, loss formatting, source sheets, insurance details, announcement filters and history. Capture bank list, three report cards, EBL announcements and NBL history at Small and Extra large. Test rotation, keyboard resize, desktop and 200% text. Existing 31 card recordings must still pass exact-text/hash and actual-playback checks.

Bank reports make no runtime TTS call. Text review is required before offline generation. `scripts/build_bank_clips.py --approved-json /private/path/review.json --output /private/path/staging` is a dry run; add `--generate --env-file /private/path/.env` only after approval. The JSON carries eleven bank slugs, exact text and `source_sha256` values; keep it private until approved. Decode and hash-check generated files before publishing to `static/audio/bank/`. Source fingerprint mismatch must suppress playback.


## Loan preview

Loan examples use the same preview branch as the bank review. Do not reseed the shared MySQL database during preview deployment. Published CSV normalization and read-time API normalization support the existing database without a production migration.

`scripts/build_loan_clips.py --approved-json /private/path/loan-review.json --output /private/path/staging` prints four exact scripts and their character total without calling a provider. Add `--generate --env-file /private/path/.env` only after text and credit approval. The offline request limit is 120 seconds per numbered account in the shared ordered fallback. Keep private draft files outside the repository. Validate text/source/audio hashes and decoded MP3s before publishing reviewed files under `static/audio/loans/bn/`; never mark unheard clips as listening-reviewed. A changed source fingerprint suppresses playback.

Check all four types, amount and term edits without requests or storage, fee-cap changes, source sheets and min/max bounds. Loan audio is not complete until the four reviewed recordings are activated and physical-device playback passes. Preserve the existing 31 card clips and pending bank-report review.

## Deposit preview

Keep database writes out of the preview rollout. Audience and scheme corrections are applied on read; the versioned seed carries only five scheme classification changes. Existing City visibility is respected without overriding hidden rows or reloading the database.

Review fourteen fixed-default scripts outside Git. `scripts/build_deposit_clips.py --approved-json /private/path/deposit-review.json --output /private/path/staging` is dry-run only. Add `--generate --env-file /private/path/.env` only after text and credit approval. It preserves exact text and uses the shared numbered-account order with the 120-second offline deadline. Decode and hash-check files before publishing to `static/audio/deposits/bn/`; retain honest listening-review status. Do not generate pending bank or loan recordings as part of this batch.

Check FDR 12 months at 1 lakh, then 50,000 and 60 lakh; test DPS 3 years, secondary target schemes, senior FDR and NCC tenor detail. Verify savings at 30,000, NCC's low slab and SBAC's unprinted gap. Amount, term, audience and sorting edits must trigger zero requests or persistence. Verify conditional protection and the warning above its sourced limit. Existing card, loan and bank regressions must still pass.
