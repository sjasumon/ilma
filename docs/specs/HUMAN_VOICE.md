# Contextual, sourced voice replies

The optional contextual engine combines understanding and wording in one Muse
Spark request. It receives the current bank's sourced facts and four redacted
conversation turns. An exact displayed option or button uses its database action
directly. A new bank, product or comparison can require a second fact-fetching
request. A factual checker can request one repair before a sourced fallback.

The model cannot set financial figures or bank conditions. Displayed replies keep
digits; pronunciation normalization produces speech text. Sentence citations
connect the reply and visible source cards. Checks cover numbers, percentages,
bank/rate binding, dates, ratings, computed conditions, repeated facts, advice,
conditional protection, source age and length. These checks reduce risk; they
cannot prove the semantic correctness of arbitrary paraphrases.

Conversation memory is stored in `ilma.app_conversation`, expires after 24 hours,
and uses signed opaque tokens. Personal amounts and identifiers are removed from
saved user words and model input. Repeat uses the exact previous reply and facts.
Switching banks clears service slots; deposit questions clear card filters.
Provider failures do not count as user misunderstandings. A genuine unclear
model result increments misses and offers typing after two misses.

Service terms support continuous ranges and discrete choices. Comparisons retain
their source conditions, match basis and term, and explicitly mark nearest-term
alternatives. Missing terms are not silently treated as a one-year request.
Comparisons without a specified term disclose the anchor term used.

Profile facts require a source URL, page and quotation. The curated profile file
currently contains 21 facts for six banks from their 2025 annual reports. It is
a source import, not a completed manual review. Missing fields stay absent;
profiles for the remaining five banks and full profile coverage remain pending.
Peer comparisons use computed conditions, comparable periods and cited inputs.
They include available capital, problem-loan, profit, profit-change, rating and
one-year deposit-rate comparisons. Incident counts describe the sourced
collection, not every event that occurred. No peer ranking is a recommendation.

## Activation and acceptance

`HUMAN_VOICE_ENABLED=false` is the default until preview acceptance passes. Run
the additive migration and profile import before enabling a preview. Operational
commands are in the runbook. Production requires a stable private log salt and
disabled diagnostic recording.

Local regression tests are separate from live model acceptance. During this
implementation, live Spark returned HTTP 402. Consequently the real-model
paraphrase accuracy, answer variation, three spoken dialogs, 95th-percentile
speaking latency and two-person listening acceptance have **not passed**.
Successful fallback replies must not be reported as successful Spark replies.
Production activation remains pending those checks and source/profile review.

`tests/human_voice_cases.json` contains 285 handwritten paraphrases, ten Bangla
and five English phrasings per intent. The opt-in evaluator
`ops/evaluate_human_voice.py --live` runs against an isolated local preview only.
It stops on provider access failure and does not count template fallback guesses
as model-understanding passes. It does not test speech latency or listening.

The intended listening acceptance is practical: two people unfamiliar with
banking should understand the bank's condition, its reasons and the history
without looking at the screen. Test Bangla pronunciation, interruptions, noisy
rooms, screen-reader navigation and older phones separately.
