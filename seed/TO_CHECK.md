# Sumon's checks before the demo

Nothing on this list has been marked as a completed personal review.

1. **NCC CRAR 15.54%:** confirm the 2025 column in the five-year table, annual
   report page 183. The quoted table is preserved in `fact.csv`.
2. **Prime and City CRAB AAA:** the export gives 17 June 2026, the same date as
   EBL. Opened each supplied source once: [City](https://www.dse.com.bd/company/CITYBANK),
   [Prime](https://www.dse.com.bd/company/PRIMEBANK),
   [EBL](https://www.dse.com.bd/company/EBL). These pages returned a generic
   client-rendered market page in the browser tool; this did not verify the
   rating text. Check the actual disclosures before assigning your name.
3. **MTB group accounts:** the supplied figures are consolidated; health rows
   explicitly show “গ্রুপ হিসাব / Group accounts”. Others retain their supplied
   solo/unknown basis. Check the nine Bangla bank-name spellings too.
4. **Three required service exclusions:** BRAC cards, Prime cards, City FDR.
   Do not remove `services_hidden.csv` entries without the specified review and
   Sumon's OK. The app exposes only “data being checked” placeholders.
5. **Additional source issues:** 13 rows have `quote_unreadable`; six MTB loan
   endpoints (services 2158–2163) are derived from a printed mid-rate ±1%, not
   literally quoted endpoints. All remain loaded but withheld. Service 2024
   gives zero with a “Free” quote and is retained as text, not used as a numeric
   calculation operand. The split comma in service 2190 (“6 ,000”) is normalized
   for evidence checking without changing the original quote.
6. **Unknown publication dates/pages:** `documents.csv` does not provide
   publication dates. Entity rating rows have blank page numbers. These are
   shown as unknown; fetch timestamps have not been relabelled as publication.
7. **Official insurance source:** no official insurance-rule source is supplied
   in this export. Provide the source before enabling the deposit insurance
   line. The old hard-coded calculator is hidden from the new services UI.
8. **History/news:** v6 incidents and its search window have not been supplied.
   The history page says it was not checked. Newspaper titles remain in their
   original language and are labelled reported/unconfirmed; no article bodies
   or invented translations are shown.
