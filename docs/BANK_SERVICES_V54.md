# Bank services v5.4 — 27 October 2026

The owner supplied the updated Bank services specification and v5.4 archive.
Only its services data is refreshed. Existing financial figures, insurance,
ratings, news, incident history and status thresholds are retained. Bank service
comparisons cover the original nine banks; the Bank tab also has two incident
supplement banks. No services are invented for those two banks.

The private original archive and collection metadata remain outside Git. The
converter produces 606 normalized service attributes: 581 visible, 25 withheld.
Rows are labelled `agent-v5.4`, not personally verified by Sumon. The public
specification uses neutral review terminology and records the fixed-example
calculator rule from the website review.

## Card comparisons

- `variant=main` uses the exact printed tier header when available, otherwise
  the earliest eligible bank source column. Selection never uses lowest fee.
- Other retail versions expand beneath the main row with printed header names,
  fees, dates and individual source sheets. Three-year totals and the savings
  story use only the main card and its own renewal fee.
- Corporate, personnel/payroll/co-branded group cards and foreign-currency cards
  are `excluded` from retail comparisons. They remain inspectable in the bank's
  services/detail views. Text-only note references never become numeric fees.
- Comma-separated amounts are normalized numerically. A printed `Free` is an
  explicit semantic zero with the original word/quote preserved, not a claim
  that a literal zero was printed. No other text is turned into a number.
- Prime Signature ZERO remains hidden pending review. City FDR remains hidden.
  Thirteen unreadable quotes and six unsupported derived loan endpoints are
  also withheld. Hidden rows never appear in public offer payloads.

Visa Signature main fees are NCC/Bank Asia 7,000; EBL/BRAC 10,000; MTB 12,000;
DBBL 20,000 marked stale. EBL Exclusive 12,000 is a variant. The fresh main-card
savings difference is 5,000. BRAC Platinum uses 5,000, with Flexi 3,000 and TARA
2,500 as its two retail variants. These are sourced schedules, not advice or
bank rankings; conditions and source dates must be checked before applying.

The existing teal/gold theme is preserved. S1 adds an explicit service mic.
Deposit/loan examples remain fixed and calculated on the device; no amount is
accepted by comparison/readout APIs. Islamic basis stays a separate filter.
The deposit insurance explanation links to the existing official legal source.

## Refresh and acceptance

```sh
# Point to a private, locally unpacked CSV directory.
EXPORT_DIR=/PRIVATE/seed-input /path/to/venv/bin/python seed/convert_services.py
PYTHONPATH=api /path/to/venv/bin/python -m ilma_api.seed_loader seed
PYTHONPATH=api /path/to/venv/bin/python tests/check_services_v54.py --base-url http://localhost:8001
```

A non-destructive MySQL migration adds `service_offer.variant`. The seed loader
rejects databases other than `ilma`, replaces only managed service rows for the
original banks, and retains unchanged personal source reviews. Back up before
importing. Removing a manual hold requires the owner's actual review/approval.

Automated checks cover exact main/variant values, exclusions, notes, source
quotes, hidden endpoints, stale savings, idempotence, voice intent/navigation,
BN/EN views and small-screen text enlargement. Physical microphone utterances,
TalkBack/VoiceOver with target users and final manual source review remain
separate acceptance work.

## Measured release checks

85 pytest tests / 25 subtests and five frontend suites pass. Fresh MySQL import
succeeded after a private backup; the `ilma` service reports release
`services-v5.4-2026-10-27`. Live BN/EN browser checks passed main/variant values,
source quote identity, hidden/excluded states, bank-specific services and 200%
text. The catalogue smoke checks passed S1/S2/S3, nine service comparison rows,
rotation, keyboard resize, desktop and local calculator/no-request behavior.
The existing eleven-bank catalogue and two High cards remain available.

A live Meta typed query “সিগনেচার কার্ডের ফি” returned a Visa Signature annual-fee
comparison with three database sources. This verifies typed intent/navigation;
it does not establish microphone transcription accuracy. A cold live browser
context reached network idle in 1.19 seconds with 13 requests, zero external
requests and no runtime/console errors. Security headers remain strict. Asset
version 35 invalidates prior shell caches. Screenshots are in
`design/reviews/bank-services/`, including the expanded Platinum variants.
