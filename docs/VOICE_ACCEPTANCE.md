# APP_SPEC_02: implementation and acceptance record

Authority: [APP_SPEC_02_voice.md](specs/APP_SPEC_02_voice.md). This record distinguishes
implemented code from checks that require the deployment host or real people.
It does not claim that unexecuted live or human checks passed.

Current remediation evidence is in [RELEASE_HARDENING.md](RELEASE_HARDENING.md):
74 Python tests, five Node suites, the Bangla punctuation correction, successful
replays of both formerly rejected recordings, deployed admission/retention,
isolated backup restore and crash recovery. Historical deployment incidents below
are not current blockers. Physical/native/source acceptance remains outstanding.

## Implemented

| Spec | Behavior / artifact | Verification |
|---|---|---|
| §0–1 | Meta ASR through ILMA, no browser speech fallback, input-specific results | Mocked provider + UI tests; no default EBL |
| §2 | MediaRecorder WebM/MP4, 1.5s configurable silence, 15s cap, 6s no-speech, 300ms noise measurement, shared RMS orb, tones/haptics | Recorder tests; physical phone still required |
| §2 | First-tap permission explanation; Home/Bank/Services context, last three non-sensitive exchanges | UI tests; actual browser permission/TalkBack still required |
| Home gesture | Single tap starts recording; while recording, two taps within 450ms stop and search. Explicit stop button remains available; BN/EN recording instructions explain the gesture | UI regression covers single taps, separated taps and double-tap input-specific routing; physical touch/TalkBack validation pending |
| Home waveform | Horizontal gold/cyan SVG replaces the orb; actual microphone levels drive listening, request lifecycle drives processing, and player events drive speaking. Native voice button, four tabs and current theme retained | UI regressions cover listening/processing/idle, playback/error and reduced-motion state. Physical device/accessibility review remains pending |
| Search feedback | Error, clarification and typed search use a native modal dialog in dark teal/gold; retry closes it before recording, Escape/close dismiss it. Microphone status text is capped at 24px | Regression tests cover modal open/retry/close; frontend styling does not resolve upstream transcription failures |
| §3 | ffmpeg memory pipes → 24kHz mono PCM WAV; standard ASR, correct bias, no keywords; 8s deadline, 429/500 retries at 2s/4s | Multipart/retry tests, actual synthetic-audio ffmpeg conversion and live Meta authentication pass; speech accuracy/latency remain unmeasured |
| §3.3 | Duplicate words/halves, known Janata Hindi output, remaining Hindi rejection, punctuation cleanup | Spec examples tested |
| §4 | NFC/digits/affix normalization, bilingual sliding-window RapidFuzz, 90/75 thresholds, four choices, risky short-name confirmation | Normalization/routing tests and actual RapidFuzz test pass |
| §4 | Demo-bank aliases + supplied mishearings, with provenance, added only to existing institutions | All nine demo banks loaded into ilma from the supplied v5.2 CSVs; required aliases added. Manual source review remains pending |
| §4 | Explicit unlicensed records get a not-licensed response, never a fraud claim | Unknown ASR matches remain unclear; absence of a match is not proof of licence status |
| §5 | Spark temperature-0 constrained intent JSON, matcher/context ID whitelist, number normalization, name-only shortcut | Mocked intent/schema tests |
| §5 | Fixed fact queries, sourced status/rates/insurance/detail answers, reviewed glossary, verified grounded wording with one retry/template fallback | Number/citation/banned-claim tests; unsupported data returns no-data |
| §5 | At most one clarification; no amounts, PINs, account numbers, audio or raw transcripts in MySQL logs | Control-flow and retention tests; client omits sensitive history |
| §6 | ElevenLabs live speech/readouts, pronunciation lexicon, slow 0.85×, one audio player, stop-on-interaction | UI/lexicon tests and live configured-voice access pass; generated speech quality and native review pending |
| §6 | Fixed clip generation → Opus 48kHz mono 32kbps + MP3 64kbps, loudness/trim recipe, 2MiB cap, native review/hash gate | Asset validation tests; actual clips not generated/reviewed here |
| §7 | 70% Latin rule after alias/loanword removal; remembered manual language; return-to-Bangla chip | All supplied examples + stream/UI tests |
| §8 | Retry/type paths, noise tip, offline mic guard, cached public reports marked offline, no upload caching | Five Node suites including offline cache tests |
| §8 | MySQL daily AI counter; status/insurance/rate templates exempt; daily retention job | Counter/retention tests; anonymous device headers are not full device authentication |
| §9 | /v1/voice audio+context, /v1/ask text+context, transcript/match/result/speech SSE; owned streaming DB session and audio release | Fragmented UTF-8 SSE + route tests |
| §10–11 | Replay CLI with explicit CSV column mapping, real-voice collector, metric thresholds, clean-real <90% review flag | Harness/threshold tests; datasets and people are not available here |

