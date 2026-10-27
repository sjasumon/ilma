# Voice pipeline audit — 2026-10-27

Scope: capture/stop/cancel, multipart upload, conversion, Meta ASR, transcript
cleanup, matching, intent, MySQL queries, SSE parsing, speech playback, diagnostic
capture and the actual systemd deployment. This is an implementation audit, not
a claim of measured speech accuracy or complete physical-device acceptance.

## Database correction (user clarification)

The user confirmed that **`ilma` is the ILMA database** and `project_db` belongs
 to other work. The earlier switch to `project_db` was incorrect and has been
reverted. The service override and default URL now select `ilma`. Created ILMA's
own schema there, preserving its existing diagnostics, and added authored glossary
entries only. No bank records or financial facts were imported from `project_db`.
The canonical database currently has no institutions; the pipeline now returns
an explicit data-not-loaded result after displaying the transcript.

Earlier replay evidence below describes the temporary configuration and must
not be interpreted as acceptance of data from `project_db`. That database is
no longer used by the service. Diagnostic copies previously placed there have
not been deleted as part of this correction.

## Findings fixed

| Finding | Result |
|---|---|
| Database selection was inferred from table names | User confirmed `ilma` is canonical. Reverted the temporary `project_db` selection and initialized ILMA tables in `ilma`, without importing unrelated records. |
| A transcript could wait on database/matching work | Transcript now streams immediately after cleanup, before querying the index; unexpected-script text remains visible on rejection. |
| Empty provider `choices` could raise an uncaught IndexError | Intent returns a controlled error; fact-grounded answer generation falls back to its database facts. |
| Unexpected backend exception could abruptly end SSE | Sanitized error event and transaction rollback; logs contain exception type only. Cancellation still propagates. |
| A truncated stream could look successful without an answer | Client requires a result event and reports incomplete responses while preserving the transcript. Reader is cancelled/released on exit. |
| CRLF SSE frames were not parsed | Handles fragmented CRLF and UTF-8 network chunks. |
| A disconnect during speech could obscure an already delivered answer | Completed answer remains visible; speech failure is announced separately. |
| Recorder could wait indefinitely for its stop event | Five-second finalization deadline, microphone cleanup, and cancellation settlement. |
| Native keyboard/assistive clicks during recording were ignored | Detail-zero activation stops and searches with one activation; ordinary touch keeps double-tap stop. Physical screen-reader validation remains required. |
| Health could say OK with only a release table | Health now checks bank schema, at least one institution, and voice tables. Provider availability remains a separate live-doctor check. |
| Some failures had no diagnostic stage information | Opt-in diagnostics now include conversion, audio duration, ASR, matching, intent, failure/cancellation stage and elapsed time. Audio/transcripts remain out of operational logs. |
| Daily quota and malformed-request errors used generic fallback copy | Explicit localized messages. |
| Speech generation shared an eight-second timeout despite longer report generation | A real 282-character report took 18.74s at ElevenLabs. Added a separate bounded `SPEECH_TIMEOUT_SECONDS` (default/max 25s); text still appears before audio. Failures log only status/type. |

## Evidence

- 48 Python tests and all five Node suites passed, including new empty-provider,
  cancellation, unexpected-exception, incomplete-database, truncated-stream,
  CRLF, late-disconnect and recorder-stop-timeout regressions.
- After correcting the service database, the public bank index returned HTTP
  200 with four existing institutions. A live typed EBL request streamed a
  transcript, match and report-card result.
- Replayed three saved human recordings privately through the host service:
  report card (5.55s), clarification (7.29s), and unexpected-script rejection
  (2.91s). All returned a transcript; none had a database error. These few
  recordings are insufficient to estimate accuracy. Their timings do not
  establish the required median result latency of four seconds.
- Existing diagnostic audio and raw transcripts were not printed or committed.
  Diagnostic capture remains enabled for the user's current test session.
- Final public health check reports `bank_data_ready=true` and
  `voice_tables_ready=true`. Live English and Bangla bank-name questions returned
  reports, an EBL FDR question returned a service answer, and an invented bank
  name returned clarification rather than selecting EBL.
- Real TTS probes: a short Bangla phrase generated audio in 1.63s; a report
  generated audio in 18.74s with a longer diagnostic deadline. The original
  eight-second speech cutoff was insufficient for that report.
- After deploying the separate speech deadline, a saved-recording replay
  completed transcript → match → report card → speech in 24.75s. This verifies
  actual generated speech data, not audible playback or native pronunciation.
  The 15-second spoken-answer target remains unmet by that sample.

## Remaining work

- Complete the verified bank dataset; current records do not cover all nine
  required demo banks. This audit did not revalidate bank financial provenance.
- Investigate Meta script/language errors using intended-question labels paired
  with recordings; do not weaken bank matching or invent translations to hide
  recognition failures. Preserve the specified language-bias settings.
- Run representative quiet/noisy speech tests and measure ASR accuracy, intent
  accuracy and end-to-end latency separately.
- Full-report TTS latency can exceed the 15-second spoken-answer target. The
  separate timeout avoids premature failure; streaming speech/shorter spoken
  summaries need further work before claiming that target is met.
- Validate permissions, quiet microphones, Bluetooth interruptions, screen-reader
  gestures and backgrounding on physical Android/iOS devices. Automated recorder
  tests do not substitute for those checks.
- Native-review/publish offline clips; verify the deployed retention timer.
- Disable diagnostic capture after the test session and clean up retained data.

## Host configuration

The host-specific drop-in is installed at
`/etc/systemd/system/ilma-app.service.d/database.conf`. For a new host, review
the database name before installing the template. Reload systemd and restart
the service after changing it. Run migrations/diagnostic commands in the same
host/database context as the service; an agent-context connection alone is not
proof that the service sees the same schema.

On this host, CLI setup/doctor/diagnostic commands should explicitly use
`DB_NAME=ilma` to match the service drop-in. The live doctor still fails
overall acceptance because ILMA bank records and reviewed offline clips are missing;
database connectivity, voice tables and both provider-access probes pass.
