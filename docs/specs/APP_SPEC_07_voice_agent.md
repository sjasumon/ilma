# Guided voice agent

Normal Home opens by default. Guided Voice only is opt-in through Settings;
the saved switch, rather than first-use completion, controls activation.

The Home flow uses a stateless conversation with allowlisted tools. Models can
select a tool and word its sourced result; deterministic rules and stored data
supply all statuses, numbers, fees and rates. No model decides bank condition.

The server script follows BANK → DETAIL or SERVICES, then FIGURES/HISTORY,
SERVICE, COMPARE, NEXT and ASK_BANK. A watch request adds a separate yes/no
confirmation. Services offers FDR/DPS and two additional visible product buttons.
There are at most two tap-count choices; product names can also be spoken.
A conversation ends after six turns. Full report opens only on request.

`POST /v1/ask` accepts existing multipart text or a discrete `choice` field,
and JSON `{choice, context}` for taps. Both `/v1/voice` and `/v1/ask` accept
`context.agent=true` and a validated `context.conversation`. The result is
`type=agent_turn`, with sentences, fact IDs and source objects, checked wording
mode, scripted next question/options, updated conversation, optional speech,
and five inspection steps. Send the returned conversation unchanged next turn.
No transcript or conversation state is stored by this feature.

The tools are bank summary, reasons, figures, history, service overview/detail/
comparison, insurance, proof, watch and end. Institution IDs must be matched or
contextual; comparison selections are recomputed against the same database
cohort. Products, terms, card tiers and networks are validated enums/bounds.
Models cannot supply SQL, URLs or arbitrary tool text. Watch writes require an
explicit yes from the user and the existing device-scoped watch identity.

PLAN uses Muse Spark for free-form replies, with deterministic aliases and
script replies as fallback. Single bank names and tap choices skip PLAN. Tap
turns also skip SAY/CHECK and use sourced templates. For model wording, the
code checks citations, numbers, percentages, names, vocabulary and advice words;
a separate CHECK call must pass before `checked=model` is returned. Rejection,
unavailability or malformed output uses a template. `MUSE_CHECK_MODEL` selects
the checker; empty uses the same configured Spark model for a separate call,
not a claim of an independent model family. Only call metadata is logged.

Home keeps conversation state in memory, clears it on tab changes and after two
minutes idle, and opens a six-second microphone window after successful speech
playback. Silence re-asks the question once after eight seconds, then waits.
The existing guided-mode tap timing distinguishes two choices from a recording
stop pair. Explicit option buttons work without physical tap counting.

Target: a short spoken summary and follow-up in less than twenty seconds of
audio. Real provider/device timing and native accessibility acceptance remain
separate from synthetic tests. A highlighted original-page snapshot service is
not available: proof uses the existing quoted source sheet and original link,
with the missing image stated explicitly. Source/manual financial review remains
pending wherever the underlying data already marks it pending.
