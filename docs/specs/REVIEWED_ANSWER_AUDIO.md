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
