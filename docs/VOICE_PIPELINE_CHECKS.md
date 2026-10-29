# Voice pipeline checks — 29 October 2026

This review covers capture, upload/conversion, real transcription, bank/intent
routing, sourced database answers, speech delivery and conversation recovery.
Generated input, mocked providers and physical-device acceptance are distinguished
below. No recordings, provider bodies, private configuration or raw exports are
published with these checks.

## Corrections

- Bank matching now rejects partial matches against words of substantially
  different lengths. “insurance” was incorrectly giving a weak match for BRAC;
  longer deposit-insurance questions now use the current bank. Approved aliases,
  nearby spellings and explicitly named multiple banks retain their checks.
- Repeat retains the previous answer’s selected fact IDs, including a specific
  profit/ratio answer and replies where all figures were already explained.
  It retrieves source records again rather than trusting client-supplied speech.
  Source-sheet actions preserve the last substantive answer. A status-rule source
  can open its rule inputs without pretending it has a PDF URL. Opening proof
  does not request speech or reopen the microphone over the sheet.
- A connection error or a clean SSE end after the answer but before promised
  speech moves the panel out of audio-wait. The answer and bank remain available;
  incomplete speech cannot silently count as successful playback.
- Two capture/no-speech failures reveal inline typing. Permission/provider/hard
  errors reveal it immediately. Automatic re-prompts stop while typing recovery
  is offered; a successful typed reply restores the normal flow and retains bank
  context. An unrecognized typed correction keeps the form available rather
  than returning to microphone capture. Silence retries remain bounded.
- The real planner initially chose an option but copied unrelated tenor/card
  defaults into its arguments, causing local validation to reject it. Tool
  purposes and allowed arguments are now explicit, with unused arguments null.
  A script option resolves its arguments through trusted code, while unmatched
  bank IDs, invalid direct-tool arguments and non-explicit watch consent remain
  rejected. Financial performance is distinguished from incident history.

The new `last_spoken_fact_ids` is ephemeral conversation metadata, not proof that
a listener heard a clip and not a stored transcript. No financial data, risk
thresholds, insurance terms or database schema changed.

## Executed evidence

The baseline passed 271 Python tests and 27 subtests. After these corrections,
281 Python tests plus 27 subtests and all seven frontend suites passed. Thirty-two
read-only source-backed paragraph checks passed across eleven bank introductions
in both languages and a complete follow-up sequence in both languages. Additional
browser checks passed exact repeat, source-sheet/microphone isolation, typing
recovery, language undo, named products, BRAC aliases, every-tab navigation,
portrait/rotation, keyboard-sized viewport, desktop and 200% text.

Readiness probes confirmed MySQL access, voice tables, all required demo banks,
Meta authentication, configured voice access, ffmpeg and RapidFuzz. Readiness
still exits nonzero because reviewed offline clips are not published; it is not
a database or provider-authentication failure.

Four private, generated spoken inputs were uploaded through the live HTTP
pipeline with real Meta transcription and real response speech. Bank name, FDR
follow-up and details follow-up in Bangla returned the intended tool, retained
bank and one complete audio clip. Result latency was approximately 2.3–3.2 seconds
from upload start. The English City sample was transcribed as “Citibank” and
received clarification, not an incorrect automatic City selection. The distinct
bank name was not silently added as a City alias. This tiny generated set is not
an ASR accuracy benchmark.

An initial Chromium fake-microphone run needed another turn; a subsequent run
recognized the bank on its first turn and played one complete clip before
reopening the microphone. Playback began about 6.1 seconds after the original
tap and ended at 37.4 seconds, including capture/upload/transcription and a
31.2-second answer. This exercised actual MediaRecorder compression and upload,
not a replacement recorder class. The input was generated WAV speech, not a real
person or physical microphone. Recognition variability remains an acceptance risk.

The same free-form performance question that previously ended in clarification
was rechecked against the real Spark provider after correction: one PLAN call
selected bank reasons, ACT retrieved the database facts, and local templates
produced the answer. The measured planner call took about 3.2 seconds. There are
no extra SAY/CHECK model calls; provider and semantic validation failures still
require clarification rather than invented facts.

## Remaining acceptance

Complete paragraph audio still takes about 11–33 seconds; the eight-second goal
is not met. Independent comprehension/native pronunciation, representative human
and noisy-room ASR, physical Android/iOS, TalkBack/VoiceOver, reviewed offline
clips and financial-source acceptance remain separate launch gates. These checks
do not establish blanket production readiness.

## Repeatable checks

Use a provider-disabled local preview for `check_answer_wording.py`,
`check_pipeline_recovery_browser.py`, `check_conversation_browser.py`,
`check_voice_agent_browser.py`, `check_brac_reply_browser.py` and
`check_app_frame.py`. Run them sequentially so admission budgets are not consumed
by competing automated probes. Rejection under parallel probe load is not speech
recognition evidence. See the operations runbook for private preview settings.

`check_voice_roundtrip_browser.py` is an explicit live-provider check. Supply
`--audio-file /PRIVATE/generated-bank-prompt.wav`, `--bank-slug primebank`,
`--language bn` and a provider-enabled `--base-url`. The generated WAV should have
a short quiet lead-in and a quiet tail so automatic silence completion can run.
The check prints stage metadata, not transcript text or recordings, and stops
capture when finished. It can incur transcription and speech costs. Existing
private diagnostic capture/retention settings still apply on the target server.

## Deployed recheck

After deployment, live browser checks passed exact repeat, source-sheet isolation
and typing recovery. The repeatable real-recording check captured a 21,350-byte
WebM/Opus Blob, made one upload, received the bank result at about 6.1 seconds
from tap, and played one clip from about 6.2 to 37.4 seconds before reopening the
mic. The real ASR stage took about 2.6 seconds in that run. Cloudflare page/API-doc
headers and responsive navigation were rechecked; the free-form planner question
was also tested through the deployed HTTP route. These are individual probe
measurements with generated input, not population latency or human-accuracy claims.

## Short wording update — 29 October 2026

The later short-answer specification supersedes the long-audio limitation above.
The 36-answer real-audio gate now passes at 4.608–9.888 seconds, with the synthesis
setting at 1.1 plus the documented short-speech processing. Exact values, statutory
conditions and schedule dates remain on the card. Native listening and physical
accessibility acceptance remain open. See `specs/APP_SPEC_10_answer_wording.md`.
