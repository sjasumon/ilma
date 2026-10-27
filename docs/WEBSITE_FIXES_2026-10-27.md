# Website review fixes — 27 October 2026

The private review is retained on the share. This record distinguishes deployed
fixes, reproducible checks and missing inputs. Current shell asset version: 32.

| Review item | Result |
| --- | --- |
| 1. High-risk example | **Resolved with approved v6.2 input.** Sumon supplied the replacement archive. National Bank and Islami Bank have sourced High cards under unchanged thresholds. The original nine-bank statuses and service scope remain unchanged. See [supplement review](../seed/incidents/README.md) for exclusions, legal-label corrections and source limitations. |
| 2. Insurance | Added the official bank rule with its legal source, qualified account aggregation and payment stages. Imported into `ilma`; the report and voice answer link the source. |
| 3. Personal amount field | Removed free-form amount entry from deposit/loan comparisons. Four fixed examples (1, 2, 5, 10 lakh) calculate locally; no personal amount is requested, sent or persisted. |
| 4. Mixed-language answers | Bangla service answers use Bangla digits/dates and bank-specific source captions. Product labels are localized; original names/quotes/conditions remain on source sheets. Known slab phrases are translated; unknown conditions explicitly direct users to the original source rather than guessing. English news headlines have a Bangla language tag. |
| 5. Sideways phone | Teal/gold hold-upright panel on touch phones. Underlying content is inert; recording/playback stops. Portrait keyboard resizing does not trigger it, and desktop retains its centered column. |
| 6. Duplicate bank names | English mode hides the English subtitle and avoids repeating the name in report metadata. Bangla mode retains the useful English subtitle. |
| 7. Tab wrapping | English navigation now says Services. Large-text wrapping remains available for accessibility. |
| 8. Duplicate news label | Main news cards retain one verification tag and omit the duplicate summary line. |
| 9. Highest rate / missing status | A prominent full-width unverified-condition notice accompanies offers from a no-data bank. Spoken service answers/readouts also announce that limitation. Sorting is still by published number, not a recommendation. |
| 10. Watch expectations | A visible explanation before and after tapping distinguishes saved Watch selections from SMS/WhatsApp alerts, which are coming soon and are not sent. |
| 11. Search button icon | Replaced the dot with a microphone SVG; the accessible name is retained. |
| 12. Headers | HSTS, CSP, nosniff and Referrer-Policy are deployed, including controlled error responses. App scripts remain self-only. API documentation uses scoped CDN permissions and hashes of its exact initializer, without weakening app/SSE policy. |
| 13. Startup work | Preserved the exact theme families using five locally hosted, licensed font subsets (277,968 bytes). Removed the startup bank-index request on Home. HTML no-transform prevents optional Cloudflare script injection from adding requests or conflicting with CSP. |

## Insurance provenance

Source: Ministry of Law, [Deposit Protection Act 2026, Act 75](https://bdlaws.minlaw.gov.bd/act-print-1703.html),
sections 12 and 21–23. Eligible bank deposits have a Tk 2 lakh cap per depositor
per member bank, combining accounts. The payment provisions are staged: the
liquidator's list, then Bangladesh Bank's payment after the required information.
The displayed wording preserves the 10+7 working-day conditions instead of an
unconditional 17-day guarantee. Human legal/native wording review remains useful.
The rule does not claim present coverage for every finance company.

Release: `export-v5.2-2026-10-27-law75`; 9 banks, 43 facts, 58 sources, 470 service
attributes and 1 bank-insurance rule. Existing eight-strong/one-no-data baseline
and hidden-offer rules remain unchanged. Import was preceded by a private backup.
The two insurance audio drafts were generated from this sourced rule without
regenerating the previous twenty. All 22 private drafts await native review;
none has been marked reviewed or published.

## Verification

- 78 pytest tests / 25 subtests and five frontend suites pass.
- Reproducible live browser checks cover Home, EN names/tab, insurance source,
  Watch expectations, four local examples with no request on selection, source
  quote integrity, prominent no-data warning, news labels, phone rotation,
  keyboard resize and desktop. No microphone/provider request is made by these
  checks. Temporary anonymous Watch selection is removed afterward.
- The public HTTPS check reached network idle in **0.85s**, made 13 requests,
  made **zero external requests**, and logged no console/runtime errors.
  This single fast-link observation is not a mobile performance guarantee.
- A separate fresh context with service workers enabled reached shell/font/worker
  readiness in **0.80s**. Offline Home reload retained the local theme fonts.
  The detailed UI smoke test blocks service workers to isolate current server
  responses; the request count above is for page-initiated requests.
- Live typed Meta requests returned a localized FDR answer with three sources in
  3.58s and the qualified insurance answer with its source in 4.08s. These are
  text-path probes, not microphone or speech-accuracy acceptance.
- Local before/after cold-context checks were 0.79s/0.74s; external requests fell
  from six to zero. This environment did not reproduce the review's 4.9s result.
- Strict CSP exposed automatic Cloudflare beacon injection during live testing;
  the documented [no-transform mechanism](https://developers.cloudflare.com/web-analytics/faq/)
  removed it. Swagger UI was checked separately for CSP compatibility.
- Real-phone microphone, TalkBack/VoiceOver, true text enlargement and offline
  field acceptance remain required. Browser emulation does not replace them.

CI follow-up caught and corrected an operations bug: backups with identical
second timestamps could be pruned by random UUID filename order. Retention now
always keeps the newly completed snapshot and uses modification time for older
completed snapshots. A fixed-clock/descending-ID regression reproduces the old
failure deterministically; unfinished concurrent dumps are excluded from pruning.

Run against the controlled demo (creates/removes one anonymous Watch entry):

```sh
/path/to/venv/bin/python tests/check_website_review.py --base-url https://app.sumon.me
```

Screenshots from the live checks are in `design/reviews/website-20261027/`.

## Approved v6.2 follow-up

The owner supplied the replacement incident archive after the original review.
The live catalogue now contains eleven banks: eight Strong, two High and one
No data, under unchanged status thresholds. Service comparisons retain their
original nine-bank scope and 470 attributes. The supplement imports four
financial facts, two ratings, nineteen incidents, thirty-four source links and
twenty-three status updates. Raw inputs remain private. See the
[review and source limitations](../seed/incidents/README.md).

Validation: 82 pytest tests / 25 subtests and five frontend suites pass. Import
and reimport succeed in isolated SQLite; the backed-up `ilma` MySQL import also
succeeds. Live HTTPS browser checks cover both languages, two High cards,
incident filters/source sheets, missing Islami NPL and phone/rotation/desktop
layouts with no runtime errors. Live HTML serves asset version 33 and retains
strict CSP, HSTS, nosniff and no-transform. These checks do not replace human
source review, physical screen-reader testing or real microphone acceptance.
