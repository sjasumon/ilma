# APP_SPEC_02: Voice in and voice out

For Sumon's build agent. Read with ILma.md (FRD) and APP_SPEC_01. Where they disagree, this file wins for voice.

**Based on Sumon's recording tests of 25 Oct 2026** (H:\Projects\ilma-test: `test-voice-transcribeV2.py`, results_tts_clean, results_noisy, results_noisy_kw, results_en, results_en_noisy). That is 1,586 transcriptions of 7 ElevenLabs voices: 4 Bangla, 3 native English. They cover 30 Bangla and 15 English questions, clean audio plus fan noise (10 dB) and crowd babble (5 dB). Section 11 has the numbers.

**Limitation:** every test clip was a synthetic voice. No real person, older speaker or phone mic was tested yet. Section 10 test 3 closes that gap before the demo.

---

## 0. What has to be true for the demo

1. A person says a bank name or a question in Bangla (or English) and sees the words they said within about 3 seconds. The tests measured a median of 3.0 s and a 90th percentile of 3.1 to 3.9 s.
2. The app lands on the right bank, or on the right Bank services answer.
3. Speech-to-text uses **Muse Voice Transcribe** (Meta Model API). The hackathon requires Meta models, and judges score Meta tooling at 25%.
4. The model never invents a number. Voice only finds *what* was asked. Facts and rules come from the database (APP_SPEC_01).

## 1. What the current build does wrong

The live app at app.sumon.me uses the browser's Web Speech API and keyword matching (`q.includes("ইস্টার্ন")`). Replace both:

- Web Speech sends audio to Google, not Meta. It doesn't work in Firefox or many Android WebViews, and it isn't Meta tooling.
- Keyword matching misses what the tests showed Muse actually returns. Muse often writes bank names in English letters inside a Bangla sentence: "Eastern Bank কি নিরাপদ?", "Premier Bank", "IFIC Bank-এর FDR rate কত?". A Bangla-only keyword check scores those as misses.

Do not keep Web Speech as a hidden fallback. If the server path fails, the fallback is typing (section 8).

## 2. Flow

```
tap anywhere (Home) or the mic in Bank / Bank services
  -> record in the browser (MediaRecorder)
  -> stop on silence or max length
  -> POST /v1/voice  (audio + context)
       1. ffmpeg -> WAV 24 kHz mono 16-bit       (the format the test used)
       2. Muse Voice Transcribe                  -> transcript
       3. clean transcript (section 3.3)
       4. bank matcher, Bangla + English aliases -> institution candidates
       5. language decision (section 7)
       6. Muse Spark intent call (JSON)          -> intent, product, amount, period
       7. route                                  -> report card | services answer | ask answer | clarify
  <- response streams the transcript first, then the result
  -> app shows "আপনি বলেছেন: …", then opens the result
  -> Ilma speaks the short result (section 6)
```

### 2.1 Recording (client)

| Setting | Value |
|---|---|
| Format | Record `audio/webm;codecs=opus` (Chrome, Android WebView) or `audio/mp4` (iOS Safari). The server converts it, so the client doesn't need WAV. |
| Stop on silence | 1.5 s of silence after speech starts (FRD 9.2). Not tested yet, because the test clips were pre-cut. Make it a config value (`VOICE_SILENCE_MS`) and raise it to 2000 if real older speakers get cut off. |
| Max length | 15 s (FRD 9.2). Test clips averaged 2.5 s. |
| No speech at all | Stop after 6 s and show E-04 "not understood". |
| Silence detection | Web Audio `AnalyserNode` RMS level. The orb animation reads the same level (design/home-options/ilma_home_teal_prototype.html already has this code). |
| Noise check | Measure the noise floor for the first 300 ms. If it is high, show "চারপাশে শব্দ বেশি, একটু শান্ত জায়গায় বলুন". Crowd talk was the one condition that broke recognition (section 11). |
| Feedback | Start tone + 30 ms vibration when the mic opens, and a lower tone when it closes. The orb pulses with the voice level. Show "শুনছি…" and a থামুন button. |
| Mic permission | Ask only on the first tap, after one line of explanation (FRD 8.3, screen S27-Mic). If denied, show E-03 with the typing option. |

### 2.2 Context sent with the audio

```json
{ "tab": "home | bank | services", "bank_id": 101, "ui_lang": "bn | en", "history": [last 3 exchanges, text only] }
```

