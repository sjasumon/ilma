# Deposits and savings

FDR, DPS and savings interest use a source-linked catalog with audience separation. The five groups are general, women, senior, students/children and non-residents. `seed/deposit_audience.csv` records the mapping. MTB Inspire remains general because its supplied quote describes balance slabs, not an exclusive audience. No eligibility is inferred from a product name alone.

The catalog provides fresh readable facts, all published terms, amount bounds, minimum installments and secondary schemes. City FDR rows are included when visible in the active database; the preview currently includes its 12-month 7% rate. Hidden seed rows stay hidden until separately reviewed. Missing, stale and unreadable facts are omitted under the current display rule. No placeholder is ranked as a bank offer.

The plain EBL fixed deposit is the primary FDR; Extra Value remains a separate product. Target schemes are secondary, with Double Benefit classified as a lump-sum FDR. An unparsed DPS term is never included in a comparison. Ranges expand by published years, while discrete lists stay discrete. Quotes and original product wording remain available through source sheets.

Amounts and terms are editable under the owner's browser-memory authorization. Neither input changes requests, URLs, storage or analytics. `/v1/services/deposits` returns the complete public catalog and rejects amount, balance and term fields; changing term or audience filters locally. The compatible comparison endpoint also supports an explicit audience filter. No schema migration or shared database reload is required.

FDR estimates use simple interest. DPS estimates use beginning-of-month installments with monthly compounding; bank calculation rules may differ. Rounding occurs only for display. Minimum installments and documented multiples apply locally. Printed amount boundaries are honored, including strict upper bounds. Savings interest is calculated only inside a published slab; an unknown gap is not interpolated. Savings appears within the account view, alongside separately source-labelled account fee references. Those references do not assert that every fee applies to the selected savings product.

Risk labels are shown on every tile; unverified and high-risk deposit banks also retain a warning. Earnings comparisons identify the leading bank's risk when applicable. Deposit protection text comes from the sourced insurance rule, is conditional, combines accounts at the same bank, and warns when the example exceeds the limit. No tax percentage is invented.

There are fourteen fixed-example narration slots: six FDR terms, three DPS terms, general savings and four audience examples. Code builds public fact sheets, model drafting is checked, and unsuitable candidates fall back to deterministic source-bound text. Text approval is required before paid offline recording. Runtime lookup verifies source, text and audio hashes and never calls a speech provider. Unsupported narration combinations hide Listen; approved audio is not yet available for these slots.

Browser acceptance covers Small/Extra large, portrait/rotation, keyboard-height resize, desktop and 200% text, plus zero edit requests and storage. Physical Note 20, screen-reader and native audio acceptance remain separate release requirements.
