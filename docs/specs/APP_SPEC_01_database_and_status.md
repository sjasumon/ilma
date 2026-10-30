# ILMA app spec 01: database, seed loader, status rules, report-card API

For Sumon's build agent. Written 27 Oct 2026. Build this before any screen that shows bank data.

## 0. Ground rules (do not break)

1. **New work only.** Write everything fresh in `ilma-private`. Do not copy code from the scraper (`bdbank`) or `demo_pack_v1`.
2. **Real data only.** No made-up numbers for real banks. The only made-up bank allowed is **"Sample Bank (demo)"**, and only in tests. Its name must say "demo".
3. **No AI for status.** The status word and the reasons come only from the Python rules below. No model call anywhere in this spec.
4. **Every fact has a source.** It needs a source URL, title, publish date, page, the exact quoted line, who checked it and when. The loader refuses any row that's missing one of these.
5. **No personal data.** No column anywhere for amount, account number, name, NID or phone (FRD DAT-01).
6. **Commits.** In Sumon's name only, with no co-author lines. No keys in the repo; `.env` stays ignored.
7. `.gitignore` blocks `*.sql`. Define the tables in Python (SQLAlchemy) and create them with a command. Do not commit a `.sql` dump.

## 1. Layout

```
api/
  pyproject.toml            fastapi, uvicorn, sqlalchemy 2, pymysql, pytest, httpx
  ilma_api/
    settings.py             reads DATABASE_URL from env
    db.py                   SQLAlchemy tables (section 2), create_all command
    seed_loader.py          CSV -> DB with checks (section 3)
    rules/
      thresholds.json       versioned config (section 4.1)
      ratings.py            rating scale (section 4.4)
      status.py             evaluate() (section 4)
      reasons.py            reason templates + Bangla number/date formatting (section 5)
    report_card.py          builds the JSON in section 6
    main.py                 FastAPI routes (section 6)
  tests/
    fixtures/               Sample Bank (demo) CSVs only
    test_status.py, test_reasons.py, test_seed_loader.py, test_api.py
seed/
  *.csv                     header rows only for now. Sumon adds real hand-checked rows.
  README.md                 what each column means
```

Commands: `python -m ilma_api.db create` and `python -m ilma_api.seed_loader seed/`. Tests run on SQLite and must also pass on MySQL 8 (utf8mb4).

## 2. Tables

The FRD says the app reads `ilma_release` views made by the scraper. For the hackathon, those views are replaced by these **seed tables**, loaded from hand-checked CSVs. Keep the same idea: the API only reads these tables and never writes to them.

**release**: release_id (PK, e.g. `seed-2026-10-27-01`), loaded_at, note. Every load makes a new release.

**institution**: id INT PK, slug (unique, used in URLs), name_bn, name_en, type ENUM(bank, nbfi), islamic BOOL, licensed BOOL, listed BOOL, coverage ENUM(full, partial, licence_only).

**institution_alias**: id, institution_id FK, alias, lang ENUM(bn, en). Unique (institution_id, alias).

**source**: source_id PK (string), url, title, publisher, published_at DATE, page INT NULL, image_path NULL (page image for proof snap later), checked_by, checked_on DATE.

**fact** (key figures): fact_id PK (e.g. `kf-ebl-npl-2025`), institution_id FK, metric ENUM(crar, npl_ratio, net_profit, provision_shortfall), value DECIMAL(20,6), unit ENUM(ratio, bdt), period (e.g. `2025`), period_end DATE, source_id FK, quote TEXT, highlight JSON NULL (box on the page image, for later), checked_by, checked_on.
- Ratios are stored as decimals: 15.49% is `0.1549`. Money is integer taka.

**rating**: fact_id PK, institution_id FK, agency, long_term, short_term NULL, outlook ENUM(stable, positive, negative, developing) NULL, rated_on DATE, valid_to DATE NULL, source_id FK, quote, checked_by, checked_on.

**event**: event_id PK, institution_id FK, type ENUM(administrator, board_dissolved, forced_merger, licence_cancelled, liquidation, withdrawal_limit, emergency_liquidity, provision_deferral, penalty, fraud_case, other), title_bn, title_en, status ENUM(reported, alleged, case_filed, charged, convicted, settled, official), official BOOL (an official source such as Bangladesh Bank or a court confirms it), severity TINYINT NULL (penalties: 1-5), event_date DATE, last_update DATE, checked_by, checked_on.
**event_source**: event_id FK, source_id FK. An event needs at least 1 source, and at least 2 if status is `alleged` or `reported`.

**rate**: fact_id PK, institution_id FK, product ENUM(fdr, dps, savings), tenor_months, rate DECIMAL(6,4), min_amount_bdt NULL, as_of DATE, source_id FK, quote, checked_by, checked_on.