`tab` and `bank_id` are what make Ask inside Bank and Bank services work: the intent call already knows the topic, so "লোন কত?" asked on the EBL page means EBL loans.

## 3. Speech to text (server)

### 3.1 The call (same as the test script)

```
POST https://api.meta.ai/v1/asr/transcribe
Authorization: Bearer $META_MODEL_API_KEY        (server env only, never in the app or repo)
multipart:
  request = {"model": "muse-voice-transcribe-1.0", "mode": "PUSH_TO_TALK",
             "audioEncoding": "WAV", "languageBias": [...]}
  audio   = WAV, 24 kHz, mono, pcm_s16le, metadata stripped
            (ffmpeg -ac 1 -ar 24000 -c:a pcm_s16le -map_metadata -1)
response: {"transcript": "...", "audioDurationMs": ...}
```

Retry on 429 or 500 up to 2 times (2 s, then 4 s). Timeout 8 s, then E-04 with typing. There were 0 errors in 1,586 test calls.

### 3.2 Settings: chosen from the test

| Setting | Use | Why (test result) |
|---|---|---|
| `languageBias` when the app is in Bangla (default) | `["Bengali"]` | Best for Bangla. CER 0.131 vs 0.234 with Bengali+English. Bank found in 103 of 103 clean clips. Clean English questions still came back in English (103 of 105), so English speakers are still detected. |
| `languageBias` when the app is in English | `["Bengali", "English"]` | Best for English. In noise, the language was right 208 of 210 times vs 195 of 210, and the bank was found in 79% vs 75% of clips. |
| No hint (auto) | Do not use | Worse than Bengali-only for Bangla (CER 0.176), with no gain elsewhere. |
| `keywords` (bank names) | Do not send | No gain: the bank hit rate was the same with and without. With Bengali+English, keywords raised CER and caused more doubled words. |
| Two calls in parallel (Bangla and Bangla+English) | Do not use | Tried as a rule on the results: Bangla language accuracy fell from 109 of 119 to 101 of 119. |
| Contributor model | **Never** for user audio | Meta may train on Contributor input. |
| Audio retention | Delete the audio right after transcription; log text only | FRD VOC-05 |

Cost: about $0.00012 per question (2.5 s clip). The whole test cost $0.20.

### 3.3 Clean the transcript before matching

Muse output had three habits in the tests. Fix them in code before matching:

1. **Doubled words.** "সোনালীসোনালী", "IFICIFIC", "সমস্যা সমস্যা", "টাকা টাকা". This happened in 6 Bangla-only calls, and 29 with Bengali+English. Collapse a word that is its own half repeated, and the same word twice in a row.
2. **Hindi letters.** One clip returned "जनता बैंक". Map the Devanagari word "बैंक" to "ব্যাংক". If any other Devanagari text remains, treat the clip as unclear.
3. **Trailing punctuation.** Strip "??", ".:", "!" and similar, plus extra spaces.

Show the cleaned text to the user as "আপনি বলেছেন: …".

## 4. Bank-name matching (after transcription)

1. Normalise: Unicode NFC, Bangla digits to 0–9, remove punctuation, collapse spaces, lower-case Latin, and strip "ব্যাংক / bank / পিএলসি / PLC / লিমিটেড / Ltd / -এর / এর".
2. Match against **both** the Bangla and English aliases of every bank in `bank_aliases`. These include short forms (EBL, DBBL, MTB, NCC, SBAC, IFIC) and Banglish ("brac", "dutch bangla"). Use `rapidfuzz` partial ratio on a sliding word window. With bilingual aliases, the test's bank hit rate went from 85% to **100% on clean Bangla** and 98% with fan noise.
3. Score ≥ 90: open that bank. Score 75–89, or 2–4 close matches: show "আপনি কোনটি বলতে চেয়েছেন?" with up to 4 big choices (S-03b). Below 75: E-04.
4. A name that is not a licensed bank or NBFI goes to S-03c "not licensed". Never say it is a fraud.
5. The 9 demo banks: EBL, BRAC, City, MTB, NCC, Prime, DBBL, Bank Asia, SBAC. Any other licensed bank still matches and shows "তথ্য এখনো যোগ হয়নি".

**Add these mishearings from the test as alias rows** (`source = "asr_test_2026-10-25"`):

