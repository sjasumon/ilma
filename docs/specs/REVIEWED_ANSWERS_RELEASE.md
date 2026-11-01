# Reviewed bilingual conversation recordings

The release maps 93 reviewed answers in each language to 186 recording entries. Identical scripts share synthesis; all question IDs retain a recording file. The selected Bangla master uses the owner's edits in the Current/reference sections for Q2, Q8, Q14, Q25, Q36, Q42, Q45, Q53, Q54, Q58, Q62, Q65, Q90 and Q92, and the Proposed sections for the other questions. English endings follow that selected master.

The batch contains 29,871 mapped characters and 176 distinct language/text scripts containing 28,216 synthesis characters. Generation uses the ordered primary, secondary and tertiary speech accounts with 120-second offline deadlines and resumable output. Text is submitted verbatim, without pronunciation rewriting. Audio/file integrity checks are not native listening acceptance.

Final files live under `static/audio/answers/{bn,en}/qNNN.mp3`, with a complete 186-entry manifest. The listening page is `/static/answer-review.html`. It displays the exact text and allows selection of question number and language. Partial batches are never installed into the live manifest.

Runtime selection requires an exact normalized question match, the expected resolved bank/product/term/intent, an unchanged source-fact fingerprint, an exact text hash and a valid audio hash. Short contextual questions retain their opening context: Q85 follows NCC FDR; Q86 follows City savings. Identical question wording can have more than one reviewed answer; selection avoids immediately repeating the same recording key. Unmatched or changed-source questions continue through the sourced answer engine. This is not a semantic guarantee for arbitrary paraphrases.

An exact reviewed answer bypasses the wording-model request. Its saved audio bypasses runtime synthesis and its 30-second short-answer cache constraint, so the approved recording is not truncated. Existing bank, card, deposit, loan and news recording sets are preserved.

The stock FDR/DPS invitation is removed from the runtime next-step defaults and model example. A reviewed answer with no closing question retains reply and navigation controls but does not automatically reopen recording or repeat a silence prompt. A single offered service action accepts yes/no; a yes after multiple alternatives does not silently choose an alternative.

Keep approved source documents, generation inputs, private source snapshots, diagnostic recordings and detailed test outputs outside the published tree. Bindings are hashes and resolved slot metadata, not API credentials or raw data exports. The `ilma` financial tables are not migrated or reseeded for this release. Physical-device and native-speaker listening acceptance must be reported separately from automated text, hash, decoding and browser checks.
