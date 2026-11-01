# Reviewed answer recordings

## Extending the reviewed question set

An extension is activated only with the complete contiguous bilingual corpus.
The manifest declares `question_count` and `expected_clips`; both languages must
contain every question ID, and existing files remain byte-for-byte unchanged.
The offline builder accepts an explicit `question_start` / `question_end` range
so it can generate only the additional recordings with its 120-second deadline.

Additional answers may reference published fact, service, incident, insurance
and profile rows through a fixed model allowlist. Their current row values,
source citations and status thresholds form the runtime evidence hash.
Explicit extension questions use those declared sources independently of the
previous conversation bank. An explicitly named, source-backed bank becomes the active bank;
general questions preserve conversation context.
Changed or missing evidence disables the saved answer. Eligibility conditions
are part of this hash. Exact reviewed general questions can use saved recordings
without a wording request, including when no bank is appropriate to the question.
The review page derives its count and question-number limit from the complete
manifest. This does not expand speech recognition or promise paraphrase coverage.

## Reference master selection

When the owner selects **Current/reference full answer — Bangla**, retain that
section for every question, including its closing question. Do not choose the
proposed section for any remaining IDs. The reference selector rejects missing,
empty or duplicate sections instead of falling back to a proposal. The owner's
explicit legacy FDR/DPS closing removal is the only automatic wording exception.
English must follow the selected Bangla meaning; stale English reference endings
must not override edits to the Bangla master. Display text remains separate from
the exact spoken-number script. Record the selected master section and review
hash in the activated manifest, and reuse only matching text/script/audio hashes.

## Conversation playback and recovery

Saved-answer URLs use the same strict audio allowlist in the ordinary player
and the conversation player. A successful spoken answer resumes recording even
when its text has no closing question. First-use permission still requires user
action; Finish, Stop, navigation, typing recovery and playback failures suspend
automatic recording. An idle microphone is not an invitation to repeat a generic
question after a completed answer. iOS selects recording mode before resuming
the audio context after playback.

A verified saved answer clears earlier recognition misses and exits typing
recovery. Successfully resolved early replies do likewise; provider failures
retain the previous miss count instead of treating network errors as user misses.
Two-bank overview requests include both named banks. A two-bank comparison with
no product compares sourced condition, not an invented default FDR request.
An explicit product comparison continues to use the published product facts.
Interest-versus-profit definitions are general glossary explanations, independent
of the previous bank or product. These changes do not alter transcription models,
provider audio input, financial source values or the approved recordings.

An explicit conjunction such as “এবং” or “and” preserves two separate bank
mentions even when one ASR spelling has lower confidence than the other.
Uncertain pairs are proposed together for exact yes/no confirmation; they are
never presented as an either/or bank choice. Only acceptance enables the pair's
financial response. Rejection keeps the previous bank and requests both names
again. A new question clears stale pair confirmation. A conjunction inside an
exact full bank name is not split into separate institutions. Bangla overview
wording includes “সম্বন্ধে বলবেন”. These rules do not add ASR aliases or relax
financial-answer confidence thresholds.

An explicit account-information request clears an inherited DPS product and term.
It asks whether the user wants savings interest, account fees or debit-card
information, with matching spoken and tappable choices. Short follow-up replies
retain the bank. A visible topic label shows the selected account scope and is
cleared on unrelated answers. Fee responses use the existing sourced account
catalog, explicitly label the fixed one-lakh example and leave unavailable fees
unknown. Approved recordings and transcription remain unchanged.
