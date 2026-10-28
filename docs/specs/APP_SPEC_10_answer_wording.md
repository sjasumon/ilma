# Connected answer wording

This specification replaces the field-fragment speech policy in APP_SPEC_08.
The private incoming review is retained outside the published tree.

## Paragraph and exact card

Agent results carry `speech` as one source-backed paragraph, `speech_format` as
`paragraph`, and `text` with exactly the same words. `speech` is narration text,
not embedded audio. The text result is still sent immediately before synthesis.
A separate speech event has one same-origin MP3 URL. TTS reads the entire
paragraph in one clip, cached by the complete pronounced text and voice settings.
No caller question or recording is stored in the public-source speech cache.

The chat bubble displays the paragraph. The expandable card below retains the
original `sentences`, `fact_ids`, exact figures, qualifications and sources. The
question appears in the paragraph, with short option buttons and a separate tap
to reply control. Focus does not scroll the new answer out of view. The automatic
screen-reader announcement does not append the question a second time.

## Wording and progression

Bank introductions answer first, connect a reason with “কারণ” / “because”, explain
a figure's meaning and comparison, add qualified deposit-protection information
once per bank, and end with a full polite question. Missing data and unsupported
banks remain explicit. No answer guarantees safety or recommends a bank.

Conversation `spoken_fact_ids` records facts selected for the spoken/chat
paragraph; it does not prove that a device successfully played them. DETAIL and
FIGURES select facts not already explained, so a normal bank → details → figures
→ history → FDR sequence progresses instead of repeating ratios. Explicit Repeat,
language undo, direct questions about a specific figure and explicit insurance
questions can repeat the requested information. The client still opens its mic
only after successful playback. A failed or interrupted clip can be replayed.
`insurance_bank_ids` prevents automatic repetition on ordinary follow-ups. No
server conversation storage is added.

Spoken percentages and profits use deterministic rounding with an approximation
label. A small nonzero ratio is not rounded to zero. Exact card values remain
unchanged. Years are ordinary phrases, and bank legal suffixes are omitted.
Capital compares against the configured base plus buffer, not a hardcoded legal
minimum. Calculated figures retain that qualification. A problem-loan ratio means
repayment difficulty, not a guarantee that all that money will be lost. Expired
ratings, uncertain outlooks, unconfirmed allegations, latest incident status and
incomplete history retain their qualifications.

FDR/service speech discusses the selected product, term, rate or fee and schedule
date, without mixing bank-health labels into the answer. It never invents an
effective-from date from a document's publication date. Conventional one-year
FDRs may use a fixed, conditional simple-interest illustration before tax; it
does not claim the example amount qualifies for a particular published slab.
No personal amount is requested. Islamic provisional rates remain provisional,
stale information remains labelled old, and comparisons retain the existing
same-term/basis/condition cohort.

Insurance wording keeps eligible deposits, member-bank scope, combined accounts
and exclusions. A payment deadline is not presented as an unconditional promise
from the day a bank closes: the sourced list and information-receipt stages are
retained. See the [official Act, sections 2 and 21–23](https://bdlaws.minlaw.gov.bd/act-print-1703.html).
Plain capital and repayment explanations follow the concepts described by the
[Federal Reserve](https://www.federalreserve.gov/faqs/cat_21427.htm) and
[ECB Banking Supervision](https://www.bankingsupervision.europa.eu/about/banking-supervision-explained/html/provisions_and_nplcoverage.en.html).
These references explain terminology, not acceptance of imported bank figures.

## Execution and acceptance

Templates supply wording. Muse Spark can still plan a free question, with the
existing one-call/timeout/token budget; no extra model wording/check calls run.
First paragraphs for all eleven covered banks, both languages, and complete
questions are pre-generated in the private cache. Full exact bank names outrank
shorter exact or fuzzy fragments inside them. Separately named banks remain
separate matches.

The incoming examples are substantially longer than eight seconds at a clear
pace. Keep actual duration and first-byte/playback measurements separate. Do not
truncate conditions, accelerate speech beyond the supported range, or label an
eight-second target passed without measurement. The measured complete first
answer is about thirty seconds; see the acceptance record. A shorter opening
requires moving some content to follow-ups. Native listening/comprehension review
is distinct from synthetic source checks and actual browser playback timing.

## Other spoken entry points

The older bank question route uses the same connected summaries and keeps its
exact `card_text` separate. Explicit full-report playback still reads that full
card. Service-tab answers use product sentences; unverified bank-condition
notices remain visible separately. Comparison readout returns one cached audio
URL and full paragraph text instead of embedded audio or bare field labels.
Published fees are read directly, without substituting a calculated waiver.
