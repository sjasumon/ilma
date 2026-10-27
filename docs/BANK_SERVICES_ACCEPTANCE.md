# Bank and Bank Services — implementation record

Authority: [bank specification](specs/APP_SPEC_03_bank_tab.md) and
[service specification](specs/APP_SPEC_05_bank_services.md).
Input: Sumon's private v5.2 CSV export. Runtime database: **ilma**.

## Implemented

- B1: nine-bank list, Bangla alphabetical sorting, name search, microphone,
  mark-and-word status chips and a prior-work/source note.
- B2: plan-A report, up to three sourced reasons, data/updated dates, no seven
  health-check block or synthetic median; explicit unverified-regulator note.
- B3: sourced health with available 2024 figures and MTB group label, ratings
  with expiry, linked reported/unconfirmed headlines, honest unavailable history,
  bank-scoped typed/voice questions and service links.
- Watch selections persist in MySQL under a salted anonymous device identifier.
  Notifications are explicitly not yet available.
- S1/S2/S3: four categories, same-product/tenor/network/tier/basis comparison,
  all nine rows, hidden/missing/not-published states, source sheets, document dates,
  stale labels, status chips, bank-filtered offers and all visible attributes.
- S4: services context, sourced response templates and comparison navigation.
  Personal amount/term prefills remain transient; comparison/calculator requests
  do not contain personal amounts. Server rejects amount query/body fields.
  The legacy amount-taking calculator HTTP routes are removed; old pure
  calculation helpers remain only for regression fixtures.
- Savings difference, three-year totals where renewal data exists, simple
  deposit interest and standard EMI run in the browser. Stale offers are excluded
  from savings/three-year calculations. Listen uses source-backed comparison
  data without accepting the user's calculator amount.
- Public GET caching covers lists/details/comparisons; private watch requests
  and voice POSTs are never cached. Loading, retry and no-data states are present.

## Evidence

- 64 pytest checks and the five existing Node suites pass. Converter repeat
  loading, duplicate-fact rollback, unrelated-database rejection, hidden-offer
  exclusion, like-for-like matching, stale savings exclusion and private watch
  persistence are covered.
- Transactional host import: 9 institutions, 43 facts, 9 ratings, 5 linked
  headlines and all 470 service attributes. Existing voice diagnostics preserved.
- Baseline test: 8 strong, SBAC no_data; thresholds unchanged.
- Live health reports `export-v5.2-2026-10-27`, bank and voice tables ready.
- Live Signature comparison: NCC and Bank Asia 7,000, MTB 12,000, DBBL 20,000
  stale, BRAC checking, Prime missing; fresh savings difference 5,000.
- Live FDR 12M: EBL plain FD 6.50, City checking, DBBL not published.
- Live comparison Listen returned generated MP3 audio successfully. This is not
  a native-speaker pronunciation sign-off.
- Live typed “সিগনেচার কার্ডের ফি” returned a service answer with Visa/Signature
  navigation. A synthetic WebM “ইস্টার্ন ব্যাংক” traversed Meta and opened EBL
  in 2.54s. The synthetic Bangla Signature recording was rejected in 2.48s.
  Subsequent retained-transcript analysis identified a local validation bug:
  shared Bangla danda punctuation was mistaken for Devanagari script. Both saved
  script-mismatch cases contained valid Bangla punctuation, not Devanagari letters.
  After correction, replaying their stored transcripts through current intent/data
  returned `service_answer` and `report_card`. This is transcript replay evidence,
  not a new microphone-to-answer accuracy benchmark. Real phone checks remain.
- Browser checks on the public host at 360×640: B1/B2/B3, source sheets, S1/S2/S3,
  nine comparison rows, correct savings line, no request when calculator inputs
  change, and no horizontal overflow with emulated 200% text on bank list,
  report, health, rating, source sheet, services home, comparison and offer
  detail in both Bangla and English (16 cases), plus the loan calculator screen.
  Physical TalkBack/VoiceOver review is still required.

## Review gaps

See [seed/TO_CHECK.md](../seed/TO_CHECK.md). Imported rows are agent-labelled,
not personally checked by Sumon. Unknown publication dates are not invented.
87 service rows are withheld (mandatory hide rules plus unreadable/unproven
quotes). Insurance needs an official source; v6 incident history needs input.

Screenshots: [Bank tab](../design/reviews/bank-tab/) and
[Bank services](../design/reviews/bank-services/). Reproduce with:

```sh
PYTHONPATH=api /home/ubuntu/venv/bin/python -m pytest -q
/home/ubuntu/venv/bin/python tests/check_catalog_browser.py --base-url https://app.sumon.me
```

Install `requirements-dev.txt` and Playwright Chromium to run browser checks on
a new host. The source conversion and reload workflow is in [seed/README.md](../seed/README.md).
