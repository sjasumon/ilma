# Repository review resolution — 27 October 2026

The original review stays on the shared workspace and is excluded from Git.
Corrections are normal new commits; existing history is preserved.

| Finding | Resolution |
| --- | --- |
| Published history must not change | Recorded in root AGENTS.md. Pre-push verifies the published anchor and rejects non-fast-forward updates/deletions. Approved author/committer and commit attribution are checked. Repository squash/rebase merge buttons are disabled. |
| Raw export copied into tests | Removed `tests/fixtures/export_v5_2/`. Originals remain private on the share. Replaced with handwritten three-bank synthetic examples; the production nine-bank loader/baseline is unchanged. |
| Non-neutral internal review wording | Renamed the metric to `requires_manual_review`, sanitized public specs, removed private planning links, and added a current-tree policy check. |
| README/public presentation | Rewritten around the bank-information pitch, Meta event/model roles, live/video links, three real screenshots, current demo status and honest prior-work disclosure. Host details live in ops/RUNBOOK.md. |
| Untidy public tree | Moved specs to docs/specs, renamed the pre-event FRD to docs/FRD.md, replaced the stale build plan and removed debug screenshots/handoff files. Shared originals are archived privately. |
| Missing feature work | Tracked in BUILD_PLAN.md: approved v6.1 incidents, Proof Snap vision/SAM, WhatsApp, SMS, Android decision, native/device acceptance and demo video. No planned feature is claimed delivered. |
| Provider settings | Verified exact transcription/chat URLs and model IDs against official Meta documentation. Standard-mode privacy guards now explain why they exist. |
| Incomplete test instructions | README installs requirements-dev.txt and runs pytest plus all five frontend suites. Added CI using pinned action revisions and verified Gitleaks installation. |

## Evidence

- 76 Python tests and 25 subtests pass, including tiny converter and public-tree
  regression checks. Five Node suites pass.
- Full-history Gitleaks 8.30.1 scan over all reachable refs passes. No historical
  data was rewritten to obtain this result.
- Current tracked files have no disallowed review-brand terms; commit identities
  remain `sjasumon <me@sumon.me>` and messages have no co-author trailers.
- The pre-event collection tool/raw exports remain outside the current public
  tree. Historical public-export fixtures remain reachable in old commits, as
  requested. Financial rows are still labelled accurately as pending manual review.

## Pending decisions / unavailable inputs

- **License:** asked Sumon to choose MIT or Apache-2.0; no license is assigned
  without his decision. Add LICENSE immediately after that response.
- **Incident archive:** the referenced `ilma_incidents_input_v6.1.zip` is not in
  this project or the checked shared export locations. Obtain the approved input;
  validate sources, supported-bank scope and status windows before importing.
  Do not change thresholds or fabricate a high-risk card to fill the gap.
- **Remote history protection:** GitHub returned HTTP 403: private-repository
  branch protection requires a paid plan or public visibility. The repository
  remains private. Local hooks and CI do not replace server-side protection;
  enable it when the plan/visibility permits. No visibility change was made.
- **Submission work:** demo video, Android packaging decision and the roadmap's
  unimplemented capabilities remain explicitly pending.

See REPOSITORY_POLICY.md for reproducible checks and persistent safeguards.
