# ILMA app spec 03: Bank tab

For Sumon's build agent. Written 27 Oct 2026. Read it together with APP_SPEC_01 (database and status rules) and the design build checklist plus `tokens.css`. If they disagree, this spec wins for the Bank tab.

## 0. What the Bank tab is

The Bank tab is one of four tabs: হোম · ব্যাংক সেবা · **ব্যাংক** · খবর.

It answers one question: **"How is this bank doing, and why?"** It has three screens:

1. **B1 Bank list:** the 9 demo banks.
2. **B2 Report card:** one status word, 3 reasons, the insurance line, and links to details. This is FRD S-04 under plan A.
3. **B3 Detail pages:** financial health, rating, news, and "Ask about this bank".

Voice or search on Home that finds a bank opens **B2** directly.

**Plan A, not 7 checks.** The mock app (`S04-Report.html`) still shows "৭টি স্বাস্থ্য পরীক্ষা" (7 health checks). Do not build that block. Replace it with "কেন?" (why) and 3 reasons (section 3). Keep everything else in the mock's layout.

## 1. Data: from Sumon's CSV export into the seed tables

Input files are in the v4 export zip. Load them through the APP_SPEC_01 seed loader. Write a small converter `seed/convert_v4_export.py` that reads the CSVs and writes `seed/*.csv` in the spec 01 format. Never edit numbers by hand in code.

**Banks (9 only):** EBL, BRACBANK, CITYBANK, MTB, NCCBANK, PRIMEBANK, DUTCHBANGL, BANKASIA, SBACBANK. Join on `banks.csv` → `short_code`. Ignore all other banks.

| Source file | Rows to keep | Goes to |
|---|---|---|
| `banks.csv` | the 9 banks | `institution` (name_en, slug from short_code, type bank, licensed true, listed true, coverage full). Add `name_bn` by hand from the table below. |
| `bank_aliases.csv` | the 9 banks | `institution_alias` (Bangla and English) |
| `annual_report_financials.csv` | `year = 2025`, `is_rejected` false, metric in CRAR, NPL_RATIO, PROFIT_AFTER_TAX | `fact`: crar and npl_ratio as ratio (15.49 → 0.1549), net_profit in taka (million × 1,000,000). Keep `basis`, `page_no`, `quote`. Store 2024 rows too if present, for the trend. |
| `bank_credit_ratings.csv` | `is_current` true and target_type Entity | `rating` (agency, long_term, short_term, outlook, rating_date, valid_until, quote) |
| `bank_news.csv` | articles that mention one of the 9 banks (via `article_banks.csv`) | `event` with `status = reported`, `official = false`, `type = other` (or the obvious type), plus `source`. These never change a status (spec 01, section 4.3). |
| `documents.csv` | the documents referenced above | `source` (url, title, published date, page) |

**Do not load:** `bb_bank_actions`, `bb_circulars`, `bb_press_releases`, `dse_*`, or `scrape_report.md`. `scrape_report.md` contains numbers that are not in the data, so never read from it.

**`checked_by` / `checked_on`:** fill in `agent-v4` and the export date. Sumon will change a row to his name once he has checked it by hand. The app shows a small "যাচাই করা হয়েছে" (checked) mark only on rows Sumon has checked.

**Bangla names:**

| Code | name_bn | name_en |
|---|---|---|
| EBL | ইস্টার্ন ব্যাংক পিএলসি | Eastern Bank PLC |
| BRACBANK | ব্র্যাক ব্যাংক পিএলসি | BRAC Bank PLC |
| CITYBANK | দ্য সিটি ব্যাংক পিএলসি | The City Bank PLC |
| MTB | মিউচুয়াল ট্রাস্ট ব্যাংক পিএলসি | Mutual Trust Bank PLC |
| NCCBANK | ন্যাশনাল ক্রেডিট অ্যান্ড কমার্স ব্যাংক পিএলসি | National Credit and Commerce Bank PLC |
| PRIMEBANK | প্রাইম ব্যাংক পিএলসি | Prime Bank PLC |
| DUTCHBANGL | ডাচ্-বাংলা ব্যাংক পিএলসি | Dutch-Bangla Bank PLC |
| BANKASIA | ব্যাংক এশিয়া পিএলসি | Bank Asia PLC |
| SBACBANK | সাউথ বাংলা এগ্রিকালচার অ্যান্ড কমার্স ব্যাংক পিএলসি | South Bangla Agriculture and Commerce Bank PLC |

Sumon should check these Bangla spellings.

