# Short connected answer wording

The 29 October update supersedes the earlier long-paragraph policy. The incoming
review remains private; this document describes the implemented contract.

## Ordinary answers and cards

An ordinary agent result has `speech_format: paragraph`, one `speech` paragraph,
and identical `text`. The text is delivered before audio generation. Speech is
at most 30 words, counting both written and pronounced Bangla forms, with at most
two statements plus the next question. Introductions give one reason. Follow-ups
normally explain one new fact. Questions remain complete and include the relevant
choices; option buttons remain short. Voice and typed options keep the current
language and bank context under the existing recovery rules.

The expandable card keeps exact figures and source quotations. Capital captions
show the exact ratio and the configured base minimum plus buffer. FDR captions
omit the legal bank suffix and health-status fragment. Published dates remain
schedule dates, not inferred effective dates. A fixed, conditional one-lakh FDR
calculation before tax stays on the card, avoiding a long numerical readout.
No personal amount is requested. Service comparison speech states sourced quotes;
it does not rank banks or compare incompatible product attributes.

Speech uses established short bank brands rather than ASR mishearings. Positive
ratios/profits are rounded with approximation wording. Negative capital ratios
retain a decimal place, so -5.48% becomes about -5.5%, not -5%. Small nonzero values
do not become zero. Negative figures are available on the card and when asked;
the short risk introduction explains the capital shortfall. Expired ratings,
calculated figures, uncertainty and the latest incident status remain qualified.
Long incident titles use their sourced category, with the full headline on the
card. A brief history answer does not recite the completeness disclaimer.

`spoken_fact_ids` tracks explained source IDs. `last_spoken_fact_ids` retains the
selection for Repeat, which re-retrieves source records rather than accepting
client-provided narration. Source actions preserve the last substantive answer.
An explicit full-report readout remains a full readout, outside this short-answer
budget; its exact card text is not replaced by the short introduction.

## Deposit protection

Strong-bank introductions leave protection details on the card. High-risk
introductions retain a short conditional protection clause, once per bank.
Explicit protection questions state the per-person/member-bank combined-account
limit and leave full eligibility and payment steps on the card. Speech does not
promise every depositor repayment after any closure or a flat deadline from
closure. The law defines eligibility/exclusions and separate list/payment clocks;
see [the official Act, sections 2 and 21–23](https://bdlaws.minlaw.gov.bd/act-print-1703.html).
No bank status, financial fact, rule threshold or protection limit is changed.

## Audio and cache

Each ordinary answer uses one same-origin MP3. Synthesis uses the configured 1.1
voice setting. Short-answer processing removes long near-digital pauses using a
conservative -60 dB peak threshold, keeps short sentence breaks, and applies a
3% pitch-preserving pace adjustment. The filter targets near-digital silence. Quiet-signal and pitch tests check
retention; human listening remains separate. Processing
uses streaming pipes, including on cold synthesis; it does not buffer the entire
provider response before releasing audio. The filter behavior is described in
[FFmpeg’s reference](https://ffmpeg.org/ffmpeg-filters.html#silenceremove).

Short speech has a separate versioned cache identity including text, language,
voice, model, synthesis speed and processing policy. Identical existing public
speech can be reused rather than billed again. Opaque tickets keep their existing
ten-minute expiry; private cache retention and size bounds are unchanged. User
recordings/questions are not added to this public-source cache.

Warmup prepares whole first answers for eleven banks in both languages, full
questions and guided prompts. The duration check fails above 10,000 ms and on a
word/sentence overrun. `check_short_answer_audio.py` measures actual cached MP3s,
not a word-based time estimate. A later voice/model/source change requires
remeasurement; Slow playback can intentionally exceed the normal-speed budget.
Native listening/comprehension and physical accessibility acceptance are separate
from automated duration, pitch and retained-speech checks.
