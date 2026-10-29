# DPS comparison check — 29 October 2026

Scope: only the best-DPS question family. Speech-to-text, audio processing and provider settings were not changed. These six live checks used typed text through the complete local HTTP pipeline with the real `ilma` database and Meta model. TTS was disabled for these checks; this is a spoken-text report, not an audio listening acceptance.

## Database coverage

Eight banks have DPS rate records. Dates below are stored rate-sheet dates, not a claim that the sources were manually reverified today. The legacy DPS rate table has no additional records.

| Bank | Annual rate and tenure | Stored sheet date |
|---|---|---|
| Bank Asia | 8.50%: 36 months; 8.25%: 36 months | 2026-10-01 |
| BRAC | 7%: 12 months; 7.25%: 24; 7.50%: 36; 7.75%: 48; 8%: 60–108; 8.25%: 120 | 2026-10-15 |
| City | General DPS 7.25%: 36, 60, 84, 120 months; Insurance Backed DPS 8%: 60, 120, 180, 240 months | 2026-10-18 |
| EBL | 8%: Confidence 12–72 months, Women Confidence 12–60, Child Future 36–180 | 2026-09-15 |
| MTB | 8%: Junior Flexi 48 months; Millionaire: structured tenure unset, source text lists 48, 72, 96, 120 months | 2026-10-01 |
| NCC | 8.75%: 24–72 months; 8.50%: 24–60 months | 2026-10-01 |
| Prime | Kotipoti 9%: 60–180 months; Lakhopati 6%: 36, 60 months | 2026-09-24 |
| South Bangla / SBAC | 10%: 12 months only | 2026-09-01 |

MTB rates are stored as percentage text. Its source text says effective 1 September 2026, which conflicts with the stored 1 October document date. MTB has no verified structured five-year quote and is excluded from selection; this change does not alter source records.

## Code-owned selection and calculations

Only current, visible, conventional five-year offers from banks classified `strong` (ভালো অবস্থা) enter ranking. Highest qualifying rate per bank wins. Prime: 9%; NCC: 8.75%; BRAC: 8%. City and EBL also offer 8%; stable bank ID breaks the third-place tie, without implying BRAC is better. South Bangla is unverified (`no_data`), offers 10% only for one year, and is flagged separately; a five-year maturity is not fabricated.

Maturity illustration: ৳1,000 deposited at each month end for 60 months, monthly compounding, before tax and fees, zero upfront. Formula: `1000 × ((1 + annual_percent/1200)^60 − 1) / (annual_percent/1200)`, rounded to the nearest taka. Prime: ৳75,424; NCC: ৳74,931; BRAC: ৳73,477. These are code estimates, not bank maturity quotes or eligibility promises. NCC’s source has a ৳25,000 upfront example; that amount is explicitly excluded from this standardized illustration. The source example does not establish a minimum upfront requirement.

## Exact fact list sent to Meta

The model receives this list and the composition rules only; no user transcript, conversation memory, unrelated bank facts, source quotes or dates are sent. Dates and source links remain on the visible supporting cards.

- মাসশেষে ১০০০ জমিয়ে ৫ বছরে মাসিক চক্রবৃদ্ধিতে কর-ফি কাটার আগে আনুমানিক হিসাব।
- ভালো অবস্থার প্রাইম: 9%, আনুমানিক 75424 টাকা।
- ভালো অবস্থার এনসিসি: 8.75%, আনুমানিক 74931 টাকা।
- ভালো অবস্থার ব্র্যাক: 8%, আনুমানিক 73477 টাকা।
- এনসিসি-এর উৎসের উদাহরণে আগাম 25000 টাকা আছে; এই হিসাবে তা বাদ।
- সাউথবাংলা: 10%, 1 বছর; অবস্থা অযাচাইকৃত।৫ বছরের তথ্য নেই।
- আপনি মাসে কত টাকা রাখতে চান?

## Six live results

Every request returned HTTP 200, `compare`, and ready comparison data. All used the same fact list above and the identical final answer below. Meta exceeded the limit in every check; each was replaced by the fixed template. Reported time is request-to-complete-response on the local HTTP server, including database access and the real Meta call, excluding TTS, recording, transcription and public-network latency.

| Question | Seconds | Final answer source |
|---|---:|---|
| কোন ব্যাংকের ডিপিএস সবথেকে ভালো | 3.442 | Fixed template: model word limit |
| ডিপিএস কোথায় ভালো | 4.204 | Fixed template: model word limit |
| best DPS কোন ব্যাংকে | 4.212 | Fixed template: model word limit |
| কোন ব্যাংকের ডিপিএস সবচেয়ে ভালো? | 3.502 | Fixed template: model word limit |
| ডিপিএসের সর্বোচ্চ সুদ কোন ব্যাংকে? | 3.251 | Fixed template: model word limit |
| কোন ব্যাংকে ডিপিএসের সুদ সবচেয়ে বেশি? | 2.474 | Fixed template: model word limit |


Final spoken text for all six questions (59 whitespace-separated words after number pronunciation):

> মাসশেষে এক হাজার পাঁচ বছরে মাসিক চক্রবৃদ্ধিতে কর-ফি কাটার আগে আনুমানিক: ভালো অবস্থার প্রাইম নয় শতাংশ, পঁচাত্তর হাজার চারশো চব্বিশ এনসিসি পৌনে নয় শতাংশ, চুয়াত্তর হাজার নয়শো একত্রিশ ব্র্যাক আট শতাংশ, তিয়াত্তর হাজার চারশো সাতাত্তর টাকা। এনসিসির উদাহরণের আগাম পঁচিশ হাজার ধরা হয়নি। সাউথবাংলার দশ শতাংশ এক বছরের, পাঁচ বছরের তথ্য নেই, অযাচাইকৃত। আপনি মাসে কত টাকা রাখতে চান?

## Guardrails and acceptance

Code checks literal quantities against the exact sent list, bank names against the allowed names, rates and maturity amounts against their own bank, required warning/tenor and upfront caveat, calculation assumptions, exact closing question and fewer than 60 pronounced words. Invented numbers/names, swapped values, omitted caveats, model failures and overlong replies use the fixed template. Model quantities must use digits before the existing pronunciation layer renders speech. If fewer than three banks have rate data, or fewer than three qualifying five-year strong-bank offers remain, processing stops before Meta and reports insufficient data.

This narrow check does not certify the entire app, microphone/device operation, current source accuracy, or new TTS synthesis. No broad corpus run was resumed.

Regression validation: 457 Python tests and 27 subtests passed, including 24 focused DPS tests. All seven documented frontend suites passed. Repository policy, full-history redacted secrets scan and staged redacted secrets scan passed before publication.