**Expected result with the plan A rules** (as a test, `test_demo_seed.py`): 8 banks get `strong` and SBACBANK gets `no_data` (it has no 2025 figures). If your result is different, stop and report. Do not change thresholds to make it match.

**Three values Sumon checks before the demo.** Add them to `seed/TO_CHECK.md`:
1. NCC CRAR 15.54%: the quote is a 5-year table, so confirm it is the 2025 column.
2. Prime and City CRAB AAA: both have the same date as EBL (17 Jun 2026). Open each source once.
3. MTB figures are consolidated (bank plus subsidiaries); the others are bank-only or unknown. Show "গ্রুপ হিসাব" (group accounts) next to MTB's numbers.

## 2. B1 Bank list

- Teal stage at the top: title "ব্যাংক", with the subtitle "কোন ব্যাংকের অবস্থা জানতে চান?" (Which bank do you want to check?).
- A search box (TXT-01 "ব্যাংকের নাম লিখুন") plus a small mic button that uses APP_SPEC_02 voice.
- The 9 banks on the ivory sheet, as rows: Bangla name, English name underneath, and on the right a small status chip (mark + word, e.g. "✓ ভালো অবস্থা" or "? তথ্য কম"). Never colour alone. Sort alphabetically in Bangla. Do not sort by status, because that reads like a ranking.
- One line under the list: "ডেমোতে ৯টি ব্যাংক আছে। আরও ব্যাংক শিগগির।" (9 banks in the demo, more soon). Below it, the prior-work note link: "তথ্য কোথা থেকে এসেছে" (where the data comes from). That opens a sheet with the README's prior-work text.
- Tapping a row opens B2.

## 3. B2 Report card (FRD §10.1 under plan A)

Top to bottom:

