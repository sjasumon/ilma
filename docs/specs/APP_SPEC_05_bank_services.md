# ILMA app spec 05: Bank services tab

For ILMA implementation. Written 27 Oct 2026. Read it together with APP_SPEC_01 (database), 02 (voice), 03 (Bank tab), 04 (Meta models), and the design build checklist plus `tokens.css`. If they disagree, this spec wins for the Bank services tab.

## 0. What the tab is

The Bank services tab is one of four tabs: হোম · **ব্যাংক সেবা** · ব্যাংক · খবর.

It answers one question: **"Where do I pay less, or earn more, for the same thing?"** Example: the same Visa Signature card costs Tk 7,000 a year at one bank and Tk 12,000 at another. The app shows that side by side, with the source for every number.

It has four screens:

1. **S1 Services home:** four categories.
2. **S2 Compare:** one product, one tenor or tier, all banks side by side.
3. **S3 Offer detail:** one bank's offer, every fee and rate, each with its source.
4. **S4 Ask about services:** Ask with the topic already set to services.

**The rule that keeps this honest:** compare only like with like. That means the same product type, the same tenor (for deposits and loans), the same card network and tier, and the same basis (conventional vs Islamic). Never put a 1-year FD next to a 2-year FD, or a Visa Gold next to an Amex Gold.

## 1. Data: from `services.csv` into the seed tables

**Input:** `services.csv` and `documents.csv` from the latest export zip (v5.4 current). The raw export stays **outside the repo**. The converter reads its folder from env `EXPORT_DIR` (add the name to `.env.example`). Only the cleaned `seed/*.csv` files are committed. Write `seed/convert_services.py`. It reads the CSV and writes `seed/service_offer.csv`, which the APP_SPEC_01 seed loader loads. Never type a number into code. When a new export arrives, re-run the converter and the loader, and nothing else changes.

**New seed table `service_offer`** (SQLAlchemy model, like the others in spec 01):

| Column | From services.csv | Notes |
|---|---|---|
| `offer_id` | `id` | |
| `institution_id` | `bank` → institution by code | Only the 9 demo banks |
| `category` | `category` | deposit · card · loan · account_fee |
| `product` | `product` | Bank's own product name, shown as is |
| `product_type` | derived | fdr · dps · savings · card · home_loan · auto_loan · personal_loan · loan_against_fdr · account_fee (map by keywords in `product`; keep the map in `seed/product_type_map.csv`, not in code) |
| `network`, `tier` | `network`, `tier` | Cards only |
| `tenor_months` | derived from `product` / `condition` | e.g. "12 Months", "1 (One) Year" → 12 |
| `attribute` | `attribute` | rate · rate_min · rate_max · interest_rate · annual_fee · renewal_fee · late_fee · foreign_currency_markup · … |
| `value_num` | `value` | Number only. If the value is text ("IR of Security + up to 3%"), `value_num` is null and the app shows `value_text` |
| `value_text` | `value` | Always kept, as printed |
| `unit` | `unit` | bdt · pct_year · text |
| `condition` | `condition` | Shown in small text under the value (slab, "plus 15% VAT", "1st year") |
| `basis` | `basis` | conventional · islamic |
| `doc_date` | `doc_date` | |
| `stale` | `condition` contains "stale", or `doc_date` older than 12 months | |
| `source_url`, `page`, `quote`, `column_header` | same | For the Source sheet |
| `hidden` | from `seed/services_hidden.csv` | See below |
| `checked_by`, `checked_on` | `agent-v5.4` and the export date | Sumon changes to his name after a hand-check; then the "যাচাই করা হয়েছে" (checked) mark shows |

**Hide list, `seed/services_hidden.csv`** (bank, category, product_type, tier, reason). Current review holds:
- CITYBANK, deposit, fdr, *: "12M 7.00 vs 5.75, waiting for Sumon's check (v5.2 S4)"
- PRIMEBANK, card, card, Signature: "Signature ZERO free: conditions not yet checked (v5.3 N1)". Remove this line once Sumon has checked.

