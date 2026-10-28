# Approved v6.2 incident supplement

Sumon supplied the v6.2 archive on 27 October 2026 to replace the previously
missing v6.1 incident input. The original ZIP and collector metadata remain
private. These CSVs are curated application data, not raw collector exports.
Imported rows carry `agent-v6.2`; they are **not** personally checked by Sumon.

The supplement adds National Bank and Islami Bank to the nine-bank catalogue.
Existing rule thresholds are unchanged. Audited 2025 capital ratios support
High status for both banks; National Bank also has a sourced bad-loan ratio and
loss. National Bank's negative capital ratio is preserved. Profit is already
in BDT in the input; it is not multiplied a second time. Islami Bank has no
explicit bad-loan ratio. On 28 October 2026 Sumon approved publishing one
calculated from the two amounts quoted in the auditor's opinion (page 1):
classified investments Tk 94,322.59 crore ÷ gross investment Tk 189,951.52
crore = 49.66%. The row has basis `solo_calculated`, quotes both inputs and is
shown as "calculated from the auditor's report"; the loader recomputes it.
Ratings preserve the supplied agency, dates and Developing outlook. From rules
`2026.10-v2`, a developing outlook is a Watch-type reason ("outlook uncertain").

There are 19 incident records, 41 sources (34 incident links) and 23 dated status updates.
The single-source City Bank embezzlement item is excluded. The Islami Bank
2022 probe and Prime Bank 2014 charge-sheet approval are conservatively
published as reported; the quoted evidence does not establish the supplied
filed/charged labels. See `review_notes.json` for these decisions.

Primary documents and newspaper allegations are labeled separately. A bank's
auditor disclosure is not automatically a regulator's finding. The Islami
Bank court notice concerns an AGM, not a fraud judgment. All incident rows
have `status_effect=false`: historical records do not silently change current
financial status. Alleged incident amounts are not aggregated or published.

No searched start/end window was supplied. The interface identifies the range
of provided records separately and explicitly says it is not a complete
history. No supplied records does not establish absence of cases.

## Source checks and limits

National Bank's negative 2025 capital ratio was independently corroborated in
[DSE's auditor opinion, page 1](https://www.dsebd.org/Auditors_opinion/2025/206.%20National%20Bank%20PLC25.pdf).
Islami Bank's 6.42% ratio matches the indexed primary
[CSE auditor opinion, page 2](https://www.cse.com.bd/upload_media/ISLAMIBANK_2025.pdf).
The CSE full fetch timed out. National Bank's annual-report fetch failed in
this environment; its bad-loan/profit source context, page 16 and last 2025
column are retained from the supplied archive. Rating exchange pages returned
JavaScript shells, so supplied rating excerpts were retained without claiming
independent reconfirmation. Incident links/excerpts need final human source
review; they are not comprehensive legal findings.

## Import

Load the original normalized seed first, then this supplement:

```sh
PYTHONPATH=api /path/to/venv/bin/python -m ilma_api.seed_loader seed
PYTHONPATH=api /path/to/venv/bin/python -m ilma_api.incident_loader seed/incidents
```

The supplemental loader validates references, domains, source counts, dates,
quoted figures and unchanged original statuses before committing. It only
accepts MySQL database `ilma` (SQLite is used in isolated tests). Reimport is
idempotent and preserves unchanged manual reviews. Service comparisons still
cover the original nine banks (the later v5.4 refresh has 606 service attributes); no service terms are
invented for the two new banks.
