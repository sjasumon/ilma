# APP_SPEC_02: implementation and acceptance record

## Full live validation with the 8-second model deadline, 29 October 2026

The pushed release `90caf6e` was tested with the contextual engine enabled and
an 8-second model deadline. Paid-provider corpus and scenario tests used an
isolated preview with the same application code and the `ilma` database;
admission limits were raised only on that preview. Public-site checks covered
layout and security headers. No user recording was used or published.

| Check | Observed result |
| --- | --- |
| Backend | 355 tests and 27 subtests passed |
| Frontend | All seven documented Node suites passed |
| Full live corpus | 240/285 passed the evaluator gate, 84.2%; target 95% not met |
| Intent labels | 267/285 matched, 93.7%; includes fallback routing, not generated-answer acceptance |
| Bank retention | Zero bank-target failures and zero unintended bank changes |
| Provider failures | 11 cases encountered a timeout; four unavailable calls had schema failures |
| Typed response time | Median 3,548 ms, p95 8,865 ms, maximum 14,163 ms; excludes ASR/TTS |
| Model calls | 223 turns used one Spark call, 52 used two, ten used three including repair |
| Additional scenarios | 28 turns across dialogs A/B/C, memory, nine demo banks, comparisons and unavailable-bank replies |
| Pronunciation shape | All 28 scenario speech texts passed the no-digits/no-Latin/no-percent/brackets Bangla check; this is not listening acceptance |
| Live app layout | Header/menu, all tabs, BN/EN, scrolling, phone/landscape/keyboard-size/desktop and 200% text checks passed |
| Live headers | Shell, API docs, OpenAPI and health returned 200 with CSP, HSTS and nosniff |
| Repository checks | Policy and full-history redacted secrets scan passed |

The corpus gate requires the expected intent, expected bank and a checked
generated answer; Repeat accepts exact server replay. A successful template
fallback alone does not pass the gate. These are single-run observations, not a
population accuracy or p95 speech-latency guarantee.

Dialog A produced checked generated answers for the opening, history, DPS and
thanks. Dialog B's opening and comparison passed, but its Prime correction used
a template and changed to a three-year comparison instead of explaining the
missing one-year Prime quote and available alternatives. Dialog C declined to
choose a bank and offered factual comparison. Card-to-deposit filters cleared,
bank switching cleared tenor, exact Repeat retained the preceding answer, and
Pubali/Rupali explicitly reported unavailable bank information.

The explicit one-year BRAC FDR probe returned three other banks. The BRAC DPS
probe included EBL Confidence at 8% and SBAC MSS at 10%. The card comparison
probe used fallback wording and spoke the same three banks as its source cards;
this does not establish generated comparison reliability across other inputs.

### Failed and remaining gates

- Comparisons passed only 5/15 corpus cases; corrections passed 7/15. Rejected
  outputs included bank/rate binding, ranks, citations, unsupported values,
  repeated facts and wording constraints. Checks remained enabled.
- First-answer variation failed: ten of 36 bank pairs exceeded 50% shared unique
  words, measured against the smaller word set after removing the next question.
  The two fresh EBL conversations returned identical fallback text. The demo has
  eight strong banks plus one with insufficient status data, not nine strong
  banks; no status was changed to satisfy a test.
- Six real TTS dialog clips measured 30,929, 29,153, 26,906, 24,111, 30,746 and
  11,076 ms. Two exceeded the 30-second limit. TTS-only onset ranged from 859 to
  1,176 ms, excluding understanding, recording and ASR, so it cannot establish
  the end-to-end speed target.
- A browser synthetic-mic round trip transcribed Prime correctly, uploaded one
  compressed recording, played a response and reopened the microphone. Its first
  run failed the one-audio-URL assertion; a diagnostic repeat passed with one
  URL. Treat the initial extra-request/playback observation as unresolved.
  Playback began about 14.7–14.8 seconds after the initial tap in these two runs,
  including capture and ASR. No 95th-percentile speech-start claim is made.
- Real playback stopped in 6 ms or less via Stop, reply tap and synthetic
  voice-detection handoff. Physical microphone echo rejection, noisy speech,
  older phones, TalkBack/VoiceOver and the two-person listening exercise remain
  unverified. Independent financial/source review remains outstanding.

The full automated/live round is recorded; release acceptance has **not passed**.
The owner-authorized live engine remains enabled with the 8-second deadline.
Prioritize term-preserving corrections, factual comparison wording, speech
pagination/duration, intermittent audio requests and fallback variety before
repeating the failed gates and the complete corpus. Private audio and detailed
response artifacts remain outside the published tree.

## Contextual human voice update, 29 October 2026

See [contextual voice behavior and remaining acceptance](specs/HUMAN_VOICE.md).
The new optional engine, signed MySQL memory, fact checker, range-aware service
comparisons and sourced profile loader are implemented behind an activation flag.
Real-data checks confirm one-year BRAC DPS comparisons include SBAC MSS and EBL
Confidence DPS, and Prime's longer DPS terms are preserved. The curated profile
import covers 38 quoted facts across eleven banks; absent fields remain empty.

