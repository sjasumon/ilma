# Code review and layout fixes — 27 October 2026

Reference: docs/FRD ILma.md, BUILD_PLAN.md, ILMA_design_build_checklist.md,
APP_SPEC_01_database_and_status.md, tokens.css and design/S01-Home.html.
The user's four-tab decision overrides the older checklist: Home, Bank services,
Bank detail, News. Settings remains deferred.

Implemented:
- Home uses document flow rather than absolute positioning. The orb keeps its
  reference artwork and teal/gold/cyan palette. Short screens use a smaller orb.
- Dock participates in layout, supports wrapped labels and safe-area padding.
  Cards, health checks, scale labels and modal content can wrap enlarged text.
- Home has a native keyboard button, separate from Stop. The source dialog traps
  focus, supports Escape, makes background controls inert and restores focus.
- Voice lookup no longer defaults unknown queries to Eastern Bank; it opens the
  bank selector with an announcement. Pending voice actions cancel on navigation.
- Report requests clear stale content and ignore superseded responses. Missing
  status and licence-only responses are supported. News has error/empty states.
- API text and quotations are escaped before HTML insertion; source links allow
  only HTTP(S). Missing quotations no longer show an invented verification line.
- Report insurance wording comes from its API record. Watch no longer claims an
  alert subscription was saved when the feature is unimplemented.
- Removed embedded database credentials. Set DATABASE_URL in the process
  environment; .env.example documents the format (no automatic dotenv loader).
- Corrected current FDR median selection, rating normalization, health-check event
  windows, API error envelope, search result limit and insurance type validation.

Validation:
`PYTHONPATH=api python -m unittest discover -s tests -v` — 12 tests pass,
using isolated SQLite fixtures. API tests exercise route functions and OpenAPI
schema directly; they do not verify HTTP transport. JavaScript syntax and Python
compilation pass. `node tests/test_frontend.cjs` passes runtime regressions for
licence-only rendering, HTML escaping, source URL handling and zero inputs. Chromium launch and HTTP listener creation are prohibited by
this workspace sandbox; no browser, axe, screenshot or TalkBack pass is claimed.

Remaining work from the build plan:
- Manually test 360×640, larger phones, both languages and 200% text; run axe and
  TalkBack on device. System/screen-reader speech coordination needs device work.
- Self-host Bengali WOFF2 fonts; the existing Google Fonts dependency remains.
- Complete English translations in calculator output, health-check values,
  bank-selector options, source controls and static helper copy.
- Verify seed facts, legal text, rates and source URLs against original documents.
  No independent provenance verification was performed in this code review.
- Voice currently uses browser SpeechRecognition and a small bank-name matcher;
  Meta voice/intent, permission explanation, typed search, proof page images,
  persistent watch/alerts, offline cache, onboarding and Android packaging remain
  build-plan features, not completed implementations.


## Screenshot follow-up
The screenshot shows unstyled Home classes, a visible live-region announcement,
and both idle/listening panels. This is consistent with an older stylesheet
being served alongside the updated HTML. Versioned CSS/JS URLs now invalidate
cached assets, and the app entry response uses Cache-Control: no-store. Listening
uses the native hidden attribute with a critical hidden rule in the HTML. The
full-area speech button has its own class, independent of screen-reader-only
text. Home centering is scoped explicitly. Frontend runtime checks verify the
listening/idle state transitions and asset versions. Browser visual verification
is still unavailable under the sandbox restrictions.


## Bilingual Home greeting — corrected lifecycle
One centered line cycles automatically every 3.8 seconds: Bangla prompt, English
prompt, Bangla bank-question example, English translation, then repeats while
Home is visible. Generic pointer/keyboard events no longer cancel the timer.
Leaving Home, recording speech or hiding the page pauses it; returning resumes
it with a single timer. Reduced motion disables the visual reveal, not the text
sequence. Unsupported reveal animations do not prevent the timer from starting.

The original tests checked frame text, but did not advance the timer or exercise
DOMContentLoaded. `node tests/test_greeting_cycle.cjs` now runs app startup and
advances 12 scheduled transitions, including ordinary interaction, page hide/show,
leaving/returning Home, speech start/stop, reduced motion and animation failure.
`node tests/test_frontend.cjs` and all 12 Python backend tests also pass. Asset URLs
are versioned `home-greeting-20261027-4`. Browser/device visual verification remains
outstanding under the sandbox restrictions.


## Language, settings and swipe update
The header language button now offers EN/BN, with a localized accessible name
stating the destination language. The adjacent Settings button opens a native
modal dialog with language, animation and swipe controls. Preferences persist in
localStorage; blocked storage does not break the controls. The four bottom tabs
remain unchanged. Home cycles only the selected language's prompt and example.

A primary touch/pen swipe left on Home (at least 70px, no more than 40px vertical,
under one second) toggles language and announces it. The subsequent synthetic tap
is suppressed so swiping does not activate the microphone. Right swipes, short
motions, vertical scrolling, mouse drags and cancelled pointers do not switch.
Swipe is optional in Settings. TalkBack/VoiceOver may consume swipe gestures;
users can always operate the labelled language button or native language select.

Lifecycle tests cover language-only cycles, settings open/close, swipe recognition,
synthetic-click suppression, ignored gestures, preference restore and blocked
storage. Native dialog focus and screen-reader touch gestures still need an
actual device check. Asset URLs: home-settings-20261027-5.


## Viewport-centered Home orb
The orb's center now sits at 50% of the viewport width and height. Its grid row
starts at half the dynamic viewport height minus half its size; header height and
rotating/listening text cannot shift it. The orb scales down on short or narrow
screens, and text flows below it with bottom clearance for the fixed Home dock.
Other tabs retain their scrolling layouts. Uses dvh with vh fallbacks; Home
header and dock respect safe areas. Assets: home-centered-20261027-6.


