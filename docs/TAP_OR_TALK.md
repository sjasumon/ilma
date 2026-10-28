# Guided tap-or-talk mode

Normal Home is the default, including the first visit. The guided flow is
opt-in: enabling **Voice only / শুধু কথায়** in Settings starts it when Settings
closes and on later app opens. Disabling it returns to normal Home and stays
off after reload. Opening Settings without changing this switch resumes an
active guide instead of starting from the beginning. The normal
Home recording, swipe language toggle, and in-place bank/services recording
remain available after Skip. Settings also offers an explicit screen-reader
preference; web browsers cannot reliably detect TalkBack.

The two-choice table is `IVR_STEPS` in `static/js/ivr.js`; application adapters
are in `static/js/app.js`. Steps: Open → microphone explanation/permission →
Language on first use → Menu → Name → uncertain-match confirmation → sourced
Report → Next. Bank services exits to the existing Services tab. The scoped
spoken commands are matched exactly on the server after normal transcription,
before bank lookup or intent classification. They do not match substrings in
financial questions. The context carries a validated `ivr_step`.

When the microphone is closed, the choice button waits 450 ms to distinguish
one physical tap from two. Enter/Space and native assistive activation resolve
one choice immediately. When recording, two physical taps stop recording and
search; they never also select choice two. Native activation stops with one
activation. Tapping a spoken question interrupts it and still chooses. Any tap
during the report stops playback and moves to Next.

Microphone windows start only after successful prompt playback ends and last
at most six seconds. If the device blocks playback or microphone access, the
question remains readable and tap choices/Skip work. If no speech is heard,
wait eight seconds and repeat that question once, then wait quietly. During a
recording window, stop recording first to use physical tap choices. Screen-reader
users can answer by voice or use native button activation. The option labels
are kept together in `updateSettingsText` for later naming changes.

Prompts use approved fixed clips when available, otherwise server TTS for
allowlisted catalog text. Bank confirmation uses a name from the database,
never arbitrary caller-supplied text. Reasons, insurance and source readouts
use existing sourced data. Sources are spoken by title/publisher and available
document date; URLs are not spoken. Recording and requests are cancelled on
Skip, tab changes, backgrounding and orientation interruption. Preferences are
local browser settings; no new database tables or user audio storage are added.

## Validation and remaining acceptance

- `node tests/test_ivr_steps.cjs`: deterministic timing, recording/choice isolation,
  interruption, one silence repeat, native activation, and Skip cancellation.
- Python `tests/test_ivr.py`: scoped command matching, no partial bank-name
  interception, early pipeline dispatch, dynamic confirmation and dated sources.
- `tests/check_ivr_browser.py`: opt-in browser integration with explicitly
  synthetic audio and recorder responses; no provider request is made.
- Existing normal-page geometry checks use completed onboarding preferences.

Native pronunciation review of the new catalog clips is **pending**. Draft
clips must follow `voice_assets` generation/review/publication; no native review
has been inferred or recorded by this change. A previously approved base bundle
continues working while the extra clips await review. The dynamic confirmation
always uses TTS for the actual database name.

No Capacitor/Android wrapper exists in this repository. An optional wrapper can
expose `IlmaAccessibility.isTouchExplorationEnabled()` returning `{enabled:
boolean}` from Android's `AccessibilityManager`; web uses the explicit setting.
The native bridge itself, real phone microphone/provider latency, eyes-closed
use, TalkBack and VoiceOver testing remain device acceptance work. Synthetic
browser checks do not establish production or accessibility acceptance.
