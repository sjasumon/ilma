# Exact numbers in generated speech

A displayed answer and its speech input are different artifacts. The reviewed November answer batch submitted displayed Bangla digits, decimal points, percentages and grouped amounts directly to synthesis. File hashes, decoding and browser playback did not establish that the voice read those values correctly. Number-bearing recordings need listening review before production promotion.

For new speech inputs, `exact_speech_numbers.prepare` spells each number explicitly in the selected language and returns an auditable map of the original numeric value to its spoken words. The display text stays unchanged. Decimal digits, including zeros, are retained exactly: no ratio rounding is used. Lists retain their separators; ranges are distinguished from negative values. Years and money amounts are spelled as integers, retaining the original scale/unit words.

Examples: `৭.২৫%` becomes `সাত দশমিক দুই পাঁচ শতাংশ`; `২.০৩%` becomes `দুই দশমিক শূন্য তিন শতাংশ`; `১০০০০ টাকা` becomes `দশ হাজার টাকা`. This avoids leaving number interpretation to synthesis. It does not guarantee that a generative voice will perform the script perfectly.

ElevenLabs recommends fully writing out numbers, dates and symbols when pronunciation matters: https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/why-are-numbers-dates-symbols-and-acronyms-not-properly-pronounced-or-spoken-in-the-correct-language

Four private diagnostic samples use this explicit-number script. They are not replacements for the published recordings yet. ASR back-transcription is supporting diagnostic evidence, not a native-speaker listening pass. Keep pilot audio and detailed diagnostics outside the published tree; approve the spoken result before another full recording batch. Both the display-text hash and exact TTS-text hash must identify a replacement recording so an older cached numeric performance cannot be reused accidentally.
