# Answer language and conversation recovery

This specification updates voice-agent reply resolution while retaining the
result-first streaming and model-call limits in APP_SPEC_08.

## Turn language

Matched scripted replies, including current option labels, fuzzy synonyms and
global navigation commands, retain the conversation language exactly like taps.
A reply such as “more details” is not evidence of a language change. Other spoken
and typed questions use the same transcript language rule: remove matched
bank aliases and common English product loanwords, then count alphabetic letters.
At least 70% Latin means English; otherwise use Bangla. When a bank name alone
leaves no language evidence, retain the conversation language or UI preference.
The transcript event, result, next question, narration and returned
conversation.language use the selected language. Button choices retain the
conversation language, including old conversations that omit the new field.

Automatic switches update the app without cancelling its active request. A
bilingual chip lets the user restore their previous language. Restoring during
an agent answer repeats the source-backed answer in that language, keeping the
bank and product. Explicit language changes clear stale undo chips.

## Reply precedence

1. Match current option labels and values, synonyms, one/two, first/second and
   yes/no. Conservative fuzzy matching handles short complete phrases, with a
   high threshold and a clear winning option. Consent and writes require exact
   affirmative choices; never fuzzy-match them.
2. Resolve global details, services, figures, history/news, product/rate,
   insurance, another-bank, repeat and finish commands across states.
3. Resolve named banks and any product in the same sentence; retain the current
   bank when no bank is named. Ambiguous short names are not silently selected.
4. Unresolved or rejected replies retain the state, bank, product and last valid
   tool. Return “বুঝতে পারিনি।” plus the current options. On the second consecutive
   miss add “লিখে বলুন” and reveal/focus typed recovery. A valid reply resets the
   miss counter. Unrecognized single words do not invoke a model to guess intent.

Known unsupported banks still return explicit missing coverage. A requested
product without a bank asks for a bank and keeps the pending product. Missing
source data remains explicitly unavailable. Free questions can still use the
single bounded PLAN call; no model supplies financial facts or SQL.

Every turn has content apart from its next question. A guard compares output
with the previous scripted question; a match records a metadata-only warning
and uses state-preserving recovery. It logs no transcript or question text.

The conversation bound is twenty turns, allowing the required ten-turn exercise;
the existing two-minute idle and navigation reset remain. No server conversation
storage or new financial records are introduced.

## Client recovery

Typed recovery is inline in the themed agent panel with retained option buttons.
Its input has a label, visible focus and keyboard submission. The microphone and
silence re-asks stay off while this recovery is active, including after speech
finishes. Submitting a valid question hides the form. Navigation/reset clears it.
Header and bottom tabs remain within the app frame during language switching,
rotation, keyboard resize and large text.

Tests use handwritten synthetic database rows and synthetic media/provider
responses. Real microphone accuracy, pronunciation and native accessibility
acceptance are separate from these conversation checks.

BRAC ASR aliases “breakbank”, “break bank” and “ব্রেক ব্যাংক” are user-approved match spellings
stored in MySQL. They do not replace the bank display/source name or add facts.

Whole matched alias phrases are removed before language-letter counting. Bank
names alone retain the conversation/UI preference; actual question words still
determine language. The ambiguous word “break” alone requires confirmation.