Waveform integration browser checks: headless Chromium at 320×568, 390×844 and
1440×900 passed startup without JavaScript errors, horizontal overflow checks,
settings open/close and reduced-motion preference propagation. These checks do
not substitute for physical microphone, TalkBack or VoiceOver testing.

All runtime database persistence uses MySQL. SQLite is only used for isolated test
fixtures. The migration never inserts bank fundamentals or sample institutions.
Glossary text is authored from FRD §21.2; native speech review is a separate gate.

## Deployment-host steps

The earlier workspace connectivity blocker is resolved as of 2026-10-27. The
agent successfully connected to the configured MySQL database, applied the voice
migration, and verified Meta authentication and ElevenLabs configured-voice
access. Dependencies are installed in the existing venv. For subsequent host setup
or readiness checks:

```sh
# Set this to the existing venv; this workspace uses /home/ubuntu/venv.
export ILMA_VENV_PATH=/home/ubuntu/venv
bash ops/bootstrap_voice.sh
export PYTHONPATH="$PWD/api"
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_doctor --live
"$ILMA_VENV_PATH/bin/uvicorn" ilma_api.main:app --host 0.0.0.0 --port 8001
```

Use HTTPS for phone microphones. Bootstrap reuses the active/existing venv; it never creates another one. It installs requirements and runs the
non-destructive MySQL voice migration. The doctor reports flags and error codes,
never keys/passwords. An incomplete readiness report exits nonzero. Confirm that
all nine demo banks exist in the verified bank data. Do not run the legacy
hard-coded seed loader against production to satisfy this check.

For daily retention, adjust /opt/ilma and the service account in
`ops/ilma-voice-cleanup.service`, then install/enable its accompanying systemd
timer. Cleanup removes logs older than 30 days and expired counters.

## Fixed audio and native review

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_assets generate --directory voice-drafts
```

Listen to every Bangla and English clip, including the actual database insurance
wording, with a native speaker. Correct text/voice settings and regenerate if
needed. Review both Opus and MP3. No reviewed flag is created automatically.
After an actual reviewer has checked every clip:

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_assets review --directory voice-drafts --reviewer 'REVIEWER_INITIALS' --all
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_assets publish --directory voice-drafts
```

Publish refuses missing/unreviewed/changed clips and a bundle over 2MiB. Review
metadata stays with the assets. User recordings are never put in this directory.
The app caches only the complete approved bundle for offline errors/hints.

## Synthetic replay

