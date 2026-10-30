# Loan comparison

Four loan types use source-linked declared rates, published ranges, fee scopes and FDR margins. Calculations use monthly amortization; rounding occurs only for display. A range never supplies an invented declared rate. A quoted midpoint may supply a declared rate, with derived bounds explicitly marked. Formula margins are added in percentage points; a floor or ceiling remains a bound in the example calculation.

The default examples are home BDT 2,000,000 / 20 years, auto BDT 1,000,000 / 5 years, personal BDT 500,000 / 3 years and FDR-backed BDT 500,000 / 1 year. Amounts and years may be edited under explicit project-owner authorization. They remain in browser memory: no requests, URL parameters, persistence or analytics carry them. Changing type resets its example. Comparison and readout endpoints reject borrower amount and loan-term fields.

Fee scopes are maintained in `seed/loan_fee_scope.csv`. Processing, settlement and partial-payment percentages apply once. Caps, slabs and documented VAT remain source-specific. Professional-loan fees are separate from general retail loans. A strict below/above boundary is not converted into an inclusive boundary without source evidence.

Freshness and readable evidence govern inclusion. Stale or unreadable facts are omitted, without missing-data filler. NCC's January 2025 fee schedule is excluded from the current comparison; it is not assigned a newer date. Prime and Dutch-Bangla stale loan rates are excluded. Bank Asia's published declared rates remain visible without an invented range. Existing BRAC and City numeric FDR-backed rates remain numeric rather than being converted into invented margins.

Saved narration uses only fixed-default public facts and a source fingerprint. Runtime readout performs no provider synthesis. Changed calculations do not change the spoken default example, which is labelled beneath the Listen button. Four narration texts require review before offline recording; until approved audio is available, the interface exposes the text and an explicit audio-unavailable state. Card recordings and bank-report review are separate.

The source CSV normalizes one-time units and three quote-supported MTB midpoints. The API also normalizes legacy database rows on read. Preview rollout does not reload the shared database; a persisted migration remains a separate release step.

Validation covers source evidence, fee scope/caps/slabs, stable EMI mathematics, hidden and stale exclusion, FDR bounds, request rejection, zero runtime provider calls and browser-only calculations. Browser automation covers Small/Extra large, rotation, keyboard-height viewport, desktop and 200% text. Actual Note 20 listening and accessibility acceptance remain outstanding.
