# ILMA app spec 06: using supplementary source data

For ILMA implementation. Written 28 Oct 2026. Input: the v5.4 export (`bb_banking_data_v4.zip`, 27 Oct 16:36 UTC), kept outside the repo and read via `EXPORT_DIR`. Load everything through converters into seed tables, as in specs 03 and 05. The app shows each item's source link only.

Filter to the 11 banks: the 9 demo banks + NBL + ISLAMIBANK. Match on `banks.id` and `dse_code`.

## Use now

| Table | Rows (11 banks) | Where in the app | Fix before loading |
|---|---|---|---|
| `dse_bank_announcements` | 445 (22 Aug 2024 – 26 Oct 2026) | B3 new page **"কোম্পানির ঘোষণা"** (company announcements): dividend, rating, financials, AGM, MD change, board meeting. Also the News tab, filtered to the user's watched banks. Label: "ডিএসই-তে ব্যাংকের নিজের ঘোষণা" (the bank's own DSE announcement). | Re-tag the 190 `other` rows by title keywords. Re-check the 15 `audit_emphasis` rows: keep only those whose text says qualified, adverse, disclaimer or going concern; the rest become `financials`. These never change a status. |
| `bank_reports` | 98 | B3 new row **"প্রতিবেদন"** (reports): annual, half-yearly and quarterly report links, newest first. | Drop rows with `year_mismatch_flag = 1`, or show the title year. |
| `bb_press_releases` | 112 not market operations | News tab section **"বাংলাদেশ ব্যাংকের সতর্কবার্তা ও ঘোষণা"** (BB warnings and notices). Keep saver-relevant items only: fraud warnings (crypto/MLM, unauthorized apps), digital transaction disruptions, deposit/interest/charges policy, refinance schemes. | Drop auctions, bond results, "Statement of affairs", seminars, courtesy calls, MPC minutes (keyword list in `seed/press_release_skip.csv`). Strip the "more...." suffix from titles. |
| `bb_circulars` + `bb_circular_banks` | 4,793 circulars; 26 bank links for the 11 banks | (a) B3 **"এই ব্যাংক নিয়ে বাংলাদেশ ব্যাংকের নোটিশ"** (BB notices about this bank): service outage notices ("Intermission of banking services"), exemptions, name changes. (b) News tab **"নতুন নিয়ম"** (new rules): BRPD/DOS/DFIM/PSD circulars from the last 12 months whose title mentions deposit, interest, card, charges, account, mobile/digital banking. Title + PDF link only. | **The bank matching is wrong in places.** Islami Bank is linked to Janata/Sonali/Agrani circulars, and NBL to a "National Bank of Pakistan" circular. Rematch: the circular title must contain the bank's full name or exact alias from `bank_aliases.csv`, and must not contain another bank's name. |
| `bb_bank_actions` | 2 for the 11 banks (NBL 12 Oct 2026, BRAC 12 Oct 2026, both special exemptions) | B3-History as **official** items, type `other_compliance`, label "বিশেষ অব্যাহতি" (special exemption). They never change a status. | Use the Unicode `quote`, never `raw_value` (Bijoy font). |
| `related_entities` | 33 | The voice/search alias matcher (spec 02) must **not** match a subsidiary name (e.g. "Prime Bank Investment") as the bank. | None. |

## Don't use

| Table | Why |
|---|---|
| `bank_deposit_rates` | Replaced by `services.csv` (v5.4), which has the column proof. Loading both would show two different numbers for the same FD. |
| `dse_bank_prices` | A share price is not about deposit safety, and a price chart on a bank card reads like investment advice, which ILMA promises not to give. |
| `bb_problem_weak_banks` | Removed in v4; never verified. |
| `scrape_report.md`, `manual_check.csv`, TODO files | Work files, not app data. |

## Tests

- `dse_bank_announcements`: 0 rows for banks outside the 11; every row has a DSE link; 0 rows tagged `other` after re-tagging, or a printed list of what's left.
- Circular matching: no Islami Bank row whose title names Janata, Sonali, Agrani or Rupali; no NBL row with "Pakistan".
- Press releases: no row with "Auction", "Statement of affairs" or "Treasury Bond" in the title.

## Done when

B3 for EBL shows company announcements, reports and BB notices. The News tab shows BB warnings and new rules. Every item opens its source link. Push to branch `feature/extra-data`.