## Optical balance follow-up
Lifted the Home orb from exact viewport center by 6% of viewport height,
bounded to 32–60px, to balance the bottom navigation and greeting below it.
A minimum 96px top clearance protects the header on short screens. The circle
stays horizontally centered; viewport sizing and text flow are unchanged.
Assets: home-balanced-20261027-7.

## Swipe compatibility follow-up
The previous handler explicitly ignored mouse drags and required Pointer Events.
It now supports primary mouse drags as well as touch/pen, captures the pointer
through release, and uses Touch Events as a fallback when Pointer Events are not
available. Recognition accepts a 56px leftward gesture within 1.5 seconds with
horizontal direction dominant. Dragged/scrolling gestures suppress synthetic
microphone clicks even when they do not change language. Vertical scrolling and
pinch zoom stay enabled. Runtime tests cover both input paths and cancellation;
physical-device and screen-reader verification is still required. VoiceOver's
one-finger left swipe navigates focus and cannot be promised as an app shortcut.
Assets: home-swipe-20261027-8.

## Tap-to-speak navigation fix
Removed the fallback that sent every unsupported/failed voice attempt to Bank
details. Home taps start the browser recognizer, interim text stays on Home, and
final transcripts search /v1/institutions/index against released bank names and
aliases. Only a single matched bank opens a report; multiple matches show choices
on Home and missing matches show a retry message. Permission denial, unsupported
browser/language, insecure context, audio capture and network failures show
localized feedback rather than navigating. Pending results are invalidated when
stopped or navigated away. The hard-coded four-bank voice router was removed.

`node tests/test_voice_search.cjs` checks simulated recognizer events, successful
Bangla/English/alias searches, error/retry behavior, ambiguity and cancelled
requests. No physical microphone test was possible in this workspace. This still
uses browser SpeechRecognition; server-side Meta transcription is not wired up.
Assets: home-voice-20261027-9.


## Meta audio integration
Replaced browser SpeechRecognition with getUserMedia/MediaRecorder and in-memory
24kHz mono PCM WAV conversion. A short recording is uploaded to ILMA /v1/ask;
server-side httpx sends the key only to the configured Meta endpoint. The
provider JSON transcript is matched to actual institution names/aliases in the
database. Results and recognized words appear on Home for explicit selection;
unknown or ambiguous input never opens a default EBL report. Bank details also
starts with an empty bank selection rather than selecting EBL automatically.

Validation: 18 Python tests pass; all four Node suites pass (frontend regression,
greeting/settings/swipe, Meta voice UI and actual audio-recorder logic). Tests
cover provider multipart/auth fields, PCM encoding, size/duration validation,
permission/silence/timeout errors, Pubali/Dutch-Bangla matches and cancelled
requests. Provider responses and audio are not persisted. The private .env stays
mode 600 and is excluded by .gitignore; no key was printed.

Live checks: the configured Meta request failed with a transport error; API key
acceptance and actual microphone accuracy could not be confirmed in this
workspace. No DATABASE_URL or local database was configured at review time;
requested the existing database URL be entered privately in .env. No fixture or
invented bank records were loaded into the user's database. See MUSE_VOICE_API.md
for configuration and startup. Assets: meta-voice-20261027-10.


## APP_SPEC_02 alignment
Read the new root APP_SPEC_02_voice.md and treated it as authoritative for voice.
Runtime MySQL replaces the SQLite fallback. Voice uses /v1/voice, compressed
recordings, server-side ffmpeg, transcript/match/result SSE events, tested language
bias settings without keywords, two ASR retries, transcript cleaning, RapidFuzz
window matching and short-name confirmation. /v1/ask now accepts typed questions
with the same context/matcher. Muse Spark intent JSON is validated and cannot
invent institution IDs. Answers use database templates only. ElevenLabs handles
speech output and manual readouts; the browser speech API has been removed.

Frontend adds permission explanation, RMS/noise feedback, six-second no-speech
cutoff, server-configured silence, typing fallback, bank/services microphones,
automatic English switching with return chip, and spoken-answer/slow settings.
Alias provenance/mishearing migration and voice logs/counters are SQLAlchemy
MySQL tables; audio and user input are never persisted. See MUSE_VOICE_API.md.

27 Python checks: 26 pass and the actual RapidFuzz check skips when unavailable.
All four Node suites pass. The workspace cannot connect to its local MySQL socket
and package installation did not supply ffmpeg/RapidFuzz. MySQL connection details
were requested privately. Subsequent DATABASE_URL was present but could not be
parsed as a URL; no migration was attempted against an unknown database. No bank
facts or production data have been altered. Replay/phone/native-review checks
remain pending. Fixed offline clips and the broader full answer-generation path
are not represented as verified by these tests.


## APP_SPEC_02 completion audit
Completed remaining implementation/tooling: compound Bangla/English numbers and
speech lexicon, fact-specific detail/glossary queries, grounded Spark wording with
number/citation checks and template fallback, one-clarification/privacy guards,
explicit unlicensed-record handling, all demo aliases, owned streaming sessions,
public-only offline caching, native-review-gated audio generation, daily retention,
replay metrics/CSV mapping, recording-only real-voice collector, and safe readiness
and host-bootstrap commands. No live/phone/native acceptance has been invented.
See VOICE_ACCEPTANCE.md for requirement mapping and the deployment-host work still
blocked by workspace restrictions. Existing credentials stay private and ignored.
