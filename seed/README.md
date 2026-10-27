# Supplied v5.2 export → ILMA seed

Only the nine codes in `bank_names.csv` are imported. Numbers are read from the
supplied CSVs; no bank figures are typed into application code. The source export
uses blank `short_code` values, so the adapter explicitly falls back to `dse_code`.
Bank names are the manual names specified in APP_SPEC_03.

```sh
/home/ubuntu/venv/bin/python seed/convert_v4_export.py /path/to/private/export
/home/ubuntu/venv/bin/python seed/convert_services.py /path/to/private/export
DB_NAME=ilma PYTHONPATH=api /home/ubuntu/venv/bin/python -m ilma_api.seed_loader seed
DB_NAME=ilma PYTHONPATH=api /home/ubuntu/venv/bin/python -m ilma_api.migrate_voice
```

Run the commands on the same host as the service, using its credentials. The
loader refuses a MySQL database other than `ilma`. It validates references,
ratios, duplicate metric/period rows, source fields and numeric quote evidence
before loading. A status-baseline mismatch rolls back the data transaction;
thresholds are never changed to make a load pass. DDL setup is non-destructive
and precedes the transaction. Reimporting the same files is idempotent. Managed
service rows absent from a later snapshot are removed transactionally.

The normalized seed CSVs are committed for reproducible setup. Converter tests
use three-bank handwritten synthetic examples in `tests/fixtures/sample_export/`,
not raw collection output. The original export stays outside the current public
tree. Earlier public-export fixtures remain in old commits; history is preserved.
Full newspaper article text is not copied into seed files or the app. Only linked
headlines and source URLs are imported.
Single-source newspaper headlines are never treated as incident evidence or
official status-changing events. No official actions, fines, DSE API data or
scrape-report numbers are imported.

## Actual import

- 9 institutions, 56 exported aliases (voice migration adds required aliases).
- 43 financial facts, including available 2024 history; 9 entity ratings.
- 58 sources (including the official legal rule) and 5 linked news headlines.
- 470 service attributes: 383 visible and 87 withheld under the current policy.
- Baseline: 8 `strong`, SBAC `no_data`, using the existing plan-A rules.

`product_type_map.csv` contains ordered regex mappings. Ambiguous products such
as “24 & 36 Months” remain without a single tenor and cannot enter a 12/24/36M
comparison. Network, tier, tenor, basis and attribute are filtered separately.
The original value and quote are always retained. Numeric values absent from
the quote are not used for numeric calculations. A printed “Free” amount is
shown as text and sorts as free without inventing a literal numeric quote; derived MTB endpoints and unreadable quotes remain withheld. See
`service_validation.json` and [TO_CHECK.md](TO_CHECK.md).

## Unknown metadata and review

The export's `documents.csv` has fetch timestamps, not publication dates. The
converter preserves publication dates as unknown instead of using fetch dates.
Financial pages are preserved; web rating sources without page numbers show an
unknown/web page. Explicit service `doc_date` values remain beside the numbers.
The export date comes from the supplied service fetch metadata: 2026-10-27.
Imported rows use `agent-v4` or `agent-v5`; none is represented as personally
checked by Sumon. The checked badge appears only for a `Sumon` review. A review
survives a reimport only if the material content is unchanged.

The original export did not supply insurance. The website review added a sourced
bank rule from the Ministry of Law's Deposit Protection Act 2026 (Act 75),
sections 12 and 21–23. This is additional event-time verification, not a claim
that the original collector or Sumon had checked it. Release suffix: `-law75`.
Approved v6 incidents/search-window input is still absent; history remains
unavailable without invented incidents or fabricated dates.
