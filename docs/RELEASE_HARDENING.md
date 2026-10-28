# Release hardening progress

Latest website/insurance changes and live browser evidence are recorded in
[WEBSITE_FIXES_2026-10-27.md](WEBSITE_FIXES_2026-10-27.md). Historical missing-
insurance-source statements below are superseded by that sourced rule.

## Stage 1 — deployed 27 October 2026

All provider-producing POST routes (`voice`, `ask`, `speech`, service `readout`)
now share pre-provider admission: 12 requests/client/minute, 60 global/minute,
1,000 global/day, 2 active/client and 4 active/global. These are configurable
ceilings, not a promise of provider billing limits. Invalid requests also consume
admission. As of the speed update, atomic MySQL counters/leases share quotas across two
workers. Process-local admission remains a single-worker development option.
Clients behind a shared address share its allowance. No device-ID or raw
forwarded-header value is used by the middleware.

Disallowed browser origins receive 403 before paid calls; CORS uses an explicit
origin list. Non-browser clients still require admission; CORS is not authentication.
Protected uploads have a 20-second total read deadline and bounded memory;
speech JSON is limited to 16 KiB. Concurrent slots span the complete SSE response
and are released after cancellation or failure.

The host daily cleanup timer is enabled. Its first manual run succeeded and
the next run is scheduled. Cleanup now expires seven-day diagnostic samples and
enforces the 200-sample cap even after capture is disabled or when traffic stops,
alongside ordinary 30-day logs and expired counters. Current recent diagnostics
remain available for investigation; capture stays enabled for the authorized test.

Evidence: 69 Python tests / 25 subtests and five Node suites pass. New tests cover
shared limits, changing device IDs, concurrency, cancellation, oversized/slow
uploads, denied origins and idle expiry with capture disabled. Live health remains
healthy and a disallowed-origin POST returns 403. No provider calls are made by
the rejection tests.

See `PRODUCTION_READINESS.md` for original findings. Its missing-admission and
missing-timer findings are superseded by this stage; other launch gates remain.

## Stage 2 — deployed voice correction

Retained-data analysis found that both saved `transcript_language_mismatch`
failures contained **no Devanagari letters**. Valid Bangla danda/double-danda
punctuation sits inside that Unicode block and the broad rejection expression
incorrectly rejected it. Cleanup now accepts the shared punctuation while still
rejecting actual unsupported script. Regression tests cover Bengali, mixed
English/Bengali and real Devanagari text. Earlier documents attributing these
two failures to Meta's script choice were incorrect; their interpretation is
superseded here.

Replayed both original saved audio recordings through the deployed HTTP pipeline,
including fresh Meta transcription, MySQL answers and ElevenLabs speech:

| Case | Transcript | Result | Generated speech complete |
| --- | --- | --- | --- |
| Bank question | 3.00s | report_card, 5.66s | 13.87s |
| Signature service question | 2.48s | service_answer, 10.42s | 19.49s |

Neither returned an error. These two probes do not establish corpus accuracy or
p95 latency. The service case still misses the 15-second spoken-answer target.

Follow-up: service speech now uses the same three source-backed values with short
bank aliases, stale warnings and a source-date/conditions reminder; full names,
dates and source links remain visible. Replaying the same saved service recording
then produced transcript **2.35s**, result **7.48s**, speech **12.32s**. This meets
the spoken target for that probe, not for a representative population.

Report speech now uses the bank status and first sourced reason plus a brief
disclaimer; the full report, other reasons and sources remain on screen. A direct
speech probe reduced the report from 255 visible to 144 spoken characters and
generated audio in 9.38s. Other saved failures included historical database
errors after successful transcription, a genuine silent 0.1s sample, and one old
sample without sufficient stage evidence. None were relabelled as recognition
failures. There are only seven original retained samples and no intended-question
labels, so no speech accuracy percentage is claimed.

New request-limit/upload/origin errors have localized frontend messages. Shell
asset version 29 ensures clients receive them rather than four-hour cached JS.

## Stage 3 — host operations verified

- Private local daily MySQL backups are installed under `/var/lib/ilma-backups`,
  directory 0700, files 0600, SHA-256 manifests, seven completed snapshots retained.
  Credentials travel through a temporary private option file, never process
  arguments or metadata. Client configuration ignores unrelated host defaults.
- The first successful backup was restored into a new isolated database: 17
  tables, 9 institutions, 43 facts, 470 service attributes, 1 release. Schema/key
  counts matched and only the newly created restore database was removed.
  The app user correctly lacks database-creation privileges (1044); local root
  socket administration performed the drill without expanding runtime grants.
- The app runs with NoNewPrivileges, PrivateTmp, a read-only system filesystem,
  0077 umask, task/memory ceilings and one worker. Current public health is ready.
- A controlled main-process SIGKILL was followed by automatic restart and healthy
  response within the recovery probe's 4.23s window; NRestarts became 1. No host
  reboot was performed because this machine also runs unrelated applications.
- The previous revision `26f729e` passed an isolated localhost rollback canary
  against the current schema. This validates its startup/schema compatibility;
  it is not a rehearsal of switching public traffic or restoring older data.
- Local health checks run every two minutes. Failed monitor/backup/cleanup units
  produce an `ilma-ops` error journal entry. The real initial backup failure
  exercised this signal. **No external alert delivery is configured.**
- 74 Python tests / 25 subtests and all five Node suites pass.
- A bounded read-only smoke test made 30 requests at concurrency 3: zero errors,
  p50 396ms, p95 502ms. Reproduce with `tests/check_read_capacity.py`. It is not
  sustained capacity evidence and contains no paid-provider POST requests.

## Stage 4 — review materials prepared

Generated 20 private BN/EN fixed-audio drafts (Opus plus MP3) in
`voice-drafts/production-review`. `review.html` provides a local listening page;
no clips were marked reviewed or published. The two insurance clips could not be
generated because the verified insurance rule is missing. The generator's exit
status 1 reflects this incomplete bundle. The folder is excluded from GitHub.
Actual native review, insurance input and device acceptance remain required.

Local backups contain diagnostics while test capture is enabled. They are private
but not application-encrypted or copied off-host. Off-host encrypted recovery,
external notifications, representative capacity testing and financial/human/device
acceptance remain launch work. Never commit backup files or test recordings.

## Remaining work / production switch

1. Obtain intended-question labels and representative quiet/noisy BN/EN recordings;
   investigate remaining failures and measure p50/p95 separately for transcript,
   answer and speech. Optimize the measured slow service path without guessing intent.
2. Obtain native review and publish fixed offline audio; source-dependent insurance
   clips remain blocked by the missing verified rule.
3. Complete `seed/TO_CHECK.md` and physical Android/iOS/TalkBack/VoiceOver checks.
4. Choose an external alert destination and encrypted off-host backup destination;
   complete controlled capacity/outage testing and a public-traffic rollback drill.
5. After diagnostics are accepted: set `ILMA_ENV=production` and
   `VOICE_DIAGNOSTICS_ENABLED=false`, restart, verify no new samples are captured,
   and apply the agreed deletion policy to existing samples, exports and backups.
   Do not disable the authorized diagnostic test prematurely.

The 28 October speed update replaces the earlier one-worker configuration with
shared ilma MySQL admission and the versioned speed drop-in. Historical canary
checks above retain their original context. See [VOICE_SPEED.md](VOICE_SPEED.md).
