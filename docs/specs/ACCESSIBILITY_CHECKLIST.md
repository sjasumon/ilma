# ILMA design: build-ready checklist (26 Oct 2026)

> **Updated 26 Oct, 09:15 UTC:** Home and the theme are settled (teal, see S-01 and §2). D1, D2 and D4 are answered. Where the four bottom tabs put each FRD screen is still open: (private planning reference omitted)

For whoever builds the app tonight. Where this file and the FRD (`ILma.md`) disagree on looks, motion or copy, **this file wins** until the FRD is updated. The FRD still wins on rules, data, privacy and status logic.

Visual references, in order of authority:
1. Teal Home: (private planning reference omitted) (code: `design/home-options/ilma_home_teal_prototype.html`)
2. Clay-bank prototype (layout of Start, Listening, Report, Source sheet; it is still navy, so swap in the teal tokens): (private planning reference omitted)
3. Tokens: [tokens.css](../tokens.css). Mascot: `design/ilma-character/claybank.png` (883×1059, transparent).

**Do not use:** the older design brief Parts 0–2, 4–5 (white theme), FRD §20.1/§20.4–20.6 colours and components, the grandma images (`nani_*.png`), the older prototype HABy7pf9….

Status key: ✅ ready · ⚠️ ready once Sumon decides (see the end) · 🔧 build from tokens, no mock needed

## 1. Screens for the demo slice