| Bank | Muse heard |
|---|---|
| Pubali (পূবালী) | উবালি, কুবালি, ভ্যালি |
| Mercantile | arcantile |
| Al-Arafah Islami | "আল-আরাফাহ Islami Bank" (mixed script) |
| Premier, Eastern, National, NCC, IFIC | English spelling inside Bangla text (e.g. "Premier Bank", "NCC Bank এর") |
| Janata | जनता बैंक (fixed by 3.3) |

**Short names are risky.** "প্রাইম ব্যাংকে" came back as "প্রায় টাকা" in fan noise. For one-word names (Prime, City, NCC, Dhaka), only accept a match when "ব্যাংক / bank" follows, or when the user taps to confirm on S-03b.

## 5. Understanding the request (Muse Spark)

One small call, temperature 0, JSON only:

```json
{ "intent": "bank_status | bank_detail | rates | service_compare | insurance | explain_word | out_of_scope | unclear",
  "institution_ids": [101],
  "product": "fdr | dps | savings | credit_card | personal_loan | home_loan | car_loan | sme_loan | null",
  "card_tier": "classic | gold | platinum | signature | null",
  "amount_bdt": 500000, "period_months": 12 }
```

- Pass the institution the matcher found. Muse Spark doesn't look up bank names itself.
- A bank name alone with no question means `bank_status`, so go straight to the report card without the model call.
- Normalise numbers before the call ("দুই লাখ" → 200000, "এক বছর" → 12).
- Never store an amount, account number or PIN. If one is heard, Ilma says "অ্যাকাউন্ট নম্বর বা পিন কখনো বলবেন না।" (FRD 16.5).
- The answer itself follows FRD 16.2 steps 4–7: facts from the database only, every number checked against the facts, and "এই তথ্য আমাদের কাছে নেই।" when nothing is found.
- Ask one clarifying question at most ("কোন ব্যাংকের কথা বলছেন?").
- The test of Spark 1.3 (results/summary.csv, 25 Oct) took 1.4 to 4.9 s per Bangla answer, so ASK-06's 15 s voice-to-spoken-answer target is reachable.

## 6. Ilma's voice (speech out)