1. **Hero (teal, status on a #0F2624 panel):**
   - back button, the bank's Bangla name (Tiro 29), and English name plus type underneath
   - status mark and word (Tiro 42), with its one-line meaning (FRD §11.1)
   - the 3-step scale ভালো · সতর্ক · ঝুঁকি বেশি with a marker. There is **no marker for তথ্য কম**.
   - the data line: "তথ্যের তারিখ: ৩১ ডিসেম্বর ২০২৫ · হালনাগাদ {date}". The first date is the newest figure's period end; the second is the newest `checked_on`.
2. **Insurance line:** from the `insurance_rule` table (VS-21 for banks), with a shield icon. It links to the insurance split explainer once that's built; until then, no link.
3. **"কেন?":** exactly the reasons from `evaluate()` (up to 3), each one sentence (spec 01, section 5), with a blue "সূত্র ›" link. Tapping it opens the **Source sheet**: the source title, page, and the quote with the number highlighted (#FFE29A), plus "উৎস খুলুন" (open the URL) and "বন্ধ করুন" (close).
4. **"যা যাচাই করা হয়নি"** (what wasn't checked): one muted line, always shown: "বাংলাদেশ ব্যাংকের ব্যবস্থা ও জরিমানা এই ডেমোতে যাচাই করা হয়নি।" (Bangladesh Bank actions and penalties weren't checked in this demo.) Honest, and judges will respect it.
5. Buttons:
   - **শুনুন** (Listen, solid #1E4542): reads the status, insurance line and reasons using TTS
   - **নজরে রাখুন** (Watch, outline)
6. Four full-width rows that open B3:
   - আর্থিক অবস্থা (Financial health)
   - রেটিং (Rating)
   - খবর (News about this bank)
   - এই ব্যাংকের সেবা ও হার (Services and rates) → jumps to the Bank services tab, filtered to this bank
7. **"এই ব্যাংক নিয়ে প্রশ্ন করুন"** (Ask about this bank) → B3-Ask.
8. The not-advice note VS-08 at the bottom.

Rules:
- No gold, no mascot and no glow on this screen (checklist §2).
- The English pill switches every text to `text_en`.
- Bank names never appear next to words like "নিরাপদ" (safe) or "ঝুঁকিমুক্ত" (risk-free), and no prediction words (STS-06).
- Data comes from `GET /v1/institutions/{id}/report-card`. The app never computes the status itself.

## 4. B3 Detail pages

**B3-Health · আর্থিক অবস্থা:** three rows, each with value, period and "সূত্র ›":
- মূলধন অনুপাত (capital ratio), with the legal minimum shown as text: "ন্যূনতম {crar_min}%"
- খেলাপি ঋণ (bad loans), with the plain line from H4/W1: "প্রতি ১০০ টাকার ঋণে {npl} টাকা ফেরত আসছে না" (of every Tk 100 lent, Tk {npl} isn't being repaid)
- কর-পরবর্তী মুনাফা (profit after tax), in crore taka

If 2024 values exist, show a small "২০২৪: x%" under each row. Don't draw a chart (two points don't make a trend). Each row needs a one-sentence explanation from the FRD §21.2 glossary.

**B3-Rating · রেটিং:** agency, long-term grade, short-term grade, outlook, date, and valid until. Add one line on what the grade means (glossary). If `valid_until` has passed, show "মেয়াদ শেষ" (expired).

**B3-News · খবর:** articles linked to this bank, newest first. Each shows the headline, newspaper, date and label TXT-04 "খবরে প্রকাশিত, নিশ্চিত নয়" (reported in the news, not confirmed), and opens the article URL. If there are none: E-12. Never show the full article text (copyright); show only the headline and link.

**B3-History · জালিয়াতি ও মামলার ইতিহাস** (fraud and legal history; data comes from v6 `incidents`, loaded into `event` and `event_source`):
- A timeline, newest first. Each item shows: date, type label, one neutral sentence, status chip, and "সূত্র ›" (with 2 or more sources when not official).
- Status chips:
  - official: "সরকারি সূত্রে নিশ্চিত" (confirmed by official source)
  - news only: TXT-04 "খবরে প্রকাশিত, নিশ্চিত নয়" (reported in the news, not confirmed)
  - closed: "খালাস" (acquitted) or "মামলা প্রত্যাহার" (case withdrawn), shown just as clearly as "দণ্ডিত" (convicted)
- `single_source` incidents are never shown.
- Filter chips: সব (all) · সরকারি ব্যবস্থা (official action) · জালিয়াতি (fraud) · জরিমানা (penalty) · সাইবার (cyber).
- Header line: "{from}–{to} সময়ের প্রকাশিত তথ্য, {n}টি ঘটনা" (published information from {from} to {to}, {n} incidents). Always state the window searched. If nothing was found: E-12.
- Only official incidents inside the FRD time windows can change the status (spec 01, section 4.3). Older ones are history only, and the card says so: "পুরনো ঘটনা অবস্থা নির্ধারণে গণ্য হয়নি" (older incidents were not counted for the status).
- On B2, the row "জালিয়াতি ও মামলার ইতিহাস ({n})" sits above the news row.

**B3-Ask · এই ব্যাংক নিয়ে প্রশ্ন করুন:** the Ask screen with the bank already chosen (`institution_id` sent with every question, so intent detection knows the topic). It uses `/v1/ask` (FRD §26.3): Muse Spark answers only from this bank's facts, every sentence maps to a fact ID, and with no facts it gives the fixed "এই তথ্য আমাদের কাছে নেই।" (we don't have this information). Offer 3 suggestion chips:
- "এই ব্যাংকের খেলাপি ঋণ কত?" (What are this bank's bad loans?)
- "রেটিং কী?" (What is the rating?)
- "আমার টাকা কতটা সুরক্ষিত?" (How safe is my money?)

## 5. API (adds to spec 01)

| Route | Returns |
|---|---|
| `GET /v1/institutions?list=demo` | The 9 banks with `id, slug, name_bn, name_en, status{code,label_bn,label_en}` |
| `GET /v1/institutions/{id}/figures` | All fact rows with source fields, newest first |
| `GET /v1/institutions/{id}/ratings` | All current rating rows with source fields |
| `GET /v1/institutions/{id}/events?page=` | News events with sources, 20 per page |

The report card stays as in spec 01, section 6.

## 6. Accessibility and states

- TalkBack on B2 reads first: "অবস্থা: ভালো অবস্থা। কারণ তিনটি।" (Status: good condition. Three reasons.) Then the reasons in order.
- Every "সূত্র ›" link is a button labelled "সূত্র দেখুন: {short reason}".
- Loading over 1 second: "একটু অপেক্ষা করুন…" (please wait a moment). Offline: E-01, showing the cached card with its date.
- Test at 360×640 with text at 200%; nothing may be cut off.

## 7. Done when

1. `pytest` passes: spec 01 tests plus `test_demo_seed.py` (8 strong, 1 no_data).
2. On a phone at app.sumon.me: Home → say "ইস্টার্ন ব্যাংক" → B2 for EBL opens, with 3 reasons that each open the right page and quote.
3. Every number on B2, B3-Health and B3-Rating opens a source sheet whose quote contains that number.
4. Screenshots of B1, B2 (EBL), B2 (SBAC, তথ্য কম), B3-Health, B3-Rating and the Source sheet, posted with the push to branch `screen/bank-tab`.