Copy the existing `H:\Projects\ilma-test\audio` and reference CSVs to a private
host directory. The replay tool accepts file/filename/audio_file/audio_path/path,
bank_id/institution_id/bank/expected_bank, and language/lang. For other column names
use --file-column, --bank-column and --language-column. Windows paths are accepted
via their basename when replaying a copied directory.

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.replay_voice --audio-dir /PRIVATE/audio --manifest /PRIVATE/references_tts.csv --suite clean_bn --report voice-reports/clean.json
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.replay_voice --audio-dir /PRIVATE/audio --manifest /PRIVATE/references_noisy.csv --suite fan_bn --report voice-reports/fan.json
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.replay_voice --audio-dir /PRIVATE/audio --manifest /PRIVATE/references_en.csv --suite english --report voice-reports/english.json
```

Create voice-reports first. Reports redact numeric input. Bank accuracy counts
only clips with an expected bank; English language accuracy counts all English
clips. Thresholds: clean Bangla >=98%, fan >=95%, English language >=98%, median
result <=4s. Both transcript/result latency and error counts are retained. These
thresholds are evaluated, not assumed from the previous synthetic baseline.

## Real people and phone checks

The acceptance page is disabled by default. For an authorized physical-device
test window, set `VOICE_TEST_PAGE_ENABLED=true` in the private environment and
restart the service, then open `/voice-test` on the HTTPS host. When disabled,
both `/voice-test` and `/static/voice-test.html` return 404. Turn the flag off
and restart after the window. This explicit switch is separate from diagnostic
audio retention. The page is a recording-only acceptance tool:
recordings stay in browser memory until explicitly downloaded and are never
uploaded by that page. Obtain participant consent. Use the builder, a woman and a
person over 60; use codes, not real names. Download at least 20 samples, covering
nine demo-bank names and five question recordings, split between quiet and TV/fan
conditions. The page downloads the corresponding references_real.csv.

```sh
PYTHONPATH=api "$ILMA_VENV_PATH/bin/python" -m ilma_api.replay_voice --audio-dir /PRIVATE/real --manifest /PRIVATE/references_real.csv --suite real --report voice-reports/real.json
```

Real replay refuses to pass insufficient role/condition/prompt coverage. If clean
real bank accuracy is below 90%, the report sets requires_manual_review=true:
send that report to the designated reviewer before proceeding with deployment.
The agent has not messaged another person or represented itself as a reviewer.

On a cheap Android over mobile data verify, in order: permission explanation,
“ইস্টার্ন ব্যাংক”, “ব্র্যাক ব্যাংকের এফডিআর রেট কত”, “Is City Bank safe?”, an
ambiguous name, denied permission, fan noise, then offline cached reports. Repeat
with TalkBack and 200% text. Confirm transcript precedes routing, correct bank or
services answer, source links, language chip, stop/slow/mute, and typing fallback.

## Current evidence

Latest bank/services update: all nine banks are now loaded into **ilma** from
Sumon's supplied v5.2 CSVs, together with 43 financial facts, nine ratings and
470 service attributes. The eight-strong/one-no-data baseline passes unchanged.
Host health is ready; the earlier missing-bank blocker is resolved by this
supplied dataset, not by using another database. See
[BANK_SERVICES_ACCEPTANCE.md](BANK_SERVICES_ACCEPTANCE.md) for 64 pytest checks,
UI screenshots, source-review gaps and the actual typed/voice routing evidence.

The following paragraphs record earlier stages of the work.


User database clarification: `ilma` is canonical; `project_db` is unrelated. The
previous switch was incorrect and has been reverted. The service now uses
`DB_NAME=ilma`; ILMA tables and authored glossary were initialized there without
importing bank facts. No institution dataset is loaded yet, so health readiness
is false and recognized questions receive an explicit data-not-loaded response.
Earlier results using `project_db` are historical, not valid data acceptance.


Historical pipeline follow-up, before the database clarification: see [VOICE_PIPELINE_AUDIT.md](VOICE_PIPELINE_AUDIT.md).
The host service's wrong database selection is corrected using the systemd
override in `ops/ilma-database.conf`; public bank lookup and a typed report-card
request now work. Forty-eight Python checks and five Node suites pass. Three
saved-recording replays produced a report, a clarification and a script rejection,
without database errors. Dataset completeness, real speech accuracy and physical
device checks remain pending.

Optional development diagnostics now support paired original audio, raw ASR
text, language and match/result/error events in MySQL. Both development mode
and an explicit enable switch are required; production defaults do not capture.
No live capture was enabled and no production diagnostic table was created.
See [VOICE_DIAGNOSTICS.md](VOICE_DIAGNOSTICS.md) for isolated setup, intended
question labels, private exports and retention behavior. Three regression tests
cover production blocking, explicit opt-in and paired sample persistence.

Activation update: the user subsequently explicitly requested capture for the
current diagnostic test. Enabled the two private switches, created the MySQL
diagnostic table and restarted `ilma-app.service` on 2026-10-27. This instance is
temporarily operating in development diagnostics; restore production/disabled
switches after testing. No private configuration or samples are committed.

Unexpected-script diagnosis: `clean_transcript` rejects remaining Devanagari
characters as required by §3.3. Previously this happened before the transcript
event, incorrectly making a returned ASR transcript look absent. Rejected text
now streams to the user before `transcript_language_mismatch`, with an editable
correction field. It is not used to choose a bank or stored in logs. Repeated
provider/language errors no longer automatically imply noise. Backend warnings
record fixed error codes only. No real-user error percentage or improvement in
Meta recognition accuracy has been measured by this fix.

Transcript feedback update: voice transcription now precedes loading the bank
index. If that lookup fails, SSE delivers the transcript before the sanitized
database error. The dialog preserves the current attempt's question above the
error and explicitly indicates when no transcript was received; retry clears
the prior voice transcript. Regression tests cover database failure ordering and
preventing an old question from appearing as the new recording's transcript.

Updated 2026-10-27 after the workspace access change:

- All 39 Python checks passed again after migration. All five Node suites passed
  previously; they were not rerun for the migration-only change.
- RapidFuzz is installed. Actual ffmpeg WAV conversion and Opus/MP3 normalization
  passed using the existing `/home/ubuntu/venv`.
- Live MySQL connectivity and voice-table readiness passed. Migration added the
  alias source column, three voice tables, 15 aliases and 94 authored glossary
  entries. A MySQL collation duplicate-alias issue was fixed before completion;
  existing aliases are preserved. No bank financial facts or sample institutions
  were inserted.
- Live Meta authentication and ElevenLabs configured-voice access passed. These
  probes do not establish real speech recognition, answer or pronunciation quality.
- No credentials were printed. Runtime requests do not save audio to disk.

## Remaining acceptance gates

Host diagnostic follow-up, 2026-10-27: the latest saved user sample decoded to
11.99 seconds, had a non-empty Meta transcript and ended in
`bank_data_unavailable`; this was not the 15-second recording limit. Running the
existing migration in the systemd service's host context stopped with
"Create/load the verified bank schema first" because its required institution
tables were unavailable there. Earlier agent-context MySQL checks do not prove
the host service has the verified bank schema/data. Do not create sample bank
facts to bypass this gate; reconcile the host database configuration/import.

Deployment incident, 2026-10-27: `https://app.sumon.me` served frontend asset
version 15, but its published OpenAPI document omitted `/v1/voice`, `/v1/ask`,
`/v1/speech` and `/v1/voice/config`. Empty POST probes to voice/ask and GET config
returned 404. No user recording was sent in these probes. Local live Meta
authentication still passed. Deploy/restart the current `ilma_api.main:app` and
verify reverse-proxy routing before retesting speech. Updating static assets
alone cannot activate Python routes. The frontend now identifies missing voice
routes explicitly; it does not claim the deployment has been repaired.