**Several cards in one tier** (v5.3 N2; BRAC has Platinum, Platinum Flexi, TARA Platinum and others). Add `variant` to `service_offer`:
- `main`: `column_header` equals the tier name (the English part, if the header is bilingual, e.g. "ভিসা প্লাটিনাম Platinum"), or is the only retail card for that bank + network + tier. If no header matches exactly (EBL's Signature tier has "Signature Light / Women Signature" and "Signature Exclusive"), `main` is the first of them in the bank's own header order (`col_num`), which is the entry-level card.
- `variant`: any other retail card in that tier (e.g. "Platinum Flexi", "Gold Flexi", "TARA World", "Women Platinum").
- `excluded`: corporate cards ("Corporate" in the name), cards limited to one group ("Defense", "Army", "Payroll" in the name), and foreign-currency cards (value in US$ or "RFCD", "ERQ" or "FX" in the name). These are kept and shown in S3, but never in a retail comparison.
- A value of "নোট ১৭ অনুযায়ী" (as per note 17) or similar is text, not a number: show it as printed in S3 only, never in a comparison.

S2 shows the `main` row for each bank. Under it, a small "আরও {n}টি সংস্করণ" (n more versions) opens the variants, each with its printed name and fee. The savings line uses `main` rows only.

**Use the printed card name.** Show `column_header` as the card's name (e.g. "Signature ‘ZERO’"), not just the tier. The network is inferred by the agent, so use it only as a filter.

A hidden row is loaded but never shown. In its place the bank shows "তথ্য যাচাই হচ্ছে" (data being checked). When Sumon clears an item, delete the line and re-run the loader.

**Missing data:** if a bank has no row for that product, show "প্রকাশিত নয়" (not published) for DBBL deposits, and "তথ্য নেই" (no data) for everything else. Never estimate.

## 2. S1 Services home

- Teal stage at the top: title "ব্যাংক সেবা", with the subtitle "একই সেবা, কোথায় খরচ কম?" (Same service, where does it cost less?).
- A search box plus a small mic (APP_SPEC_02 voice). Spoken or typed text goes to the intent call (spec 04, 2a) with `tab = services`. If it finds product + tenor/tier, open S2 directly. Example: "সিগনেচার কার্ডের ফি" opens S2 for Visa Signature.
- Four large tiles on the ivory sheet, each with an icon and one line:
  - **জমা ও সঞ্চয়** (Deposits and savings): FDR, DPS, savings
  - **কার্ড** (Cards): credit card fees and rates
  - **ঋণ** (Loans): home, car, personal, loan against FDR
  - **অ্যাকাউন্টের খরচ** (Account charges): maintenance, debit card, SMS, cheque book
- Tapping a tile opens S2 with that category's most common choice already selected:
  - Deposits: FDR 12 months
  - Cards: Visa Gold
  - Loans: home loan
  - Account charges: savings account maintenance
- One line at the bottom: "৯টি ব্যাংকের প্রকাশিত হার ও ফি। তারিখ প্রতিটি সংখ্যার পাশে।" (Published rates and fees of 9 banks. The date is next to every number.)

## 3. S2 Compare

**Top:** selector chips for the choice:
- Deposits: product (FDR · DPS · সঞ্চয়ী হিসাব (savings)), then tenor (3 · 6 · 12 · 24 · 36 months)
- Cards: network (Visa · Mastercard · Amex), then tier (Classic · Gold · Platinum · Signature · World · Infinite, showing only tiers that exist in the data)
- Loans: type, plus fixed amount examples and term for the installment calculator
- Account charges: item

**List:** one row per bank (all 9, always). Each row shows:
- The bank's Bangla name, with English underneath
- The main number, large:
  - FD/DPS/savings: rate per year
  - card: annual fee in taka
  - loan: declared rate, with "সর্বনিম্ন–সর্বোচ্চ" (lowest–highest) underneath
  - account charge: the fee
- `condition` in small text (e.g. "১ কোটির কম", "+১৫% ভ্যাট")
- The document date. If `stale`, add a grey chip "পুরনো তথ্য" (old data).
- The bank's status chip from the Bank tab (mark + word, same as B1). This is ILMA's special angle: a high FD rate means less if the bank is weak, so the saver sees both.
- "সূত্র ›" → Source sheet (same as spec 03: title, page, quote with the number highlighted, "উৎস খুলুন").
- Rows with no data, hidden rows, or "প্রকাশিত নয়" go at the bottom, muted.

**Sorting:** by the main number. For deposits, highest rate first; for cards, loans and account charges, lowest cost first. Show the sort in words above the list: "বেশি হার আগে" (higher rate first) or "কম খরচ আগে" (lower cost first). This is a sort by a published number, not a ranking of banks. Never use words like "সেরা" (best) or "সবচেয়ে ভালো ব্যাংক" (best bank).

**Savings line** (the money-saving story, computed by code from the two rows, never by a model):
- Cards: "{bank A}-এর ফি {bank B}-এর চেয়ে বছরে {diff} টাকা কম" (Bank A's fee is Tk {diff} a year less than Bank B's). Compare the cheapest and most expensive shown rows that are not stale. If renewal fees exist, use them for year 2 onwards, and show "৩ বছরে মোট" (total over 3 years) as year-1 fee + 2 × renewal fee.
- Deposits: a fixed-example selector (default ১,০০,০০০). Show "{tenor} মাসে সুদ" (interest over {tenor} months) per bank = amount × rate × months / 12, simple interest, before tax. Label it "আনুমানিক, কর কাটার আগে" (estimate, before tax).
- Loans: fixed amount examples and a term box. Show the monthly installment (standard EMI formula) at the declared rate, labelled "আনুমানিক কিস্তি" (estimated installment).
- All calculations run on the phone. Amounts are never sent to the server and never stored (same rule as the insurance split calculator).

**Insurance line** under deposit lists: "প্রতি ব্যাংকে জমাকারী প্রতি ২ লাখ টাকা পর্যন্ত বিমা সুরক্ষিত" (insured up to Tk 2 lakh per depositor per bank), from the `insurance_rule` table with its source.

**Islamic banks:** label rows with `basis = islamic` "মুনাফার হার (আনুমানিক)" (profit rate, provisional) instead of "সুদের হার" (interest rate). Use the same comparison screen with that label, under a separate Islamic basis filter; never mix bases.

## 4. S3 Offer detail

Opened by tapping a bank row in S2, or from the Bank tab B2 row "এই ব্যাংকের সেবা ও হার" (filtered to that bank).

- The bank's name and status chip, then the product name as the bank prints it.
- Every attribute for that product as a row: label in Bangla, value, condition, date and "সূত্র ›". For a card: annual fee, renewal fee, interest rate, late fee, cash advance fee, foreign currency markup, replacement fee, supplementary card fee, lounge access, fee waiver rule.
- A muted line at the bottom: "ব্যাংকের প্রকাশিত তালিকা থেকে। আবেদন করার আগে ব্যাংকের সাথে নিশ্চিত হোন।" (From the bank's published schedule. Confirm with the bank before applying.)
- A button "এই ব্যাংকের অবস্থা দেখুন" (See this bank's condition) → B2.

**Bank view** (from B2): all categories for one bank, grouped, each row opening S3.

## 5. S4 Ask about services

The Ask screen, with `tab = services` sent with every question. It uses `/v1/ask` and the spec 04 checks: Muse Spark answers only from `service_offer` facts, every number must appear in a cited fact, and with no facts it gives "এই তথ্য আমাদের কাছে নেই।" (we don't have this information).

Suggestion chips:
- "কোন ব্যাংকে ১ বছরের এফডিআর-এ হার বেশি?" (Which bank has a higher 1-year FDR rate?)
- "সিগনেচার কার্ডের বার্ষিক ফি কোথায় কম?" (Where is the Signature card annual fee lower?)
- "২০ লাখ টাকার গৃহঋণে মাসিক কিস্তি কত?" (What is the monthly installment on a Tk 20 lakh home loan?)

When the answer is a comparison, also show a "তুলনা দেখুন" (see comparison) button that opens S2 with the same choice. The model never invents a value, and never says which bank to choose.

## 6. API (adds to spec 01)

| Route | Returns |
|---|---|
| `GET /v1/services/categories` | Categories with the choices that exist in data (product types, tenors, networks, tiers) |
| `GET /v1/services/compare?product_type=&tenor_months=&network=&tier=&attribute=` | One row per demo bank: value, condition, doc_date, stale, hidden/missing state, status chip, source fields. Sorted per section 3. |
| `GET /v1/institutions/{id}/services` | All non-hidden `service_offer` rows for one bank, grouped by category and product |
| `GET /v1/services/offers/{offer_id}` | One row with full source fields |

The server never takes an amount. All calculators run in the app.

## 7. Accessibility and states

- TalkBack on S2 reads the choice first, then each row: "{bank}, {value}, {date}". For example: "ইস্টার্ন ব্যাংক, বার্ষিক ফি সাত হাজার টাকা, অক্টোবর ২০২৬" (Eastern Bank, annual fee seven thousand taka, October 2026).
- "শুনুন" (Listen) on S2 reads the savings line and the first 3 rows.
- Numbers use Bangla digits in Bangla mode and Western digits in English mode.
- Test at 360×640 with text at 200%; nothing may be cut off.
- Loading, offline and empty states as in spec 03, section 6.

## 8. Tests

`tests/test_services_seed.py`:
1. The converter run on the v5.4 `services.csv` loads 606 rows, all with source_url, page and quote.
2. Every `value_num` appears in its `quote` (same as the agent's check, repeated on our side).
3. The compare query for Visa Signature annual_fee returns NCC 7,000, Bank Asia 7,000, EBL 10,000 ("Signature Light / Women Signature" as main, "Signature Exclusive" 12,000 as variant), BRAC 10,000, MTB 12,000 and DBBL 20,000 (stale), with Prime "Signature ‘ZERO’" hidden until Sumon clears it (then Free = 0). The query for Visa Platinum returns BRAC's main row 5,000, with 2 retail variants (Platinum Flexi 3,000, TARA Platinum 2,500); Corporate, RFCD and ERQ are excluded.
4. The compare query for FDR 12 months returns City as hidden, DBBL as "প্রকাশিত নয়", and EBL plain FD 6.50.
5. A hidden row never appears in any API response.
6. Stale rows are shown in the list but left out of the savings line. So the Visa Signature savings line compares NCC/Bank Asia (7,000) with MTB (12,000): Tk 5,000 a year. DBBL (20,000, stale) is not used.

## 9. Done when

1. `pytest` passes: spec 01 tests plus `test_services_seed.py`.
2. On a phone at app.sumon.me: Bank services → কার্ড → Visa → Signature shows the list, with the savings line, and every fee opens a Source sheet whose quote contains that number.
3. Voice: say "সিগনেচার কার্ডের ফি" on S1 and S2 opens for Visa Signature.
4. From the Bank tab, EBL → "এই ব্যাংকের সেবা ও হার" opens EBL's bank view.
5. Screenshots of S1, S2 (FDR 12M, Visa Signature, home loan), S3 (one card) and the Source sheet, pushed to branch `screen/bank-services`.

## 10. When later data arrives

- **Later services export:** re-run `convert_services.py` and the loader. Remove items from `services_hidden.csv` only after manual review and Sumon's approval.
- **v6 incidents export:** loads into dedicated incident/source/history tables for the Bank tab's History (spec 03, B3-History). Bank services is not affected.
