# Repository publishing safeguards

Sumon's 27 October review is retained privately on the shared workspace. Public
corrections use new commits; existing commits and dates are preserved.

## Install the checks in a full clone

```sh
python3 ops/install_gitleaks.py
git config ilma.gitleaksPath "$PWD/.tools/gitleaks"
git config core.hooksPath ops/hooks
chmod +x ops/hooks/pre-push
python3 ops/check_repo.py --with-secrets
```

The installer pins Gitleaks 8.30.1 and verifies the official release checksum.
The pre-push hook checks the public tree, approved author/committer, neutral
review terminology, the existing published-history anchor, a clean worktree and
fast-forward updates, then scans every reachable commit with redaction. A failed
check must be resolved; never bypass the hook or rewrite published history.

The GitHub workflow runs development-dependency installation, all Python and
frontend tests, repository policy and the same secrets scan on pushes/PRs.
The Python test command is pytest; unittest discovery does not run all checks.

## Public/private boundary

- Publish application implementation, normalized seed CSVs, selected app
  screenshots, sanitized specifications and tiny handwritten synthetic fixtures.
- Keep the separate pre-event collection tool and raw export private. Do not
  include collection paths, run identifiers, source-file hashes or scraper
  metadata in fixtures. Do not copy real source-export rows as a shortcut.
- Keep original private planning documents, review reports, agent handoffs and
  debug screenshots on the share, outside the Git tree. The current archived
  originals are under ignored `private-reference/`.
- Credentials, diagnostic recordings, database dumps and audio drafts remain
  ignored. Do not stage them explicitly. Inspect staged filenames before commit.
- Do not claim imported financial rows have been personally reviewed. Keep
  `checked_by` provenance and unavailable states honest.

Old commits contain the removed public export fixtures and historical planning
wording. Leave those commits unchanged. The current-tree cleanup and accurate
README disclosure address the review without replacing event evidence.

## Before the demo submission

Confirm the README's live/video links, license choice, source review and planned
feature list. Keep deployment internals out of the public tree. Re-run the full
checks from a fresh clone and retain their results. If the approved incident
archive is unavailable, track the gap; never invent a high-risk example.
