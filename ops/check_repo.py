"""Check public-tree policy and optionally scan every reachable Git commit."""
import argparse
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

AUTHOR = 'sjasumon <me@sumon.me>'
LEGACY_AUTHOR = 'sjasumon <5217484+sjasumon@users.noreply.github.com>'
# Existing history at the identity change; never rewrite published commits.
# These immutable tips do not permit the old identity on new descendants.
LEGACY_IDENTITY_TIPS = (
    '9ce0f263694c4f1ced9393e3aca0bccd93c9164e',
    '4a524feab585b3c7d2f6a229c216e85d24693bfa',
)
PUBLISHED_ANCHOR = 'b76ec330ca1dd1bda8d35c5e41020a75f0e1b82e'
# Split the definitions so this self-scanning policy does not match its own text.
UNAPPROVED_BRANDS = ('cl' + 'aude', 'anth' + 'ropic')
PRIVATE_PREFIXES = ('private-reference/', 'bank and bank service menu/',
    'ilma-agent/', 'ilma_waveform_agent_handoff/', 'tests/fixtures/export_v5_2/',
    'voice-diagnostics/', 'voice-backups/', 'voice-drafts/', 'audio/', 'feedback/', 'muse/')
DEBUG_ASSETS = {'design/error.png', 'design/error1.png', 'design/e1.png', 'design/search.png'}
PRIVATE_COLUMNS = {'local_path', 'sha256', 'obtained_by', 'run_id', 'article_text'}


def git(repo, *arguments, check=True):
    return subprocess.run(['git', '-C', str(repo), *arguments], check=check,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def identity_allowed(commit, author, committer, legacy_commits):
    allowed = {AUTHOR}
    if commit in legacy_commits:
        allowed.add(LEGACY_AUTHOR)
    return author in allowed and committer in allowed


def tree_errors(files):
    """files maps tracked paths to bytes; errors never include file contents."""
    errors = []
    for name, content in files.items():
        path = Path(name)
        if (name.startswith(PRIVATE_PREFIXES) or name.startswith(('ilma_incidents_input_','ilma_seed_input_','ilma_extra_input_','docs/FIX_','docs/AGENT_INSTRUCTIONS_HUMAN_VOICE_')) or name in DEBUG_ASSETS or
            path.name.startswith(('REPO_REVIEW_', 'WEBSITE_REVIEW_', 'CODE_REVIEW_', 'WEBSITE_FULL_TEST_', 'TAP_OR_TALK_FIXES_')) or name in {'docs/review_muse.md','docs/APP_SPEC_07_voice_agent.md','docs/APP_SPEC_08_speed.md', 'docs/FIX_09_language_and_loop.md', 'docs/FIX_10_answer_wording.md', 'docs/FIX_11_speech_wording_and_pronunciation.md', 'docs/AGENT_INSTRUCTIONS_HUMAN_VOICE_AGENT.md'} or (path.name.startswith('.env') and path.name != '.env.example') or
            name.endswith(('.sql', '.sql.gz'))):
            errors.append(f'Private/unwanted path tracked: {name}')
        try:
            source = content.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if any(word in source.casefold() for word in UNAPPROVED_BRANDS):
            errors.append(f'Non-neutral review terminology: {name}')
        if name.startswith('tests/fixtures/') and name.endswith('.csv'):
            header = next(csv.reader(io.StringIO(source)), [])
            if PRIVATE_COLUMNS.intersection(header):
                errors.append(f'Collection metadata in fixture: {name}')
        if name == '.env.example':
            for line in source.splitlines():
                if '=' not in line or line.lstrip().startswith('#'):
                    continue
                key, value = line.split('=', 1)
                if re.search(r'(API_KEY|PASSWORD|DB_PASS|LOG_SALT|VOICE_ID)$', key.strip()) and value.strip().strip("'\""):
                    errors.append('Secret placeholder is populated in .env.example')
    return errors


def check(repo, with_secrets=False, pre_push=False):
    errors = []
    if git(repo, 'merge-base', '--is-ancestor', PUBLISHED_ANCHOR, 'HEAD', check=False).returncode:
        errors.append('Published history anchor is not reachable from HEAD.')
    legacy_commits = set(git(repo, 'rev-list', *LEGACY_IDENTITY_TIPS).stdout.decode().splitlines())
    identities = git(repo, 'log', '--all', '--format=%H%x00%an <%ae>%x00%cn <%ce>').stdout.decode().splitlines()
    if any(not identity_allowed(*row.split('\0'), legacy_commits) for row in identities):
        errors.append('Commit author/committer differs from the approved project identity.')
    messages = git(repo, 'log', '--all', '--format=%B').stdout.decode()
    if re.search(r'co-authored', messages, re.I) or any(word in messages.casefold() for word in UNAPPROVED_BRANDS):
        errors.append('Commit messages contain disallowed attribution.')
    names = git(repo, 'ls-files', '-z').stdout.decode().split('\0')
    files = {name: (repo / name).read_bytes() for name in names if name and (repo / name).is_file()}
    errors.extend(tree_errors(files))
    if pre_push:
        if git(repo, 'status', '--porcelain').stdout.strip():
            errors.append('Commit/review pending tracked or untracked changes before pushing.')
        for line in sys.stdin:
            local_ref, local_sha, remote_ref, remote_sha = line.split()
            if set(local_sha) == {'0'}:
                errors.append('Branch deletion is blocked; preserve published event evidence.')
            elif set(remote_sha) != {'0'} and git(repo, 'merge-base', '--is-ancestor', remote_sha, local_sha, check=False).returncode:
                errors.append('Non-fast-forward push blocked. Fetch and preserve the remote history.')
    if with_secrets:
        configured = os.getenv('ILMA_GITLEAKS') or git(repo, 'config', '--get', 'ilma.gitleaksPath', check=False).stdout.decode().strip()
        binary = configured or shutil.which('gitleaks')
        if not binary:
            errors.append('Gitleaks is required: run ops/install_gitleaks.py and configure ilma.gitleaksPath.')
        else:
            result = subprocess.run([binary, 'git', str(repo), '--log-opts=--all', '--redact', '--no-banner'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Scanner output can contain context despite redaction: print only the result.
            if result.returncode:
                errors.append('Full-history secrets scan failed. Review redacted scanner output privately; do not rewrite history.')
            else:
                print('Full-history secrets scan passed.')
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print('Repository policy checks passed.')
    return not errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--with-secrets', action='store_true')
    parser.add_argument('--pre-push', action='store_true')
    args = parser.parse_args()
    try:
        raise SystemExit(0 if check(args.repo.resolve(), args.with_secrets or args.pre_push, args.pre_push) else 1)
    except (subprocess.SubprocessError, OSError, ValueError):
        raise SystemExit('Repository check could not complete. Use a full Git checkout and inspect configuration privately.') from None
