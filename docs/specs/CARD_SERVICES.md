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

The dry run contains seven Bangla clips totalling 4,790 characters, individually 608–750 characters after number pronunciation. Full texts are in [CARD_AUDIO_DRY_RUN.md](CARD_AUDIO_DRY_RUN.md). After Sumon authorized generation, seven MP3 drafts were created outside the published tree. All decode successfully and have non-silent peaks below clipping. Measured durations are 53.16–70.43 seconds; four exceed the approximate 60-second target. No extra paid regeneration was attempted. The public service manifest remains empty pending actual listening review, in line with the approved-manifest pattern. Sub-second phone playback has not been established.

Automated checks cover grouping, plain conditions, selected-fact ordering, fresh-before-stale behavior, source retention, non-comparable cash units, no runtime provider calls, reviewed-file integrity, unchanged generation skipping and text-size persistence. Browser checks cover Small/Extra large at 360 pixels, rotation, keyboard-sized viewport, desktop, source dialogs, six-cell tiles and the four detail sections. A synthetic player verifies synchronous play and visible failure states. Physical Note 20 and screen-reader acceptance remain for Sumon; no claim of device acceptance is made.

Release regression checks: 472 Python tests and 27 subtests passed; all seven documented frontend suites passed. Browser checks used the actual read-only ilma data. The real generated MP3 files decode successfully, but automated decoding is not native listening acceptance.
