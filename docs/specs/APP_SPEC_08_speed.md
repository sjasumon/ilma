# Voice speed specification

This specification supersedes the timing and model-call policy in voice specs
02 and 07. It documents implemented behavior; device acceptance remains separate.

## Request stages and delivery

Each voice/typed request has a random request ID. Metadata-only `voice_timings`
log lines include upload_done, ffmpeg, asr, clean+match, intent, tools,
answer_text, tts_start, tts_done and sent, with stage and elapsed milliseconds.
Completed stages also appear in SSE progress events. Unused stages are marked
skipped in the final log. No transcript, question, recording or credential is
included in these timing logs. `sent` means answer text delivered, not playback.

The result event is delivered as soon as source-backed text is ready. It never
contains audio. A subsequent speech event contains same-origin audio_url and
ordered audio_urls. An agent waits for successful playback before opening the
microphone, or leaves readable options when speech is unavailable. Playback does
not wait for the SSE connection to close. MP3 responses bypass compression and
stream the provider's first chunks through the application and Cloudflare.

Opaque audio tickets expire after ten minutes. Source-backed, public speech is
cached separately for up to thirty days, bounded to 128 MiB. Cache keys include
voice, model, speed, language and pronounced text. Cache files/tickets are private
0600; no caller question or microphone recording enters this cache. A shared
file lock and partial stream deduplicate generation across workers. Failure
never publishes a partial file as a completed cached MP3.

## Routing and source use

Current option labels and spoken synonyms take the same path as tapping.
Known bank/status, product/rate, financial figures, history and insurance intents
use deterministic source-backed templates with no Spark request. Product-only
follow-ups retain the conversation's bank. Known unsupported banks return an
explicit coverage-unavailable message. Bengali vowel variants are folded only
for matching, preserving source spelling.

Other free-form questions use at most one Muse Spark PLAN request, temperature
zero, minimal reasoning effort, at most 1,000 total completion tokens and a
bounded 4.5-second request. The larger total includes hidden reasoning; the
original 300-token budget produced no JSON in a live probe. Invalid,
unavailable or ungrounded plans fall back to clarification/templates. There are
no serial model SAY/CHECK requests; local validation checks plan scope and facts.
Financial answers remain sourced templates. Partial generated financial wording
is not streamed to users. Metadata trace rows accurately label script/template/
code steps and real model calls.

## Speech and execution

Bank summary speech contains the status, one compact sourced reason and the next
question. Details speak up to two short reasons. The full card retains source
text, numbers, dates, qualifications and citations. Insurance is spoken only when
requested. Speech is split into short ordered segments; background warmup covers
both languages for nine demo banks, questions and fixed guided prompts. Warmup
is opt-in and never blocks application startup. Provider speed defaults to 1.1;
the user's slower playback preference remains available.

Keep the current Bangla-capable Eleven v3 model. The documented Flash 2.5 language
list does not include Bangla, so a model switch requires native quality review.
Use the official HTTP streaming endpoint and one shared async keep-alive client
per worker for external services. ffmpeg runs asynchronously. MySQL work runs in
a thread with a fresh task-owned session and the existing connection pool.

Production runs two workers with atomic MySQL admission counters/leases shared
in the **ilma** database. It requires a stable private VOICE_LOG_SALT and fails
closed if admission is unavailable. Existing per-client/global provider budgets
are retained. Static/page reads do not acquire a provider slot.

## Client and acceptance

Agent/guided recording allows eight seconds to begin speaking and fifteen seconds
total, with two silence re-asks. Playback and recording are cancelled on stale
turns/backgrounding/navigation. One reusable AudioContext and audio element are
unlocked during a user gesture; recording graphs are disconnected after use.

Targets from upload: text <=3 seconds for templates / <=6 for Spark; first speech
<=4 / <=8 seconds; spoken reply <=8 seconds at normal playback; concurrent page
loads <2 seconds. Measure five demo banks, each initial turn plus details. Record
cache state, input method, actual MP3 duration and whether first bytes or actual
browser playback were measured. Do not describe typed or synthetic voice checks
as real microphone, native accessibility or mobile-network acceptance.

See [measured results](../VOICE_SPEED.md) and [deployment](../../ops/RUNBOOK.md).

Muse Spark reasoning consumes the same output-token budget as visible JSON.
A live minimal-effort probe at 300 tokens spent 298 on reasoning and returned
no content. At 1,000 total tokens it completed valid JSON using 541 tokens
(476 reasoning, 65 visible). This measured exception to the original 300-token
proposal preserves usable intent output: [official Meta guidance](https://dev.meta.ai/docs/reasoning).

[APP_SPEC_10](APP_SPEC_10_answer_wording.md) supersedes the three-segment short
narration policy. The immediate-text, streamed-URL and bounded-provider policy
remains. Its complete explanations have measured durations above eight seconds;
that earlier playback target is not claimed as passed.
