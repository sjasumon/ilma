# Persistent project instructions

These instructions record Sumon's repository-review requirements of 27 October
2026. Read them before editing, committing or publishing this project.

- Preserve published history. Create normal new commits only. Never force-push,
  recreate the repository, squash published work, or amend/rebase pushed commits.
  Keep the current published history reachable; commit dates are event evidence.
- Use the configured author/committer `sjasumon <me@sumon.me>`. Do not add
  co-author trailers or coding-assistant attribution. Use neutral manual-review
  terminology in public code, fixtures, documents and commit messages.
- Keep the pre-event collection tool, raw source exports, scraper metadata,
  private reviews, agent handoffs, credentials, recordings, dumps and audio drafts
  outside the published tree. Test converters with tiny handwritten synthetic
  fixtures. Do not copy the supplied export into tests again.
- Preserve private original documents on the shared workspace when reorganizing
  public docs. Public specifications belong in `docs/specs/`; the pre-event FRD
  belongs at `docs/FRD.md`. Keep deployment-specific details in `ops/RUNBOOK.md`.
- Be accurate about provenance and completion. Data collected before the event is
  prior work. Do not describe agent-imported data as manually checked. Never
  invent warning cases, incident evidence, insurance facts, or test results.
- ILMA provides information, not financial advice or safety guarantees. Keep
  planned features clearly separate from implemented behavior.
- Use only the `ilma` MySQL database. Never fall back to another project's DB.
  Keep `.env` private, ignored and mode 0600; never print its values.
- Before every push: inspect the complete staged file list, run the documented
  Python and frontend suites, run repository policy checks and a full-history
  redacted secrets scan. Install the versioned pre-push hook. Never bypass it.
- Push completed updates to GitHub as requested by Sumon, using fast-forward
  pushes. Report remaining source/device/accessibility acceptance honestly.
- Ask Sumon for the license choice; do not assign a public license silently.