Live Spark access is restored. The 285-case baseline passed 213 cases, below the
95% target, and 44 cases encountered provider timeouts. Later fixes still need
complete live acceptance. Real-model paraphrase accuracy,
varied wording, three live dialogs, speaking-latency acceptance and two-person
listening are pending. The owner subsequently authorized live activation with an
8-second model deadline; the code default remains disabled. Existing
device, native-speaker and accessibility acceptance is not replaced by mock tests.

Continuation checks: 354 Python tests plus 27 subtests and all seven Node suites
passed. A subsequent isolated live sample passed 45 of 57 cases, with no bank
target failures; all 12 unsuccessful cases encountered a model timeout, sometimes
after a checker rejection. This sample predates the final fallback-only wording
adjustment and is not a replacement for the complete 285-case acceptance run.
A synthetic spoken Prime Bank query was transcribed correctly and selected Prime;
its fallback audio lasted 26.7 seconds. This establishes one round-trip result,
not human listening quality or generated-response latency acceptance.

Verification for this update: 346 Python tests and 27 subtests passed, as did all
seven documented Node suites. Browser checks passed at 360×640, 390×844 and
1366×768, with doubled text, fixed header/menu across all tabs, phone rotation
and keyboard resize. Live Cloudflare responses for the shell, API docs, OpenAPI
and health carried the required security headers. These are automated browser
checks, not physical-device or screen-reader acceptance.

ASR now uses bounded retries with jitter for transient provider responses and
connection/timeouts, within a 25-second total budget. Empty recordings are rejected
as no speech; reaching the recording cap asks for a shorter question. Contextual
memory keeps four redacted turns. These supersede the historical three-turn and
fixed 2/4-second retry entries below.

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


## Connected answer wording — 28 October 2026

Bank answers now connect the assessment to an explanation, explain rounded
ratios/profits in ordinary language, retain years and source qualifications,
and end with a complete polite question. Exact source sentences and figures
remain unchanged in an expandable card. DETAIL/FIGURES progress to unexplained
facts; ordinary follow-ups do not repeat insurance. Explicit repeat or a direct
figure/insurance question can still retrieve the requested information.

FDR answers stay on the product, term and published rate, with a conditional
fixed example before tax. Publication dates are described as schedule dates,
not invented effective dates. Unverified bank-condition notices remain visible
separately from service speech. Full-report playback retains the exact card.
Legacy bank answers and comparison readouts also use connected narration.

Full-name matching checks found and corrected NCC/National and SBAC/Dutch-Bangla
alias overlaps. Generic deposit-insurance requests now outrank spurious weak
bank matches and retain the current bank. Separately named banks still require
disambiguation. Existing
BRAC spellings and scripted-option language retention passed browser checks.

One full paragraph is delivered as text before a single cached MP3 URL. Actual
Bangla recordings measured 10.9–32.5 seconds across seven sourced paragraphs;
Prime’s introduction was 31.2 seconds, its FDR answer 22.5 seconds and qualified
insurance answer 23.5 seconds. The eight-second target is **not met**. Shortening
requires moving content to later turns, not removing eligibility conditions,
increasing playback speed or claiming an unmeasured pass. These are synthesized
clips, not human microphone recordings. A cached Chromium playback check showed
text at 154 ms, playback at 186 ms, end at 31,461 ms and microphone activation
at 31,462 ms, with one audio URL and no scroll displacement. Cold synthesis
previously took about 5–15 seconds, while streaming first bytes in 0.7–1.6 seconds.
Seventy public-source/approved-prompt phrases, including all eleven bank
introductions in both languages, were prewarmed privately. Cache misses and new
voice settings can still require synthesis.

The opt-in source-backed review covers all eleven introductions in BN/EN and
Prime’s details → figures → history → FDR → insurance sequence in both languages.
It checks paragraph/card identity, source IDs, retained language, next questions
and repeated-fact suppression. Source-backed checks use read-only database data;
regression fixtures remain handwritten and synthetic. Browser checks also cover
source sheets, report navigation, cold load, rotation, keyboard-size viewport,
desktop and 200% text. Native phones, TalkBack/VoiceOver, independent lay-listener
comprehension and financial-source acceptance remain pending. This update does
not establish ASR accuracy or blanket production readiness.

Validation for this update: 271 Python tests plus 27 subtests and all seven
frontend suites passed. Thirty-two source-backed paragraph checks passed.
Live Cloudflare checks verified the sourced conversation flow, English
introduction, every-tab responsive chrome and root/API-doc security headers.
The eight-second duration and native/independent listener acceptance remain
open as described above.


## Full pipeline recheck — 29 October 2026