**share_price_flag**: institution_id PK, days_below_face INT, window_end DATE, source_id FK. Optional, and listed banks only. Leave it empty if there's no clean source. Do not use DSE `/api`.

**insurance_rule**: inst_type PK ENUM(bank, nbfi), covered BOOL, limit_bdt INT NULL, payout_working_days INT NULL, covered_from DATE NULL, text_bn, text_en, source_id FK.
- Bank row: covered, 200000, 17 (Deposit Protection Act 2026). Sumon adds the official source URL.
- NBFI row: not covered, covered_from 2028-07-01, text from VS-22.

**App tables (`ilma_app`, FRD §27.1):** build them as written in the FRD: app_device, app_watch_item, app_push_subscription, app_alert, app_alert_delivery, app_question_log, app_rate_counter, app_answer_cache, app_content, app_feedback, app_correction, app_daily_counts, app_admin_audit. Add `'sms','email'` to `app_alert_delivery.channel`. Do **not** add a phone or email column yet: whether SMS alerts may store a phone number is still open with Sumon. Skip app_whatsapp_link for now.

## 3. Seed loader checks

Reject the whole load (no partial loads) and print every bad row if:
- any required source field or checked_by/checked_on is empty;
- a fact, rating or rate points to a missing source or institution;
- a ratio is outside 0 to 1, or a rate is outside 0 to 0.25;
- the same institution, metric and period appears twice;
- an alleged or reported event has fewer than 2 sources;
- an institution's name has "demo" in it but the file isn't a test fixture (so the sample bank never reaches the real DB).

On success, print counts per table and the new release_id.

## 4. Status rules (plan A, FRD §11)

`evaluate(inst, data, as_of: date, cfg) -> Result(code, triggers[], reasons[], rules_version)`

### 4.1 thresholds.json

```json
{
  "rules_version": "2026.10-v1",
  "crar_min": 0.10,
  "crar_buffer": 0.025,
  "npl_high": 0.25,
  "npl_watch": 0.10,
  "rating_high_at_or_below": "BB+",
  "fdr_premium_pp": 0.02,
  "share_below_face_days": 60,
  "figures_max_age_months": 18,
  "windows_months": {"H1": 24, "H2": 12, "W3": 12, "W4": 24, "W8": 12, "W9": 6},
  "penalty_min_severity": 3
}
```
Put a `_note` field in the file saying the values must be checked by a domain expert (STS-04). `crar_min` is the Bangladesh Bank minimum and must be confirmed.

### 4.2 Order (stop at the first that applies)

1. **তথ্য কম (`no_data`)**: the latest `npl_ratio` **or** the latest `crar` is missing, or its `period_end` is more than 18 months before `as_of`, **and** no High trigger applies.
2. **ঝুঁকি বেশি (`high`)**: any High trigger.
3. **সতর্ক থাকুন (`watch`)**: any Watch trigger.
4. **ভালো অবস্থা (`strong`)**: otherwise.

"Latest" means the row with the newest `period_end` for that metric.

### 4.3 Triggers

| ID | Fires when |
|---|---|
| H1 | event of type administrator, board_dissolved, forced_merger, licence_cancelled or liquidation, `official=true`, event_date within 24 months |
| H2 | withdrawal_limit event, official, within 12 months |
| H3 | latest crar < crar_min |
| H4 | latest npl_ratio >= 0.25 |
| H5 | latest long-term rating (newest rated_on across agencies) is BB+ or lower |
| W1 | 0.10 <= latest npl_ratio < 0.25 |
| W2 | crar_min <= latest crar < crar_min + crar_buffer |
| W3 | within 12 months: the same agency's rating went down, or the outlook is negative, or the latest rating is BBB+, BBB or BBB- |
| W4 | within 24 months: a penalty event with severity >= 3 and official, or a fraud_case with status case_filed or later (case_filed, charged, convicted) |
| W5 | the latest provision_shortfall is > 0, or a provision_deferral event is official within the latest report year |
| W6 | the latest net_profit is < 0 |
| W7 | the bank's 12-month FDR rate minus the median 12-month FDR of all institutions that have one is >= 0.02. Compute the median on the fly; use the newest as_of per bank |
| W8 | emergency_liquidity event, official, within 12 months |
| W9 | share_price_flag.days_below_face >= 60 and window_end within 6 months |

- Events that are not official (`reported`, `alleged`) **never** fire a trigger.
- Triggers based on time windows expire on their own because they're computed from `as_of`.
- Each trigger keeps the fact_id or event_id that caused it (STS-03).

### 4.4 Rating scale

