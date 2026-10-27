# ILMA app: build plan for the hackathon (prepared 26 Oct 2026, before kickoff)

No code exists yet on purpose. The rules require new work only, so all app code starts in fresh repos after kickoff (26 Oct, 22:00 Dhaka): a private `ilma-private` (github.com/sjasumon/ilma-private) for daily work, and the public `ilma` (github.com/sjasumon/ilma) that receives the same commit history after each finished step (Sumon's plan, 26 Oct). Push with `git push public main` from the private repo; never squash or rewrite, so the public history shows the work happening during the event. The scraper and raw data stay out of both repos. Workflow: one screen per branch; Sumon's local agent builds, Claude reviews before merge, then the finished step is pushed to public. This file is planning only.

Sources: FRD `ILma.md` (rules, data, privacy, API), `design/build/ILMA_design_build_checklist.md` + `tokens.css` (looks, copy, motion; overrides FRD §20), teal Home reference `design/home-options/ilma_home_teal_prototype.html`, feature decisions in the doc "Making ILMA more than basic RAG", demo data in `ilma-data/demo_pack_v1/` (values to re-verify by hand after kickoff, not code to reuse).

## 1. What we are building (final list, 26 Oct)

| # | Feature | Core idea |
|---|---|---|
| 1 | Core path | Say or type a bank name, get the report card |
| 2 | 7 health checks | Capital, bad loans, profit, rating, liquidity, no regulator action, deposit insured. Pass / fail / "not enough data", each with its rule and source. No single score |
| 3 | Proof snap | Tap any number, see the source page with that line highlighted |
| 4 | Insurance split explainer | "Tk 2 lakh of your Tk 5 lakh is covered", no account details asked |
| 5 | FDR rates with real return | Rate list sorted by rate, check count beside each, taka left after tax and inflation |
| 6 | Watch my bank | Follow a bank by name; alerts by SMS, email and in-app when a check or a rate changes |
| 7 | Ask on WhatsApp | Bangla voice note to a WhatsApp test number, same answer back |
| 8 | Full English mode | One-tap switch plus voice auto-detect; subtitles on the video |
| 9 | Eyes-free mode | Tap-or-talk flow for blind users (shown in the video) |

Out: rumour check, offer check.

## 2. Stack

| Part | Choice | Why |
|---|---|---|
| App | Vite + TypeScript + Preact, service worker, portrait only | Small shell (FRD budget ≤ 500 KB), one codebase |
| Android | Capacitor (mic, push via FCM, haptics, status bar) | Decided 24 Oct |
| API | FastAPI (Python 3.12), OpenAPI generated | FRD §26 |
| Data | MySQL 8, loaded from a hand-verified seed CSV (one row per fact: value, source URL, page, quoted line, checked-by date) | FRD API-03: every fact carries its source |
| Rules | Plain Python: 7 checks, status, real return, insured split. Never the model | "The AI cannot invent a figure" is the pitch |
| Meta models | Muse Voice Transcribe (Bangla/English speech in), Muse Spark (intent, bank name, grounded wording, English), Muse Spark vision + SAM 3.1 (proof snap highlight) | Stage One requires Meta models; Meta tooling is 1/4 of the score |
| Ilma's voice | Decide on day 1 (Meta voice if available, else ElevenLabs) | Design D6 |
| WhatsApp | Meta WhatsApp Cloud API test number, webhook `POST /webhooks/whatsapp` | Same pipeline as the app |
| SMS | Sumon's Bangladesh gateway; key only in server env, never in the repo | Repo is public |
| Hosting | OCI server, Docker Compose, Cloudflare Tunnel | FRD §6 |

## 3. Repo layout (same in both repos)

```
ilma/
  app/        web app (Vite) + capacitor.config.ts + android/
  api/        FastAPI: routes, rules/, models/ (Meta clients), jobs/
  seed/       facts.csv, institutions.csv, sources/ (page images for proof snap)
  docs/       architecture, data provenance, demo script
  docker/     compose.yaml, .env.example (names only, no values)
```

## 4. Day plan (feature freeze 1 Nov)

**Working order chosen by Sumon (26 Oct):** finish the v4 data checks first. From 27 Oct, build screen by screen and module by module, starting with Home; animation comes last. Sumon develops against their own MySQL server and pushes via git. Aim to have the demo path (Home, voice, report card, proof snap) working roughly end to end by about 29 Oct, then deepen each screen. Decide at Home whether the clay bank becomes the mic.

| Day | Date | Goal | Done when |
|---|---|---|---|
| 0 | Mon 26 Oct night | Kickoff; repo, keys and accounts ready; Muse Voice Transcribe Bangla test | A Bangla clip comes back as correct Bangla text |
| 1 | Tue 27 | Scaffold app + API + DB; seed loader; re-verify 3 banks' facts | `/health` live; report-card JSON for EBL from seed |
| 2 | Wed 28 | 7 checks + status rules; Home (teal), Listening, voice search | Say "ইস্টার্ন ব্যাংক" on a phone, land on the right bank |
| 3 | Thu 29 | Report card with checks; Source sheet; proof snap | Tap a number, see the highlighted page |
| 4 | Fri 30 | Insurance split; FDR list + real return; English mode | Same path works fully in English |
| 5 | Sat 31 | WhatsApp voice note; watch my bank (in-app, SMS, email) | Voice note answered; a seed change sends an SMS |
| 6 | Sun 1 Nov | Eyes-free mode basics; Capacitor APK; **feature freeze** | APK runs on a cheap Android |
| 7 | Mon 2 | Polish, accessibility pass, user tests | Lighthouse and TalkBack checks pass |
| 8 | Tue 3 | Video shoot and edit with English subtitles | 3-minute cut done |
| 9 | Wed 4 | Freeze, write-up, submit before 9 PM ET (5 Nov 08:00 Dhaka) | Submitted |

If time runs short, cut in this order: eyes-free mode beyond the video moment, email alerts (keep SMS + in-app), FDR list to 2 banks, WhatsApp audio reply (keep text). Never cut sources, the check rules or privacy.

## 5. Needed from Sumon at kickoff

1. ~~Create two GitHub repos~~ Done 26 Oct: public `sjasumon/ilma`, private `sjasumon/ilma-private`. Before each push to public, check that no keys, `.env` files or raw data are in the commits: anything pushed once stays in the public history.
2. Meta Model API access and key (needs a card on the account for the $150 credit).
3. A Meta developer app with the WhatsApp Cloud API test number.
4. SMS gateway key and sender ID, entered as a server secret (not in chat).
5. Email sending: which provider or address.
6. A Firebase project for Android push.
7. OCI server and domain/tunnel access, or say if we demo from a simpler host first.

## 6. Design points to settle (from the build checklist)

- Home is now teal with the glass wave orb and a bottom dock; the checklist and tokens are still navy. Need one theme for the whole app before day 2.
- The report card must show both the status word and the 7 checks; layout of the checks list is not yet mocked.
- Open: D3 motion moments, D4 idle line, D6 voice; tagline.
