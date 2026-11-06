# Contextual voice replies

The token protocol is implemented on the voice feature branch and tested on an
isolated preview. Production still uses the earlier contextual engine. The new
release has not passed all acceptance gates and is not ready for production.

## Implemented preview behavior

Code resolves bank names, spaced acronyms, product, term, comparison and correction
slots before asking Muse Spark. A clear new bank replaces the current one;
otherwise the current bank is retained. Corrections preserve unaffected slots.
An exact displayed option uses its action without a model call. A bank-specific
request without a bank asks which bank, rather than inventing a default.

All service facts and comparison rows are prepared before the wording request.
Spark selects finite, bank-bound fact-token clauses through a streamed schema.
Code fills their sourced values and verifies declarations and bank/row binding.
The model cannot write financial values, compute a condition or invent a rank.
Bad later sentences are repaired locally or dropped. Invalid headers or first
sentences permit one repair request inside the original shared model deadline;
there is no second fact-fetching pass. Exact repeat replays the checked reply.

Introductions explain the meaning of capital and problem-loan indicators. Exact
figures and sources remain on cards. Material differences use configured
thresholds and comparable, verified financial bases. A material capital or
problem-loan weakness takes priority over optional positive details. This is
information, not a bank recommendation or a safety guarantee.

Deposit protection is available only for direct questions. It is excluded from
other token registries, fallbacks, prewarming and the fixed clip catalog. Incident
speech uses a neutral category and event year, with an unconfirmed-news caveat
when appropriate. Full headlines remain on source cards.

MySQL conversation memory uses signed opaque identifiers and a 24-hour expiry.
Saved turns keep resolved slots and checked replies; arbitrary user words are
replaced with a redaction marker. Resolved context and checked partial replies
are saved before completion, allowing interruption and repeat without restoring
an earlier bank. Raw user text never becomes TTS input.

The preview streams checked text to the screen. A sentence-based word budget
keeps replies within 45 pronounced words and offers continuation on “yes”. Cards
localize labels and dates; every completed answer has two allowed next steps.

Offline introductions are stored in `ilma.app_voice_variant`. Their fingerprint
covers the prompt, source revision and code-owned wording. Reuse validates the
tokens again and rotates variants. Changed facts invalidate the cache; offline
composition must then be rerun. The compiler makes explicit opt-in Spark calls
and no TTS calls. Only one bank has been trialled so far, not the full bundle.

Acknowledgements are cached-only, skip taps and cached introductions, and avoid
consecutive repeats. Missing acknowledgement audio causes no synthesis on the
waiting user's path. The answer player polls opaque ticket status before its
single MP3 request. Identical synthesis shares a job, provider text rejections
have a short negative cache, duplicate speech events are ignored, and the
microphone waits 300 ms after completed playback before reopening.

## Validation and remaining gates

The authored corpus contains 404 cases, including 30 comparisons and 30
corrections. Complete live preview runs passed the Phase 1 gate; the acceptance
record includes both runs and their failures, rather than only the best score.
Recorded finite-token responses replay against synthetic meanings in CI without
paid calls or copied source exports. Old and new engine tests explicitly isolate
their environment flags and do not load the private environment file.

The 45-word budget does not prove the 30-second speech requirement. Measured
duration and graceful continuation of unusually slow audio still require work.
The full offline audio bundle, all-intent variation and first-audio/variety
targets remain incomplete. Phase 2 needs two consecutive passing nightly runs.

Phase 3 security, dashboard, external alerts, signed mutation identity, release
branch integration and rollback rehearsal remain pending. Existing production
API documentation is still public. Physical Android/iPhone testing, diverse
consented recordings, TalkBack/VoiceOver, native clip review, two-person listening
and source approval are separate human gates. See `docs/VOICE_ACCEPTANCE.md` for
measured evidence.
