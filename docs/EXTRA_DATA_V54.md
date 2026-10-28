# Extra publication data — 28 October 2026

The owner supplied APP_SPEC_06 and the extra v5.4 archive. Its raw CSVs, original
review and collector metadata remain private. This feature publishes normalized
titles, dates and source links, not announcement bodies, raw font encodings or
collection work files. Imported rows are `agent-extra-v5.4`, not personal reviews.
Existing unrelated local work is preserved separately from this feature commit.

## Imported scope

Only the eleven configured banks are eligible for bank-specific publications.
The loader adds dedicated `extra_item` and `related_entity` tables in `ilma`;
it does not import deposit rates, share prices or purported weak-bank flags.
No extra publication changes a financial status.

- 445 supplied DSE announcements become 438 distinct title/date/source entries;
  seven duplicates are removed. All 190 `other` rows are retagged from titles,
  with `company_notice` for headings too general for a stronger category.
  Of fifteen audit-emphasis candidates, three explicitly qualified-opinion
  disclosures retain that tag and twelve become financials. They are still
  bank disclosures, not independent regulator findings.
- 98 report records become 69 distinct links: one year-mismatch row is dropped,
  then twenty-eight duplicates removed. Unknown publication dates stay unknown;
  the displayed year is a reporting year. Reports sort by reporting year/period.
- Five distinct saver-relevant BB press notices remain after market-operation,
  event and duplicate filtering. Titles lose the trailing `more....` suffix.
- Nineteen bank-specific circulars are rematched from titles against all 63
  institutions. Six incorrect or ambiguous original links are rejected,
  including joint-bank notices, the unrelated state-bank notices and Pakistan.
  A nested short name such as Trust Bank within Mutual Trust Bank is handled
  as one full-name match. No broad substring or fuzzy bank match is accepted.
- Twelve matching BRPD/DOS/DFIM/PSD rules meet the import's twelve-month window;
  the News endpoint also filters that window at request time.
- Two Unicode-quoted official special exemptions appear in History as
  `other_compliance`, explicitly without a status effect. They are not fines.
- Thirty-three subsidiary/related names are loaded for exclusions. Parent-bank
  matches are blocked in voice candidates and REST search, including the
  contextual bank fallback.

Exact decisions are in `seed/extra/review_notes.json`. These are supplied
records, not a comprehensive search or completed human source review.

## Source links and interface

EBL and other bank detail screens add Company announcements, Reports and BB
notices. Pages show twenty items at a time, with a Show more button. The News
screen adds BB warnings, new rules and announcements for the anonymous device's
watched banks. Without a watch, it explains how to select a bank. That response
is `Cache-Control: no-store` and varies by the device header; it is not offline
cached. Existing newspaper news remains separately labelled.

The source-document map is from the previously supplied v5.4 services archive.
Many press notices have no individual URL: their source is the recorded BB press
index, visibly labelled **Open source index**. DSE records similarly link to
the recorded company page. Report/circular links use their supplied documents.
No individual PDF or announcement URL is invented. Original English headings
are identified in Bangla mode; interface labels and dates are localized.

## Reproduction

```sh
EXPORT_DIR=/PRIVATE/extra-v5.4 /path/to/venv/bin/python seed/convert_extra.py \
  --documents /PRIVATE/seed-v5.4/documents.csv --checked-on 2026-10-28
PYTHONPATH=api /path/to/venv/bin/python -m ilma_api.extra_data seed/extra
PYTHONPATH=api /path/to/venv/bin/python tests/check_extra_browser.py --base-url http://localhost:8001
```

Load the base bank and incident seeds first on a new database. Back up before a
live import. Reimport replaces only managed extra-publication rows, preserves
unchanged personal reviews, and leaves financial/service/incident data alone.
The source map is an explicit converter input because this ZIP omits documents.

## Acceptance

91 Python tests / 25 subtests and five frontend suites pass in the isolated
feature checkout. Tests cover scope, source links, audit classification,
misassigned/nested bank names, subsidiary exclusion, idempotence, unchanged
financial/service data and private watched-bank filtering. Live BN/EN browser checks passed all three EBL pages, pagination, source
links, private watched-bank filtering and cleanup, phone/desktop viewports
and 200% text. The public service reports `extra-v5.4-2026-10-28`;
Cloudflare serves asset version 38 with strict CSP/HSTS/nosniff and no-transform.
Swagger returns 200. A live typed subsidiary query with its parent selected
returns `related_entity`, before intent/provider processing.
Screenshots are in `design/reviews/extra-data/`. Physical screen-reader and device acceptance,
and human checking of source availability/content remain outstanding.
