# Natural speech and pronunciation

This contract supersedes the length and audio-processing rules in spec 10.
An ordinary reply keeps separate `speech` and `speech_tts` strings. The displayed
`text` equals `speech`; the source card retains exact figures and quotations.
Only normalized `speech_tts` goes to the configured TTS voice/model, using the resolved reply language rather than the previous UI language. The same
normalization builds the cache identity, so stale pronunciation is not reused.

First introductions use full bank names, status, connected reasons, conditional
protection once per bank, and a full question. Their budget is 45 displayed
words; the target is roughly 15–20 seconds (12–22 seconds in the acceptance
check). Later explanations may take about 25 seconds; the ordinary-answer
ceiling is 30 seconds. Actual generated audio must be measured; word count
alone does not establish duration or comprehension. Source qualifications,
expired ratings, negative capital and calculated figures remain explicit.
No financial values, thresholds or source allegations are rewritten.

Long source narration is paged at clause/word boundaries with a “Hear more”
question. Continuation re-retrieves the source facts and carries only IDs/page
indices, never client-supplied narration. Completed facts are tracked separately
from a partly spoken source. Repeat replays the current page; it does not restart
the document. The card keeps the whole source text.

TTS normalization converts Bangla and English digits into Bangla words in the
Bangla voice, with lakh/crore units, colloquial hundreds, years, and quarter/half
percentages. Negative capital rounds to tenths before pronunciation. Known bank,
product and rating acronyms have explicit pronunciations; unknown Latin strings
are spelled rather than silently dropped. English replaces percent symbols and
Tk, and pronounces AAA as “triple A.” The displayed figures remain unchanged.

The withdrawn ten-second silence gate and extra tempo adjustment are removed.
The configured voice/model/synthesis speed remain consistent across turns;
streamed MP3 bytes keep their original pacing. A versioned natural-speech cache
policy prevents reuse of the previous accelerated/filtered clips. Audio and
measurement artifacts remain private.

During agent playback, a themed Stop speaking control is visible. Stop, reply
taps, and detected speech invalidate pending playback, preventing late completion
from selecting an option or reopening the microphone. A reply tap during speech
interrupts before starting capture, even in guided mode. Voice interruption only
observes input when microphone permission is already granted and the browser
reports echo cancellation; it never opens a permission prompt during playback.
The in-memory level detector requires sustained speech above its calibrated
baseline, then hands the stream to the normal recorder. No monitoring recording
is stored or uploaded. Unsupported browsers retain tap/Stop interruption.

Deposit protection stays conditional and per person/per bank. Speech does not
promise unconditional repayment or turn the separate statutory list/payment
clocks into seventeen days from closure. Full terms remain on the source card.

Acceptance requires number/pronunciation fixtures, source/Repeat/continuation
checks, all bank introductions in both languages, actual duration measurement,
and real playback stopping within 300 ms. Synthetic monitoring checks establish
cleanup/handoff, not physical echo rejection. Two non-banking listeners must
still hear the Bangla introduction, details, FDR and negative-capital replies
without the screen and explain the condition, reason and protection limit.
Native comprehension, pronunciation and physical-device acceptance must not be
reported as passed by automated checks.


The reliability recheck also requires complete source-card coverage and validated
audio publication. A failed decode, zero duration or over-budget ordinary clip
must not become a reusable MP3. Invalid existing entries are repaired; shared
workers ignore artifacts from older synthesis attempts. Pending microphone
explanations suspend automatic reply timers, and calibration retains short
spoken replies. These changes preserve narration and natural pacing.

Uncertain single-bank matches require explicit confirmation rather than a
financial answer. The current bank is not replaced before acceptance; product
and term are retained. A negative reply clears the pending choice. Distinct
City Bank Bangladesh and Citibank N.A. names are not merged into one alias.