| Kind | How |
|---|---|
| Fixed clips (welcome, hints, 4 status words, insurance line, errors) | Pre-made once in one voice, checked by a native speaker, bundled offline. Bangla and English versions. |
| Live answers and report read-outs | ElevenLabs (Meta's API has no text-to-speech). Pick one of the Bangla voices already in Sumon's account from the test: arfa, swati (female) or rakib, rayhan (male). The FRD persona is a calm female voice, so arfa or swati. Final pick is design decision D6. |
| Pronunciation | Apply the FRD 22.3 lexicon before TTS: "২,০০,০০০" → "দুই লাখ", "10.5%" → "সাড়ে দশ শতাংশ", PLC/Ltd not spoken. |
| Speed | Slightly slow. A "ধীরে" setting plays at 0.85×. |
| Behaviour | Text appears first, then audio. One sound at a time. Any tap stops it. Listen turns into Stop while playing. Never autoplay on a page the user didn't ask to hear. |

## 7. Language switching

Muse mixes scripts: a Bangla sentence often comes back with the bank name or "FDR rate" in English letters. So the rule cannot be "any English letters means English".

1. Remove the matched bank alias and these loanwords: bank, FDR, DPS, rate, PLC, card, loan.
2. Count the remaining letters. **Switch to English only if at least 70% are Latin.** This keeps "Eastern Bank কি নিরাপদ?" and "IFIC Bank-এর FDR rate কত?" in Bangla, and switches "is জনতা ব্যাংক safe?" and "Is Sonali Bank safe?" to English.
3. After a switch, show the chip "English · বাংলায় ফিরুন". From then on, send `["Bengali", "English"]` (section 3.2).
4. The English pill in the top bar stays as a manual switch. The choice is remembered on the device.

## 8. Errors and fallbacks

| Case | Screen | What happens |
|---|---|---|
| Mic denied or no mic | E-03 | Explain, and offer "⌨ লিখে খুঁজুন", which opens S-03 text search with the same matcher |
| Nothing heard / not understood / no bank match | E-04 | "বুঝতে পারিনি। আবার বলুন বা লিখুন।" with Retry and Type. Never jump silently to another tab. |
| Noisy room (high noise floor, or a second failure in a row) | E-04 + tip | "চারপাশে শব্দ বেশি…". With crowd talk, the bank was found in only 58–67% of clips, so after 2 failures offer typing first. |
| Offline | E-01 | Mic disabled; cached report cards still open |
| Transcribe timeout or API error | E-04 | Same as above; log the error, not the audio |
| Daily limit (20 AI questions per device, FRD 16.6) | Notice | Template answers (status, insurance, latest rate) still work |

## 9. API

`POST /v1/voice` (multipart: `audio`, `context` JSON) returns a stream of events:

```
event: transcript  {"text": "ইস্টার্ন ব্যাংক কেমন আছে", "language": "bn"}
event: match       {"intent": "bank_status", "institution_ids": [101], "confidence": 0.94}
event: result      {"type": "report_card", "url": "/v1/institutions/101/report-card"}
event: speech      {"audio_url": "...", "text": "..."}   (only if speak=true)
```

`POST /v1/ask` takes the same body with `text` instead of `audio` (typed questions and WhatsApp text). WhatsApp voice notes go through the same pipeline from the webhook.

## 10. Tests the agent must pass

1. **Unit:** transcript cleaner (every example in 3.3), language rule (every example in 7), number normaliser, and the alias matcher. Every mishearing in the section 4 table must match the right bank. Also check the intent JSON schema.
2. **Replay:** reuse H:\Projects\ilma-test\audio with `references_tts.csv`, `references_noisy.csv` and `references_en*.csv`, run every clip through `/v1/voice`, and print the transcript, matched bank, language and time for each. Pass levels, from the 25 Oct baseline: clean Bangla bank ≥ 98%, fan noise ≥ 95%, English language right ≥ 98%, median ≤ 4 s end to end.
3. **Real voices (must do before the demo):** about 20 phone recordings. Use Sumon, one woman, and one person over 60. Say the 9 demo banks plus 5 questions, half in a quiet room and half with a TV or fan on. Add them to `audio/` with a `references_real.csv` and rerun test 2. If clean real voices fall below 90% bank found, send the results to manual review before going further.
4. **Phone:** on a cheap Android over mobile data, say "ইস্টার্ন ব্যাংক", "ব্র্যাক ব্যাংকের এফডিআর রেট কত" and "Is City Bank safe?", and check each lands right.
5. **Privacy:** no audio file on disk after a request, and no PIN, amount or account number in the logs.

## 11. Recording test results (25 Oct 2026)

Columns: CER (lower is better), bank found (as scored by the test script, then with bilingual aliases), language right, median response time.

| Set | Setting | CER mean | Bank found (script) | Bank found (bilingual aliases) | Language right | Median s |
|---|---|---|---|---|---|---|
| Bangla clean, 119 clips | A Bengali | **0.131** | 88/103 | **103/103** | 109/119 | 2.86 |
| | B Bengali+English | 0.234 | 73/103 | 98/103 | 101/119 | 2.80 |
| | C auto | 0.176 | 81/103 | 97/103 | 106/119 | 2.84 |
| | D Bengali+English+keywords | 0.214 | 73/103 | 101/103 | 103/119 | 2.87 |
| Bangla, fan 10 dB, 60 clips | A Bengali | 0.150 | 38/52 | **51/52** | 54/60 | |
| | B Bengali+English | 0.235 | 35/52 | 49/52 | 55/60 | |
| | E Bengali+keywords | 0.147 | 40/52 | 50/52 | 54/60 | |
| Bangla, crowd babble 5 dB, 60 clips | A Bengali | 0.372 | 19/52 | 30/52 | 50/60 | |
| | E Bengali+keywords | 0.373 | 19/52 | 32/52 | 47/60 | |
| English clean, 105 clips | A Bengali | 0.051 | 60/63 | 60/63 | 103/105 | 3.00 |
| | B Bengali+English | 0.051 | 60/63 | 61/63 | 104/105 | 3.04 |
| English noisy, 210 clips | A Bengali | 0.202 | 72/126 | 95/126 | 195/210 | 2.98 |
| | B Bengali+English | **0.147** | 91/126 | **100/126** | **208/210** | 2.99 |

- Errors: 0 of 1,586 calls. Slowest call 7.8 s. Cost about $0.00012 per clip.
- Most "bank not found" results in the script were Muse writing the name in English letters, not mishearing it. That's why bilingual aliases fix it.
- Real mishearings: Pubali (উবালি / কুবালি / ভ্যালি), Prime (প্রায়), Mercantile (arcantile), and one Hindi-script reply.
- Not tested yet: real human voices, older speakers, phone mics, and the silence timer. These are covered by section 10, test 3.
