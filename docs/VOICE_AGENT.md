# Voice agent implementation and checks

Normal Home opens on a fresh visit. Guided Voice only starts only when its
saved setting is enabled. Turning it off returns to normal Home and remains
off after reload; unrelated settings changes do not restart the guided flow.

Implemented in `api/ilma_api/voice_agent.py`, with Home adapters in `app.js` and
conversation lifetime/tap counting in `voice-agent.js`. Public behavior and API:
[specification](specs/APP_SPEC_07_voice_agent.md).

Every result has ASR, PLAN, ACT, SAY and CHECK trace rows with actual model names,
measured times and skipped/unavailable states. Tool facts retain their source
and uncertainty. Model wording is limited to three fifteen-word sentences and
is checked conservatively; templates preserve source wording when a paraphrase
cannot be verified. The inspection panel never labels a template as model
verified. It does not display prompts, credentials or model response bodies.

Service comparison uses the existing curated selector, then requires the same
basis, unit, attribute, tenor, network/tier and normalized published condition.
Stale and future-dated offers are excluded from comparison. A small compatible
cohort may contain fewer than three banks; this is not a bank recommendation.
Overview counts are service attributes, not distinct products or account counts.

The `app_model_call` table stores only turn UUID, stage, model, duration, status,
nullable token counts and creation date. Existing question logs remain redacted.
No new recording retention or server conversation storage is introduced. The
existing diagnostic switches still govern the separate test recording feature.
Runtime migration is limited to the `ilma` database; isolated tests use SQLite.

Validation commands:

```sh
PYTHONPATH=api python -m pytest -q
node tests/test_voice_agent.cjs
python tests/check_voice_agent_browser.py --base-url http://127.0.0.1:8018
```

The browser check uses synthetic media/recorder/provider responses. The spoken
reply fixtures test scripted matching, not microphone recognition accuracy.
Real phone audio, under-twenty-second speech duration, native TalkBack/VoiceOver,
new fixed-clip pronunciation review and highlighted original-page images remain
acceptance items. No native wrapper or snapshot generation is claimed here.

Agent speech is measured after synthesis. Small overruns use a bounded tempo
adjustment of at most 15%, aiming at nineteen seconds without truncating words.
Longer speech is left intact and marked `over_target` in the trace; measurement
unavailability is explicit. The user's slower playback preference is preserved.
The timing target applies to normal playback, not the deliberately slower mode.

Live smoke check on 28 October 2026: the model-free Bangla BRAC summary
measured 19.932 seconds of generated audio at normal playback. This is one
sample, not a guarantee for all answers or slow mode. A separate live SAY
response failed the conservative local check and correctly used the template;
it was not labelled model-verified. Real microphone and device acceptance
remain pending.

## Reply resolution

Current option labels (Bangla/English), one/two, yes/no and known option synonyms
resolve before PLAN and use exactly the tap path, including template wording.
A free-form bank-and-product question routes directly to that bank's service
tool; product-only follow-ups retain the current bank and current product/term.
A bank question is asked only when no current or named bank is available.
Recognized out-of-demo names return “এই ব্যাংকের তথ্য এখনো যোগ হয়নি।” and never
fall through to the previous bank. The nine demo banks and the existing approved
NBL/Islami supplements retain their coverage. Bengali vowel-sign spelling
variants (`ু`/`ূ`, `ি`/`ী`) are folded only for matching; source names and quotations
retain their original spelling.
