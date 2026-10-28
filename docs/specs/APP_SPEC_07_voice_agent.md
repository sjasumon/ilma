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
A conversation ends after twenty turns; navigation and two-minute idle also reset it. Full report opens only on request.

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

Exact current option labels, their short synonyms and one/two/yes/no resolve
before PLAN and follow the tap path. Explicit product questions bypass PLAN and
use the named bank, or the current conversation bank when none is named.
Unsupported named banks report missing coverage instead of asking which bank.
The [speed specification](APP_SPEC_08_speed.md) supersedes the initial model-call
and timing policy. Simple factual turns and options skip models. Other free
replies use at most one Spark PLAN call with deterministic fallback. All wording
uses sourced templates with local validation; no serial SAY/CHECK requests run.
Only model-call metadata is logged.

Home keeps conversation state in memory, clears it on tab changes and after two
minutes idle, and opens the microphone after successful speech playback. Allow
eight seconds to begin speaking and fifteen seconds total. Silence can re-ask
twice, waiting eight seconds before each re-ask, then remains quiet.
The existing guided-mode tap timing distinguishes two choices from a recording
stop pair. Explicit option buttons work without physical tap counting.

Target: a short spoken summary and follow-up in at most eight seconds of
audio at normal playback. Real provider/device timing and native accessibility acceptance remain
separate from synthetic tests. A highlighted original-page snapshot service is
not available: proof uses the existing quoted source sheet and original link,
with the missing image stated explicitly. Source/manual financial review remains
pending wherever the underlying data already marks it pending.
