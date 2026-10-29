# Voice speed checks — 28 October 2026

Implemented policy: [APP_SPEC_08](specs/APP_SPEC_08_speed.md). These are bounded
checks from the server's network through the live Cloudflare host, not a
production latency SLA or real phone/ASR acceptance.

## Before / after: ten fixed typed turns

Five banks, each name followed by “আরও বিস্তারিত”, Bangla, speech enabled.
Time starts before POST /v1/ask. Text means the result SSE event was received;
audio means the first MP3 response bytes, not audible phone playback. Speech
length is the sum of decoded MP3 segment durations at normal speed. Baseline
audio was embedded base64 in the delayed result. Final runs used warm persistent
speech cache; all final audio responses reported cache hits. No recordings or
raw provider payloads are published.

| Bank / turn | Before text (s) | After text (s) | After first audio bytes (s) | Before speech (s) | After speech (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| bracbank / first | 17.064 | 0.196 | 0.277 | 19.043 | 6.427 |
| bracbank / detail | 12.329 | 0.083 | 0.165 | 27.221 | 5.957 |
| primebank / first | 13.171 | 0.125 | 0.199 | 18.809 | 6.035 |
| primebank / detail | 12.299 | 0.092 | 0.173 | 28.814 | 5.957 |
| ebl / first | 18.650 | 0.090 | 0.169 | 19.541 | 6.114 |
| ebl / detail | 14.993 | 0.081 | 0.148 | 27.299 | 5.957 |
| mtb / first | 15.803 | 0.103 | 0.185 | 19.043 | 6.114 |
| mtb / detail | 10.327 | 0.087 | 0.157 | 27.612 | 5.957 |
| bankasia / first | 15.485 | 0.084 | 0.151 | 19.043 | 6.114 |
| bankasia / detail | 10.933 | 0.083 | 0.147 | 28.422 | 5.957 |

The final text range is 0.081–0.196 seconds, first MP3 bytes 0.147–0.277 seconds,
and speech 5.957–6.427 seconds. Concurrent page GETs peaked at 0.074 seconds,
with no failed responses, compared with baseline maximum 0.172 seconds. The
reported historical server freeze was not reproduced by this bounded check.

## Intermediate measurements

These two-turn BRAC samples measure different cache states and provider calls;
they are diagnostic snapshots, not statistically controlled comparisons.

| Step | First/detail text (s) | First/detail first audio bytes (s) | Speech first/detail (s) |
| --- | --- | --- | --- |
| Result first, streamed audio | 16.762 / 0.067 | 18.279 / 0.960 | 18.442 / 28.604 |
| Simple templates, no serial SAY/CHECK | 0.189 / 0.069 | 1.149 / 0.117 | 20.767 / 28.604 |
| Initial short segments | 0.134 / 0.068 | 0.899 / 0.112 | 9.875 / 5.826 |
| Final, two workers + warm cache | 0.196 / 0.083 | 0.277 / 0.165 | 6.427 / 5.957 |

The short-speech trial exposed a duration overrun. Compact sourced reasons and
a clearer Bangla BRAC bank name brought the final summary under eight seconds.
Full screen facts, numbers, dates and citations are retained. Insurance remains
qualified and is narrated only when asked; extended readouts and slower playback
are outside this short summary measurement.

## Full pipeline: synthetic audio, not human recordings

A separate paced ten-turn run uploaded TTS-generated public bank names and a
details phrase through /v1/voice → async ffmpeg → Meta ASR → routing → audio.
It retains failures in the results; no synthetic audio file is published.

| Bank / turn | Transcript (s) | Answer text (s) | First audio bytes (s) | Routing |
| --- | ---: | ---: | ---: | --- |
| bracbank / first | 2.361 | 2.400 | 2.432 | Asked bank; no bank assigned |
| bracbank / detail | 2.257 | 4.489 | 4.587 | Asked bank; no bank assigned |
| primebank / first | 1.539 | 1.640 | 1.675 | bank_summary |
| primebank / detail | 2.225 | 2.254 | 2.291 | bank_reasons |
| ebl / first | 1.643 | 1.699 | 1.732 | bank_summary |
| ebl / detail | 2.426 | 2.472 | 2.568 | bank_reasons |
| mtb / first | 2.267 | 2.334 | 2.419 | bank_summary |
| mtb / detail | 2.345 | 2.392 | 2.432 | bank_reasons |
| bankasia / first | 1.972 | 2.026 | 2.056 | bank_summary |
| bankasia / detail | 1.544 | 1.552 | 1.583 | bank_reasons |

Eight turns resolved the expected bank/tool and returned text within 1.552–2.472
seconds; first audio bytes arrived within 1.583–2.568 seconds. Meta transcribed
the synthetic BRAC name as “breakbank”; both BRAC turns stayed in ASK_BANK
instead of silently selecting a bank. These are recognition/clarification cases,
not successful bank answers. The follow-up without a bank used a bounded Spark
request and returned clarification at 4.489 seconds. No claim of perfect ASR is
made. Transcript latency ranged 1.539–2.426 seconds, so the two-second transcript
target was not consistently met. Concurrent page GET maximum was 0.108 seconds,
with no errors. “আরো বিস্তারিত” correctly bypassed Spark when a bank existed.

Provider/device recognition and tail latency remain acceptance work; speed
optimizations must not turn an unknown transcription into a guessed bank.

## Planner budget correction

The proposed 300-token intent budget was insufficient for the current Muse
reasoning model. A live minimal-effort probe returned finish_reason=length,
zero content characters and 298 reasoning tokens out of 300 total. A 1,000-total-
token probe returned valid plan JSON using 541 tokens (476 internal reasoning,
65 visible). The planner now uses minimal reasoning, a 1,000-total-token ceiling,
one call and a strict 4.5-second wall-clock deadline, with sourced fallback.
The deployed Bangla free-question probe completed in 3.162 seconds with one
successful 2.925-second PLAN call and template wording. This is a measured
deviation from the original small total-budget proposal,
not a claim that generated financial wording is required.
[Meta explains the combined budget](https://dev.meta.ai/docs/reasoning).

## Browser and execution checks

Actual Chromium MP3 playback, fixed typed BRAC question, 390×844 viewport:
text appeared at 158 ms; first playback began at 235 ms; the third segment ended
at 6,982 ms; the synthetic recorder started at 6,984 ms. Real audio playback was
used, with a synthetic recorder to avoid capturing a microphone. This verifies
the client waits for all segments, not SSE closure. It is not iPhone acceptance.

Synthetic regression tests cover delivery before synthesis finishes, first-chunk
streaming, single- and two-worker generation deduplication, expiry, private file
permissions, compression bypass, nonblocking database work with task-owned
sessions, shared-admission failure, and simple intents avoiding Spark. Independent
limiter instances on the actual **ilma** database enforced a shared client lease
and release. Two workers run under the application service; budgets are retained.

A request sent immediately during a service restart received a transient 502;
after startup, root, docs, redoc, OpenAPI and the new audio asset all returned
200 with live Cloudflare security headers verified. This deployment is not a
zero-downtime rolling upgrade.

Live frame checks passed all tabs in BN/EN, portrait/rotation, keyboard-sized
viewport, desktop and 200% text. Guided and agent browser integration use synthetic
media/provider responses and passed the separate result/speech event protocol.

## Repeat and remaining acceptance

Opt-in check (uses paid speech on cache misses; respect provider budgets):

```sh
python tests/check_voice_speed.py --base-url https://app.sumon.me
```

It uses only fixed public bank names and writes metadata to /tmp by default.
Run cold and warm tests separately, record actual cache headers and distinguish
first response bytes from audible playback. Never clear rate counters to run a
benchmark. Repeated checks correctly triggered HTTP 429; a paced run respects
the existing shared budget.

Real Android/iOS microphone, VoiceOver/TalkBack, native pronunciation, slow/mobile
networks, representative concurrent load/outages and p50/p95 remain pending.
Do not infer financial source acceptance or unrestricted production readiness
from these speed checks. Public source/manual review requirements are unchanged.

The current Bangla-capable model is retained: Eleven v3 supports Bangla, while
Flash 2.5's documented language list excludes it. Model substitution needs native
review. References: [models](https://elevenlabs.io/docs/overview/models),
[HTTP streaming](https://elevenlabs.io/docs/api-reference/text-to-speech/stream),
[speech speed](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/can-i-change-the-pace-of-the-voice).

Final documented suites: 207 Python tests plus 25 subtests, all seven frontend
Node suites, repository policy and redacted full-history secrets checks.

The BRAC “breakbank” recognition failure recorded above predates the subsequent
user-approved alias update. “breakbank” and “ব্রেক ব্যাংক” now match BRAC exactly
in the database index. This improves routing for those transcripts; it is not
a claim of improved upstream ASR accuracy. See [voice acceptance](VOICE_ACCEPTANCE.md).

The later [connected-wording update](specs/APP_SPEC_10_answer_wording.md) replaces
these short three-segment answers with one complete paragraph/clip. The six-second
figures above are historical and do not describe the new paragraph duration.
See VOICE_ACCEPTANCE.md for the longer measured playback and remaining target.

The 29 October short-answer update supersedes the 11–33-second paragraph timings.
Ordinary answers now have a 30-word budget and a measured ten-second gate. The
synthesis setting remains 1.1; short speech also trims long digital pauses and
uses a 3% pitch-preserving pace adjustment. Full-report readouts and user-selected
Slow playback are separate. Current evidence is in `VOICE_ACCEPTANCE.md`.


## Natural-speech update — 29 October 2026

The ten-second target and extra silence/tempo processing above are superseded
by [the natural speech contract](specs/APP_SPEC_11_speech_wording_and_pronunciation.md).
Replies now use full bank names, fuller sentences and a separate pronunciation
string. Two-person listening/comprehension and physical echo-rejection checks
remain pending; automated duration checks do not establish those outcomes.