| Screen | State | Notes |
|---|---|---|
| S-00 Start | ✅ | Teal stage. "হ্যালো, আমি ইলমা", tagline "আপনার সঞ্চয়ের বিশ্বস্ত সাথী", clay bank centre with soft gold halo, three question bubbles (static), mic line, ivory bottom bar "চলুন শুরু করি →". Privacy line. Shown once per install. |
| S-01 Home | ✅ | Teal gradient. Animated glass orb with gold-to-cyan dotted waves (calm when idle, moves with the voice while listening). **The whole screen above the bar is the tap target.** Line "কথা বলতে যেকোনো জায়গায় ট্যাপ করুন" / "Tap anywhere to speak", plus one rotating example line. English pill top right. Bottom glass bar: হোম · আমার সঞ্চয় · জিজ্ঞাসা · সেটিংস, **no centre mic**. Nothing else: no search, My banks, news bar or mascot. |
| S-02 Listening | ✅ | Same teal screen; the orb waves react to the voice (replaces the 3 rings). "শুনছি…" then "ইলমা খুঁজে দেখছেন…", recognised words large in Tiro Bangla, outline "থামুন". Start and stop tones + 30 ms vibration. |
| S-04 Report card | ✅ | Teal hero (status words on a `--stage-lo` area, see §2): back / হোম, bank name (Tiro 29), meta line with data date, status mark + word (Tiro 42), one-line meaning, 3-step scale ভালো · সতর্ক · ঝুঁকি বেশি with marker. Ivory sheet: shield + insurance line, "কেন?", 3 reasons each with blue "সূত্র ›", শুনুন (solid #1E4542) + নজরে রাখুন (outline), not-advice note. **No mascot, no gold** on this screen. |
| Source sheet | ✅ | Ivory bottom sheet over scrim: source title, document box with the quoted sentence highlighted (#FFE29A), বন্ধ করুন. |
| S-04 "তথ্য কম" | 🔧 | Grey `?` mark, word "তথ্য কম", **no marker on the scale** (it is not a point between good and risky). |
| S-04 "ঝুঁকি বেশি" | 🔧 | Same layout, muted coral, no glow, no pulse. Demo uses a clearly fictional "নমুনা ব্যাংক (ডেমো)". |
| S-03 Search results / did-you-mean | 🔧 | Ivory sheet, slim teal top bar, up to 5 rows (name, English name, type). |
| S-27 Mic permission | 🔧 | Ivory sheet before the Android/browser prompt: why, what we never keep, অনুমতি দিন / এখন না. |
| S-28 Offline / error | 🔧 | Ivory sheet, plain line, আবার চেষ্টা করুন. Loading > 1 s: "একটু অপেক্ষা করুন…". |
| Rotate panel / desktop column | ✅ | Per FRD §20.3: teal panel "ফোনটি সোজা করে ধরুন"; desktop = centred 412-wide phone column on `--page`. |

Everything after the demo slice (S-05 to S-26) uses the same pattern: slim teal top bar, all content on the ivory sheet. Typed search moves off Home (FRD §9.1 has it there); which tab holds it is part of the open screen plan.

## 2. Colours and tokens ✅

- Two surfaces: the **teal stage** (gradient #2B5653 → #0F2624) for Start, Home, Listening and the report-card hero, and the **ivory sheet** for anything people read.
- Contrast catch on teal: the light top (#2B5653) only passes for ivory text (7.2:1). Helper text, gold text and all status words must sit on the darker part (#1E4542 or #0F2624). On the report card, put the status mark, word and scale on a #0F2624 panel.
- Green "ভালো অবস্থা" sits close to the teal hue, so the ✓ mark and word carry the meaning; never colour alone.
- Gold is brand only (wordmark, Start button, orb waves, active tab). It is close to the amber "সতর্ক" colour, so never on a report card or next to a status. The prototype's gold "English" pill on the report card becomes an ivory outline.
- One glow in the whole app: the Home orb.

## 3. Type ✅

- Hero lines, bank name, status word: **Tiro Bangla**. Reading text, buttons: **Noto Sans Bengali** (line height 1.6). Latin: Noto Sans.
- Galada / Dancing Script only for the S-00 and Home hello frames. Check Galada renders every conjunct in "কথা বলতে চাপুন" and "হ্যালো, আমি ইলমা" before shipping; fall back to Tiro Bangla if not.
- Sizes follow FRD §20.2: body **20**, minimum 16 anywhere. The prototypes use 17–19 in places; bump them in the build.
- Self-host subset WOFF2 files (no Google Fonts call on a cheap phone).

## 4. Copy ✅

| Place | Bangla | English |
|---|---|---|
| Wordmark | ইলমা + ILMA | same |
| Tagline | আপনার সঞ্চয়ের বিশ্বস্ত সাথী | Your trusted savings companion |
| Home idle line | কথা বলতে যেকোনো জায়গায় ট্যাপ করুন | Tap anywhere to speak |
| Home sub line | ব্যাংকের নাম বলুন বা প্রশ্ন করুন | Say a bank's name or ask a question |
| Search | ব্যাংকের নাম লিখুন… | Type a bank's name… |
| Listening | শুনছি… → ইলমা খুঁজে দেখছেন… | Listening… → Ilma is checking… |
| Privacy | পিন, ওটিপি বা অ্যাকাউন্ট নম্বর কখনো চাই না | We never ask for your PIN, OTP or account number |
| Not advice | এটি তথ্য, পরামর্শ নয়। টাকা রাখার আগে ব্যাংকে হার ও নিয়ম নিশ্চিত হয়ে নিন। | This is information, not advice… |

- Never "advisor", "নিরাপদ" badges, rankings or "best bank". Status words only from FRD §11.
- Demo data: real values only (EBL, Pubali, Dutch-Bangla, checked list in project memory). The prototype's "উদাহরণ ইসলামী ব্যাংক" reasons are placeholders and must not reach the build.
- Full English strings for the demo path are already in the prototype's `T.en` table; reuse them.

## 5. Motion ⚠️ D3

Recommended rule: **"motion only with meaning"**. Ordinary transitions ≤ 200 ms. Named moments allowed to be longer:

1. S-00 write-on (~1.5 s, once).
2. Home hello cycle: Bangla ⇄ English, stops on first touch or after 2 rounds and rests on Bangla.
3. Orb waves: slow when idle, follow the voice while the mic is open.
4. Report-card marker slide (~1.1 s, once per open).
5. Mascot gentle bob on S-00 only (no mascot on Home now).

Drop from the prototypes: the floating drift of the S-00 bubbles and the slow spin of the stitch rings (decoration, battery). All motion off with reduce-motion.

## 6. Accessibility ✅ (scope ⚠️ D5)

- Touch targets 56 dp, text buttons 48 dp; 8 dp apart.
- TalkBack: the full-screen tap area is one button and the first focus on Home, label "কথা বলুন। ব্যাংকের নাম বলুন।"; bottom tabs are labelled buttons; mascot and halos `aria-hidden`; report card announces "অবস্থা: সতর্ক থাকুন। কারণ তিনটি।" first; live regions polite.
- ILMA's voice yields to TalkBack (ACS-05). Audio never autoplays before the first tap.
- Text at 200% must not cut off the curved sheet or the scale labels; test on a 360×640 phone.
- Contrast: run Lighthouse/axe on every build, target ≥ 95.

## 7. Open decisions for Sumon

| # | Decision | Recommendation |
|---|---|---|
| D1 | Home layout | **Decided:** empty teal Home with the wave orb, tap anywhere, bottom tabs, no centre mic. |
| D2 | English | **Decided:** English pill top right on Home. Still to confirm: translate the demo path only, and take English off the FRD cut list. |
| D3 | Approve the five named motion moments above, replacing the FRD's "≤ 200 ms, ring only" rule? | Yes. |
| D4 | Home line | **Decided:** "কথা বলতে যেকোনো জায়গায় ট্যাপ করুন" / "Tap anywhere to speak". |
| D5 | Blind access in V1: TalkBack basics only, or also the eyes-free tap-or-talk mode? | TalkBack basics in V1 (the FRD requires them anyway); tap-or-talk as a stretch goal after the demo path works. |
| D6 | Ilma's voice for the clay bank: which TTS voice? | Pick one warm, calm Bangla female voice from the speech service you use for the Meta AI tooling score; test it on day 1. |
| D7 | Which tab holds each FRD screen (search, save wizard, alerts, My banks) | See the screen plan linked at the top. |

After Sumon answers, update the FRD in one pass: §8.1, §9.1, §16/§22.4 (language), §20 (replace with this file + tokens), §23.4 (motion), §33.3 (cut list), Appendix A (English clips).