[Voice pipeline checks](VOICE_PIPELINE_CHECKS.md) records real provider probes,
actual browser recording/upload with generated input, newly corrected matcher,
Repeat, planner-argument and audio/typing recovery bugs, and repeatable checks.
The updated suite passed 281 tests plus 27 subtests and all seven frontend suites.
The English City/Citibank ambiguity and initial browser recognition variability
are retained as evidence, not counted as a representative ASR-accuracy pass.
Native/human/offline-clip/source acceptance and the eight-second audio goal remain
open. Database and provider authentication succeeded.


## Short-answer recheck — 29 October 2026

The new 30-word / ten-second policy supersedes the long paragraph timings above.
Strong introductions omit spoken insurance; high-risk introductions retain a
short conditional clause. Full eligibility/payment details, precise figures,
minimum comparisons and the fixed conditional FDR example remain on the card.
Negative capital is rounded to tenths when spoken. FDR card lines omit legal
suffixes and health-status fragments.

Actual TTS measurement found extra generated silence, as well as excess wording.
Short-answer streaming now trims long near-digital pauses and applies a small
3% pitch-preserving pace adjustment after synthesis at 1.1. Synthetic tone tests
check quiet content, pitch, early streaming, cache separation and cancellation.
The previous 31.2-second Prime BN introduction measured 9.072 seconds after these
changes. Native voice-quality/comprehension acceptance remains pending; no person
was represented as having reviewed these generated clips.

The expanded real-audio gate passed **36** source-backed answers across all eleven
bank introductions in BN/EN, the five-turn sequence, protection, comparison and
negative-capital questions. Measured range: **4.608–9.888 seconds**, one clip each,
with both written and pronounced word limits checked. The explicit full-report
readout retains the full card and is outside this ordinary-answer budget.

Final verification passed 288 Python tests plus 27 subtests and all seven
frontend suites. After service restart, the live generated-input browser round
trip passed compressed recording, real Meta transcription, Prime selection,
one 9.1-second reply and microphone reopening after playback. Repeat/source/
typing recovery passed. Live Cloudflare root, API docs and OpenAPI returned 200
with security headers; layout passed phone rotation, keyboard-sized viewport,
desktop and 200% text. These checks do not establish human ASR accuracy or
native-device accessibility acceptance.


## Natural-speech update — 29 October 2026

The ten-second target and extra silence/tempo processing above are superseded
by [the natural speech contract](specs/APP_SPEC_11_speech_wording_and_pronunciation.md).
Replies now use full bank names, fuller sentences and a separate pronunciation
string. Two-person listening/comprehension and physical echo-rejection checks
remain pending; automated duration checks do not establish those outcomes.

Release verification passed 306 Python tests plus 27 subtests and all seven
frontend suites. The real-audio gate passed all 36 source-backed BN/EN samples:
introductions 16.771–21.708 seconds; all replies 4.911–21.708 seconds, one clip each.
Prime's Bangla introduction measured 20.271 seconds; National's 20.114 seconds.
Synthesis remains at the configured 1.1 setting, with no additional tempo or
silence processing. These timings describe the measured cached voice/model,
not every possible future source or voice.

The preview browser passed phone/rotation/keyboard-sized viewport/desktop/200%
layout and Repeat/source/typing recovery. Real audio interruption completed in
2.3–5.6 ms for Stop, reply tap and a synthetic voice-detection handoff. The level
detector separately passed sustained-input, permission, echo-support and cleanup
fixtures. These synthetic checks do not prove physical speaker echo rejection.
A reply-language regression also confirms English replies use English TTS even
when the previous UI language was Bangla.

After deployment, the live service health reported an active database and ready
bank/voice tables. Cloudflare root, Swagger, ReDoc and OpenAPI returned 200 with
CSP, HSTS and nosniff; the application kept its strict self-only script policy.
The live layout check passed, and actual playback stopped in 1.7–2.4 ms through
the three tested interruption paths. The voice-detection path used a synthetic
handoff; physical microphone/echo and two-person comprehension remain pending.
A complete preview playback used one cached MP3 and reopened capture after
playback ended (20.5 seconds elapsed), with no document scroll jump.


## Pipeline reliability recheck — 29 October 2026

[The pipeline checks](VOICE_PIPELINE_CHECKS.md) record corrected early-word
capture, full source-card coverage, invalid/stale audio cache recovery, permission
timer suspension and explicit uncertain-bank confirmation. Real Meta tests
covered a bank question, contextual FDR/details and English City confirmation.
The full suite passed 321 tests plus 27 subtests and all seven frontend suites.
The 36 measured narration paragraphs remain unchanged. Human comprehension and
physical microphone/echo acceptance remain pending; no new ASR-accuracy claim
is made from mixed unlabelled diagnostics or generated clips.

After deployment, the live generated-input browser round trip also passed:
answer at 6.7 seconds, one 20.3-second clip, then capture reopening. Phone/rotation/
keyboard viewport/desktop/200% layout passed. Cloudflare root, Swagger, ReDoc and
OpenAPI returned 200 with security headers and the application kept its strict
self-only script policy. A stale pending bank ID is cleared without a server
error. The original private reviews, recordings and diagnostic outputs remain
outside the published tree.
