# Reviewed deposit recordings

Fourteen owner-approved Bangla scripts contain 9,939 characters. The supplied text is used verbatim, without model rewriting or pronunciation substitution. The owner explicitly retained the three-month introduction as supplied; its rounded upper range says 2,100 while its following SBAC example says 2,125. On-screen calculations retain the exact calculated amounts.

Final recordings use `static/audio/services/bn/deposit_{slot}.mp3` and merge into the existing services manifest, preserving all 31 card entries. Each entry binds the exact text hash, source-catalog hash, audio hash and fixed example. Generation tries the configured primary, secondary and tertiary speech accounts in order, allowing 120 seconds per account for offline generation. Runtime speech retains its existing deadline.

Playback requires unchanged source facts and the approved amount and term: FDR/savings 100,000 taka, DPS 5,000 taka monthly. Another approved term selects its own recording. Unsupported examples expose text rather than a mismatched recording. Amounts remain in browser memory and are neither transmitted nor stored.

Contextual products mentioned in a narration have separate source-linked references. Reference-only products do not join ranked calculations. NCC NXT remains eligibility-unverified and excluded from the general savings calculation. General and NRB savings recordings appear in the unified accounts view under a savings-interest label; these recordings do not claim to narrate debit-card or SMS costs.

File integrity and browser playback checks do not constitute a native-speaker listening review. Physical-device and assistive-technology acceptance remain separate.