Resolved later on 2026-10-27: the existing `ilma-app.service` was already enabled
at boot with `Restart=always`, but its process predated the voice implementation.
Restarted that service. Both localhost:8001 and `https://app.sumon.me` now return
200 for `/v1/voice/config`, and both OpenAPI documents contain all four voice
routes. Service is active/running. This resolves the missing-route incident;
physical microphone transcription still needs a fresh phone test.

The overall readiness command still exits nonzero. Connectivity and dependency
installation are no longer blockers; the following work remains:

- **Manual source review:** the original nine banks and two supplemental banks are present.
  Complete `seed/TO_CHECK.md`; agent-imported rows are not marked as personally
  checked by Sumon. The official bank-insurance rule is now sourced; approved v6.2
  incidents now support qualified history answers. Source review and complete
  search-window coverage remain outstanding.
- **Offline voice bundle:** all 22 private drafts are generated, including the
  sourced insurance clips. Obtain actual native-speaker review and
  publish the approved bundle. `reviewed_offline_clips` remains false.
- **Synthetic and real speech acceptance:** replay the referenced corpora and
  consented participant recordings; accuracy and latency thresholds have not
  been measured.
- **Physical device/accessibility checks:** microphone permissions, Android/mobile
  data, TalkBack, 200% text and offline behavior still require hands-on validation.
- **Deployment operations:** daily retention, local backup/isolated restore,
  local health monitoring, crash recovery and HTTPS are now verified. External
  alerts, encrypted off-host recovery, capacity tests and traffic rollback remain.

## Guided tap-or-talk mode (28 October 2026)

Implemented first-use/Voice only steps and exact server command dispatch are
documented in [TAP_OR_TALK.md](TAP_OR_TALK.md). Automated timing and synthetic
browser checks are separate from real microphone/provider and screen-reader
acceptance. New clip pronunciation review and physical TalkBack/VoiceOver
walkthroughs remain pending; no native wrapper is present in this repository.

## Scripted voice agent

See [VOICE_AGENT.md](VOICE_AGENT.md). Automated fixtures cover the allowlisted
tools, source checks, scoped plans, template fallback, explicit watch yes, six
turns and the BANK → SERVICES → SERVICE → COMPARE → BANK path. These fixtures
do not establish real transcription accuracy or the target speech duration.
Physical phone/eyes-closed and native screen-reader acceptance is still pending.

