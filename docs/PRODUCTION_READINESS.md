# Production readiness audit — 27 October 2026

**Verdict: NO-GO for unrestricted production. Suitable for controlled testing.**
This audit combines current code review and fresh live checks with previously
recorded voice/browser acceptance evidence. Passing tests and a healthy database
do not establish speech accuracy, financial correctness or accessible usability.

## Fresh verification

- Public HTTPS `/v1/health`: `ok=true`, release `export-v5.2-2026-10-27`,
  database connected and bank/voice tables ready.
- Host runtime configuration: database **ilma**, environment **development**,
  diagnostics **enabled**. No credentials or recordings were exported for this audit.
- `ilma-app.service` is enabled and active, `Restart=always`, zero automatic
  restarts in the current activation. This verifies configuration, not a reboot drill.
- 64 Python tests and 25 subtests pass; all five Node suites pass.
  `pip check` reports no broken requirements.
- Host timer inventory contains no ILMA cleanup timer. The committed cleanup
  service template points to `/opt/ilma`, unlike this deployment's actual path.
- App service runs as ubuntu; `NoNewPrivileges` and `PrivateTmp` are disabled.
  This is an operational hardening gap, not evidence of an exploit.

## Release blockers and required evidence

| Priority | Finding | Required before public production |
| --- | --- | --- |
| P0 | Diagnostic mode currently retains original audio, Meta transcripts and result events in MySQL, as requested for testing. | Set production mode and diagnostics off; explicitly decide retention/deletion of existing samples and backups. Verify new requests create no diagnostic rows. |
| P0 | Seven-day/200-sample diagnostic pruning runs on capture or explicit CLI use. Ordinary log cleanup has no installed daily timer. Idle records can outlive the intended retention period. | Install a correctly configured daily cleanup job for both ordinary logs and diagnostic samples; test expiry without a new voice request and alert on failure. Disabling capture alone does not delete existing rows. |
| P0 | ASR accuracy is not accepted. Previously tested bank-name audio succeeded, while a synthetic Bangla Signature question returned an unexpected script and was rejected. Real quiet/noisy phone corpus metrics are missing. | Replay labelled real recordings; measure transcript accuracy, bank/intent accuracy, no-speech rejection and per-stage latency for BN and EN, including failures and corrections. Agree acceptance thresholds before launch. |
| P0 | Financial rows are agent-labelled; manual checks remain, including NCC figures, rating dates and source metadata. 87 service attributes are withheld. | Complete and record the reviews in `seed/TO_CHECK.md`; retain unavailable states until evidence supports publication. Do not imply independent regulatory verification. |
| P0 | No general pre-provider admission limit exists for public transcription and speech routes. The 20-question quota is applied after transcription/intent and exempts some intents; anonymous device IDs are client-controlled. CORS allows all origins. | Apply trusted server/proxy rate and concurrency limits before paid calls, upload/read deadlines and resource budgets. Restrict browser origins to intended deployments. Load-test normal use and abuse without generating uncontrolled provider costs. CORS alone is not an abuse control. |
| P0 | Physical TalkBack/VoiceOver and mobile microphone acceptance is outstanding. | Test permission denied/revoked, interruptions, background/resume, single/double taps, keyboard activation, slow speech, 200% text and offline recovery on actual Android/iOS devices with target users. |
| P1 | Previous full spoken report took 24.75 seconds, exceeding the 15-second target. Current speech deadline is 25 seconds. | Measure end-to-end p50/p95 under representative load and outages; shorten speech or change delivery to meet the agreed response target. Increasing the timeout does not improve latency. |
| P1 | Fixed offline audio has not been published and native-speaker pronunciation review is incomplete. | Generate/review/publish required clips and validate a real offline session. |
| P1 | Official insurance input and incident-history input are absent; Watch has no notifications. | Keep these capabilities explicitly unavailable or finish them before advertising them as supported. These need not block a narrower, accurately described release. |
| P1 | Database backup/restore, rollback, alerting, provider outage drills and capacity limits have no accepted evidence. | Restore an `ilma` backup to an isolated target, rehearse deployment rollback and restart, configure health/latency/error alerts, and document proxy timeouts and operational ownership. Never use `project_db`. |

## Pipeline review

The implemented path is browser recording → bounded upload → ffmpeg conversion
→ Meta ASR → visible transcript → bank matching/constrained intent → MySQL
facts/services → SSE answer → optional ElevenLabs speech. Typed input joins the
same matching/answer path. Unsupported or ambiguous input does not default to EBL.

Existing safeguards include a 15-second recording cap, 1 MiB audio limit,
conversion/provider timeouts, recorder cleanup, transcript-first events, explicit
empty-data and unexpected-script errors, source-backed numeric answers, hidden
offer exclusion, private-request cache exclusion and sanitized provider failures.
These are useful safeguards; they do not substitute for the missing acceptance work.

The 1.5-second default silence stop and 15-second cap particularly need testing
with slow speakers. Permission prompts, browser/OS interruptions and variable
mobile audio encoding require device evidence beyond the automated recorder tests.

## Audit boundaries

This is not a penetration test or a new measured speech benchmark. Prior browser
and paid-provider observations are recorded in `BANK_SERVICES_ACCEPTANCE.md` and
`VOICE_ACCEPTANCE.md`; they were not repeated or relabelled as fresh measurements.
No production settings were changed, no recordings deleted and no unrelated
database accessed. Diagnostic capture remains active for the authorized test phase.

Recommended sequence: finish labelled voice diagnostics, add provider admission
controls and scheduled retention, complete source/accessibility acceptance, then
perform a documented production configuration switch and operational rehearsal.