Order from best to worst: AAA, AA+, AA, AA-, A+, A, A-, BBB+, BBB, BBB-, BB+, BB, BB-, B+, B, B-, CCC+, CCC, CCC-, CC, C, D.
Map CRAB-style grades first: AA1→AA+, AA2→AA, AA3→AA-, A1→A+, A2→A, A3→A-, BBB1→BBB+, BBB2→BBB, BBB3→BBB-, BB1→BB+, BB2→BB, BB3→BB-, B1→B+, B2→B, B3→B-. Remove spaces and suffixes like "(Bank)" or "(Islamic)". If a grade isn't on the scale, ignore that rating and log a warning. Do not guess.

### 4.5 Picking exactly 3 reasons (FRD §11.4)

1. All High triggers, in the order H1, H2, H3, H4, H5.
2. Then Watch triggers, in the order W1 to W9.
3. Then positive facts, in this order:
   - P1 crar >= crar_min + buffer
   - P2 npl_ratio < npl_watch
   - P3 latest rating is A- or better with no downgrade or negative outlook
   - P4 net_profit > 0
4. Then the newest non-official event, labelled "খবরে প্রকাশিত, নিশ্চিত নয়", but only if there are still fewer than 3.
5. For `no_data`, the first reason is the "No data" line naming what's missing (annual report or rating).
6. If there are still fewer than 3, stop. Never pad with filler. If there's nothing at all, use the "None" line.

## 5. Reason text

Use the FRD Appendix B.2 templates exactly, in Bangla and English, for H1 to W9, None and No data. Add these positive templates:

| ID | Bangla | English |
|---|---|---|
| P1 | মূলধন অনুপাত {crar}%, আইনি ন্যূনতমের ({min}%) চেয়ে বেশি ({period})। | Capital ratio {crar}%, above the legal minimum ({min}%) ({period}). |
| P2 | খেলাপি ঋণ {npl}%, যা কম ({period})। | Bad loans {npl}%, which is low ({period}). |
| P3 | দীর্ঘমেয়াদি রেটিং {rating}, স্থির ({agency}, {date})। | Long-term rating {rating}, stable ({agency}, {date}). |
| P4 | গত বছর মুনাফা {amount} কোটি টাকা ({period})। | Profit of Tk {amount} crore last year ({period}). |

Formatting:
- Bangla digits ০-৯ in `text_bn`, Western digits in `text_en`.
- Percent with 2 decimals, trailing zeros dropped (0.1549 → ১৫.৪৯%).
- Crore = taka / 10,000,000, with 2 decimals.
- Dates as "২২ অক্টোবর ২০২৬" / "22 Oct 2026".
- Never use the words দেউলিয়া or ডুবে যাচ্ছে, and no predictions (STS-06). Add a test that scans every template for them.

Each reason in the output: `rule, text_bn, text_en, fact_id, source_url, source_title, published_at, page, quote`.

## 6. API (FastAPI, base `/v1`)

| Route | Returns |
|---|---|
| `GET /health` | `{ok, release_id, db}` |
| `GET /institutions?q=` | Matches on name_bn, name_en or alias: case-insensitive, Bangla NFC-normalised, contains-match. Up to 5 results: `id, slug, name_bn, name_en, type, coverage` |
| `GET /institutions/index` | All institutions with aliases (for offline search) |
| `GET /institutions/{id}/report-card` | Same shape as FRD Appendix C.1: `institution, status{code,label_bn,label_en,rules_version}, reasons[3], insurance, ratings[], figures[], events[] (latest 5), rates{as_of, fdr_12m, sector_median_fdr_12m, source_url}, data_date, release_id, disclaimer_key:"VS-08"`. Every figure, rating and rate also includes its source fields (API-03) |

- 404 uses the shared error format: `{"error":{"code":"not_found","message_bn":"...","message_en":"..."}}` with E-06 wording.
- For `licence_only` coverage, return status `null` and the E-09 message. Never return "strong" by default.
- `data_date` = the newest checked_on among the facts used.
- Device auth (`POST /device`) comes later, in another spec. These read routes are open for now.

## 7. Tests that must pass

Use the Sample Bank (demo) fixtures. Write one test per trigger: H1-H5, W1-W9, and P1-P4.

Plus these:
1. CRAR 15.49% and NPL 2.24% from 2025, rating AAA, profit > 0 → `strong`, with reasons P1, P2, P3.
2. NPL 18% → `watch`, first reason W1.
3. NPL 26% and CRAR 8% → `high`, reasons H3 then H4.
4. Figures 20 months old → `no_data`. The same with an official administrator event → `high`.
5. A reported (non-official) fraud story → no status change, and it appears only as a labelled 3rd reason.
6. An official event 25 months old → no H1.
7. The loader rejects a fact with an empty quote and loads nothing.
8. The report-card JSON for Sample Bank matches a saved snapshot.
9. A search for "ইস্টার্ন" with an alias row finds the bank, and so does a search for "eastern".

## 8. Hand back

Push a normal new commit to the ILMA repository and tell Sumon. Obtain manual review before the merge. Include the `pytest` output and the loader output for the fixtures.