Voice-only activation correction: a fresh browser opens normal Home. Only the
saved `voiceonly` switch starts the guide; disabling it survives reload.
Settings opened without changing that switch resumes the current guided step.
Automated settings and synthetic browser regressions cover these cases.


## Speed update — 28 October 2026

The [speed specification](specs/APP_SPEC_08_speed.md) supersedes earlier latency,
serial model wording/check and microphone-window descriptions in this record.
Answers now precede streamed/cached speech, simple factual turns use templates,
and free turns use at most one bounded Spark PLAN. Agent/guided recording allows
8 seconds to start and 15 seconds total, with two silence re-asks. Historical
checks above remain dated evidence, not a statement of the current architecture.
See [VOICE_SPEED.md](VOICE_SPEED.md) for measured provider/browser timing and
remaining real-device/accessibility acceptance. Source financial review remains
unchanged and must not be inferred from speed tests.


## Conversation language and loop recovery — 28 October 2026

[The recovery specification](specs/APP_SPEC_09_language_and_recovery.md) adds
current-option precedence, cross-state commands, retained context on misses,
a metadata-only question-loop guard and inline typing after two misses.
Transcript/result/conversation language and speech agree for spoken and typed
questions. The client supports both automatic-switch directions and a language
undo that retains the bank. Tap replies retain conversation language. Twenty
turns replace the earlier six-turn bound; idle/navigation reset is unchanged.

Synthetic tests cover ten consecutive replies, ambiguous “ঢাকা” twice, global
DETAIL/services/product commands, voice and typed language cases, TTS language,
exact consent and the question-only guard. Browser checks cover source-backed
local read-only tools, bilingual undo, keyboard focus, retained context, inline
typing recovery, portrait/rotation/keyboard-size/desktop/200% text and existing
agent integration. Provider responses and microphone media in regression tests
are synthetic; this does not establish native pronunciation, ASR accuracy or
TalkBack/VoiceOver acceptance. Financial source review remains pending as before.

Validation for this update: 231 Python tests plus 25 subtests and all seven
frontend suites passed. Live Cloudflare conversation/frame checks passed; root,
API docs, redoc and OpenAPI returned 200 with security headers verified.


## BRAC aliases and scripted-reply language — 28 October 2026

The user-approved spellings “breakbank” and “ব্রেক ব্যাংক” are stored as BRAC
aliases in ilma, tagged with user-report provenance. An idempotent migration
adds them without replacing source names or financial facts. The standard voice
migration also reapplies them after seed reloads.

Matched scripted replies retain conversation language before the transcript
language event is emitted, including current options, fuzzy synonyms and global
navigation commands. “more details” in a Bangla conversation therefore retains
Bangla text, narration and next options. Genuine questions still use language
detection. Synthetic tests cover both languages, current/global states, TTS
language, idempotence and exact alias routing. The full suite passed 242 tests
plus 25 subtests; all seven frontend suites passed. Live browser checks used
typed spellings with speech disabled; they do not establish microphone accuracy.


## Spaced BRAC alias — 28 October 2026

“break bank” is added alongside “breakbank” and “ব্রেক ব্যাংক”. Matched whole
alias phrases are removed before language-letter counting; a bank-name-only
transcript retains the current conversation/UI language. Real question words
still select their language. The word “break” alone requires confirmation
instead of silently selecting BRAC. Source names and financial facts are unchanged.

Synthetic text/voice-path tests verify all three spellings with both BN and EN,
including transcript/result/TTS language. The opt-in browser check now covers the
spaced spelling as well, using typed inputs with speech disabled. Actual phone
recognition and native accessibility remain separate acceptance items.

This update passed 256 Python tests plus 25 subtests and all seven frontend
suites. Live typed-input browser checks verified all three aliases without
changing Bangla, plus responsive frame and Cloudflare/API-doc security headers.


## Capital explanation wording — 28 October 2026

The P1 capital explanation now states the configured base minimum plus buffer
(currently 10% + 2.5%) in both languages. It says the combined threshold is met,
which includes equality, rather than describing only a 10% legal minimum. The
configuration, status decisions, source quotes and financial rows are unchanged.
A synthetic boundary test checks both the current configuration and an alternate
base/buffer pair to prevent hardcoded wording.

Validation: 257 Python tests plus 27 subtests, all seven frontend suites, and
live EBL reason/card checks passed, including rotation, keyboard-sized viewport,
desktop, 200% text and Cloudflare/API-doc security headers. This is a wording
correction, not independent regulatory or financial-source acceptance.
