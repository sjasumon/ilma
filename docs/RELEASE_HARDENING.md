# Release hardening progress

## Stage 1 — deployed 27 October 2026

All provider-producing POST routes (`voice`, `ask`, `speech`, service `readout`)
now share pre-provider admission: 12 requests/client/minute, 60 global/minute,
1,000 global/day, 2 active/client and 4 active/global. These are configurable
ceilings, not a promise of provider billing limits. Invalid requests also consume
admission. Quotas are process-local and reset on restart: this deployment must
remain one Uvicorn worker/replica until limits move to a shared trusted ingress.
Clients behind a shared address share its allowance. No device-ID or raw
forwarded-header value is used by the middleware.

Disallowed browser origins receive 403 before paid calls; CORS uses an explicit
origin list. Non-browser clients still require admission; CORS is not authentication.
Protected uploads have a 20-second total read deadline and bounded memory;
speech JSON is limited to 16 KiB. Concurrent slots span the complete SSE response
and are released after cancellation or failure.

The host daily cleanup timer is enabled. Its first manual run succeeded and
the next run is scheduled. Cleanup now expires seven-day diagnostic samples and
enforces the 200-sample cap even after capture is disabled or when traffic stops,
alongside ordinary 30-day logs and expired counters. Current recent diagnostics
remain available for investigation; capture stays enabled for the authorized test.

Evidence: 69 Python tests / 25 subtests and five Node suites pass. New tests cover
shared limits, changing device IDs, concurrency, cancellation, oversized/slow
uploads, denied origins and idle expiry with capture disabled. Live health remains
healthy and a disallowed-origin POST returns 403. No provider calls are made by
the rejection tests.

See `PRODUCTION_READINESS.md` for original findings. Its missing-admission and
missing-timer findings are superseded by this stage; other launch gates remain.
