# Card services and readable text

Implemented for preview review on 30 October 2026. Production deployment waits for Sumon's phone acceptance. Deposits and loans retain their existing views; account service labels are renamed while the internal `account_fee` key stays unchanged.

## Text size

Settings offers Small (14), Medium (16), Large (19), and Extra large (22). The `--fs` root variable drives data-screen typography; `ilma.textSize` persists the choice. A hash-authorized initializer applies it before stylesheet paint and handles unavailable storage. Home orb captions retain their own size. Touch controls remain at least 48 pixels tall. Meta text, titles and values use relative scales.

## Card facts and source boundaries

A shared computed `card_key` joins bank, network, tier and cleaned printed name. Both conversion and runtime views use it, so existing imported data needs no schema migration or source rewriting. Original bilingual column headings and quotes stay in source records. Printed variants such as Gold Flexi remain distinct.

The compare API accepts `compare_by` (annual fee by default) and returns all ten fact slots for each card, with null for missing facts. Each available fact retains its own value, unit, document date, stale marker and source. Hidden offers stay hidden. Fresh facts precede stale ones. Percentage-only cash fees sort separately from taka amounts; they are never treated as taka.

Card tiles show the selected fact and six source-linked fact cells. Unknown bank condition uses the grey unverified label, without the deposit-rate warning. Unpublished tiers are explicit. Four detail sections include renewal, waiver, supplementary, interest, late, cash, markup, replacement and lounge facts. Three-year fee totals require fresh annual and renewal values. The bank-services view groups individual cards by network.

Bangla condition wording is deterministic, using the first matching row in `seed/condition_bn_map.csv`. Unmatched conditions have no invented explanation; full original wording remains in the source sheet. Fee-waiver values and percentages stored as text are handled without changing source values.

## Saved comparison narration

`/v1/services/readout` returns saved reviewed audio and the code-built text, or null audio with text. It makes no TTS or model request. The card comparison response includes the same readout so the tap handler need not await a server request.

The services tab loads the public clip manifest. A Listen tap synchronously sets the source and calls `play()` during that handler. The narration is visible. Missing clips and playback rejection show a visible fallback. Saved service clip URLs are narrowly allowed by the audio player and cached by the service worker.

The offline build tool supports dry run, explicit generation, and publication of unchanged reviewed files. Generated drafts remain outside the published tree. Each clip requires matching text and audio hashes plus actual review metadata before runtime playback. Unchanged text and voice skip regeneration. Source data changes invalidate incompatible narration.

## Current acceptance status

The initial compressed drafts totalled 4,790 characters; seven private MP3 drafts were generated after authorization, but user feedback rejected their clarity. They are not approved for activation. The revised narration uses complete sentences, explicit currency units, bank-specific percentage/floor combinations, ATM context and accurate free-card counts. It removes the unsupported universal promise of no interest after full payment and limits VAT statements to documented conditions.

The revised dry run has seven texts and 8,427 characters, individually 995–1,404 characters after pronunciation. Full texts are in [CARD_AUDIO_DRY_RUN.md](CARD_AUDIO_DRY_RUN.md). This exceeds the earlier 500–750-character summary target to address the later completeness feedback. The user authorized regeneration of all seven revised texts. The new private MP3 drafts decode and match the planned text hashes; measured duration is 83.57–123.09 seconds. They are longer than the original summary target. Native listening and phone playback are not certified. The builder keeps the old 750-character spending limit by default: longer generation requires an explicit reviewed `--max-characters` limit. `--key` allows one sample before regenerating the whole set. The user explicitly authorized activation of version two on preview for listening. Seven source/hash/decoding-checked clips are published. Manifest metadata records technical checks and that authorization separately from `native_listening_reviewed: false`; no native listening or production acceptance is claimed.

Automated checks cover grouping, plain conditions, selected-fact ordering, fresh-before-stale behavior, source retention, non-comparable cash units, no runtime provider calls, reviewed-file integrity, unchanged generation skipping and text-size persistence. Browser checks cover Small/Extra large at 360 pixels, rotation, keyboard-sized viewport, desktop, source dialogs, six-cell tiles and the four detail sections. A synthetic player verifies synchronous play and visible failure states. Physical Note 20 and screen-reader acceptance remain for Sumon; no claim of device acceptance is made.

The earlier release passed regression and browser checks. Revised wording checks cover cash units, fee ties, non-repeated late fees and one-versus-two free-card conditions. Earlier MP3 decode checks are not acceptance of the revised narration or native listening quality.

Revised wording regression: 479 Python tests and 27 subtests passed, along with all seven documented frontend suites. Paid generation was limited to the seven explicitly authorized revised clips; no runtime provider generation was introduced.

## Selected-cost reader

The card comparison now uses one native dropdown for the five cost options. The automatic cheapest-versus-most-expensive bank callout is removed. A selected-cost article is visible immediately, without pressing Listen. It has separate meaning, coverage, bank-by-bank, old-data and missing-data sections, with short bank names, localized amounts/dates and individually labelled source buttons. The article changes with `compare_by` in both Bangla and English. Cash explanations retain higher-of percentage/currency conditions and known ATM context. Different source dates for annual-fee waiver or renewal conditions are explicit.

Each saved recording is now keyed by network, tier and selected cost. Its complete spoken text covers that cost’s meaning, available range when units are comparable, every fresh bank’s published amount, conditions and dates, status coverage and missing-data limits. Old prices are not spoken as current facts. The exact pronounced recording text appears in separate paragraphs in the transcript disclosure. Selecting another cost stops playback and preserves keyboard focus. An overview or another cost’s clip is never used as fallback. Recordings require a reviewed dry run and explicit credit authorization before offline generation; runtime still makes no provider calls. Four Mastercard Titanium options have fewer than two fresh-bank facts and therefore no comparison recording; their available text and explicit missing-audio state remain visible.

## Approved verbatim selected-cost release — pending completion

The later explicitly approved 31-script JSON supersedes the seven-overview V3 draft for this release. Recordings use network + tier + cost keys. Approved text is sent unchanged to speech generation and returned unchanged for on-screen playback; deterministic draft wording and `pronounce()` do not alter it. Numbered account fallback is shared with both runtime speech paths. The first batch completed six recordings and stopped after all three accounts timed out on the next clip. The manifest marks this partial state; twenty-five clips and preview release acceptance remain pending. No production deployment or native listening acceptance is claimed.
