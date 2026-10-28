# Production readiness audit — 27 October 2026

**Verdict: NO-GO for unrestricted production. Suitable for controlled testing.**
Remediation progress is tracked in [RELEASE_HARDENING.md](RELEASE_HARDENING.md).
The original script-mismatch attribution below was corrected by retained-data
analysis: both saved cases were false rejection of valid Bangla danda punctuation,
not proof that Meta returned an unexpected script. Source/device acceptance is
still outstanding.
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
- Remediation installed daily cleanup/backups and two-minute health monitoring.
  First cleanup, backup, isolated restore and controlled crash recovery passed.
- App service runs as ubuntu with `NoNewPrivileges`, `PrivateTmp`, a read-only
  system filesystem and resource ceilings. See the hardening record for details.

## Release blockers and required evidence

| Priority | Finding | Required before public production |
| --- | --- | --- |
| P0 | Diagnostic mode currently retains original audio, Meta transcripts and result events in MySQL, as requested for testing. | Set production mode and diagnostics off; explicitly decide retention/deletion of existing samples and backups. Verify new requests create no diagnostic rows. |
| P0 | Daily idle diagnostic/log pruning is now installed and tested. Existing exports/backups have separate retention. | Verify ongoing scheduled success and agree deletion of existing test exports/backups before production. Disabling capture alone does not delete them. |
| P0 | The false script rejection caused by Bangla punctuation is fixed; both original saved recordings now complete end-to-end. Real quiet/noisy phone corpus metrics remain missing. | Replay labelled real recordings; measure transcript accuracy, bank/intent accuracy, no-speech rejection and per-stage latency for BN and EN, including failures and corrections. Agree acceptance thresholds before launch. |
| P0 | Financial rows are agent-labelled; manual checks remain, including NCC figures, rating dates and source metadata. 25 service attributes are withheld after the v5.4 refresh; manual source acceptance remains pending. | Complete and record the reviews in `seed/TO_CHECK.md`; retain unavailable states until evidence supports publication. Do not imply independent regulatory verification. |
| P0 | Pre-provider global/client limits, concurrency ceilings, upload deadlines and explicit origins are deployed. Atomic ilma MySQL counters/leases now share budgets across two workers. | Finish representative sustained/abuse testing and trusted ingress enforcement. CORS alone is not an abuse control. |
| P0 | Physical TalkBack/VoiceOver and mobile microphone acceptance is outstanding. | Test permission denied/revoked, interruptions, background/resume, single/double taps, keyboard activation, slow speech, 200% text and offline recovery on actual Android/iOS devices with target users. |
| P1 | Shorter summaries completed bank speech in 13.87s and service speech in 12.32s for two saved recordings. Representative latency remains unmeasured. | Measure end-to-end p50/p95 under representative load and outages. Two successful probes do not establish the response-time target. |
| P1 | Twenty private offline audio drafts are generated; insurance clips are blocked and native review/publication is incomplete. | Review/publish the required bundle once complete and validate a real offline session. |
| P1 | The official bank-insurance rule is now sourced. Approved v6.2 history is imported with incomplete-coverage warnings; Watch explicitly says notifications are coming soon. | Keep unavailable capabilities clear; finish source/native review before broader claims. These need not block a narrower, accurately described release. |
| P1 | Local backup/isolated restore, crash recovery, rollback startup canary and local failure signals pass. External alerts, encrypted off-host recovery and traffic switching remain unverified. | Configure authorized destinations, restore off-host, rehearse public-traffic rollback and finish sustained capacity/outage acceptance. Never use `project_db`. |

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
The audit itself changed no settings; subsequent authorized hardening is recorded
in the remediation document. Diagnostic capture remains active for the test phase.

Recommended sequence: finish labelled voice diagnostics, add provider admission
controls and scheduled retention, complete source/accessibility acceptance, then
perform a documented production configuration switch and operational rehearsal.
