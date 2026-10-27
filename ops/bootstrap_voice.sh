#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Reuse the project's existing/activated environment. Never create a second venv.
ILMA_VENV_PATH="${ILMA_VENV_PATH:-${VIRTUAL_ENV:-}}"
if [[ -z "$ILMA_VENV_PATH" ]]; then
  ILMA_VENV_PATH="$(python3 -c 'import sys; print(sys.prefix if sys.prefix != sys.base_prefix else "")')"
fi
if [[ -z "$ILMA_VENV_PATH" ]]; then
  for candidate in "$PWD/.venv" "$PWD/venv"; do
    if [[ -f "$candidate/pyvenv.cfg" ]]; then ILMA_VENV_PATH="$candidate"; break; fi
  done
fi
if [[ -z "$ILMA_VENV_PATH" || ! -x "$ILMA_VENV_PATH/bin/python" ]]; then
  printf '%s\n' 'Activate your existing venv or set ILMA_VENV_PATH to its directory.' >&2
  exit 2
fi
printf 'Using existing venv: %s\n' "$ILMA_VENV_PATH"
"$ILMA_VENV_PATH/bin/python" -m pip install -r requirements.txt
export PYTHONPATH="$PWD/api"
"$ILMA_VENV_PATH/bin/python" -m ilma_api.migrate_voice
"$ILMA_VENV_PATH/bin/python" -m ilma_api.voice_doctor || true
printf '%s\n' 'Dependencies and migration completed. Read readiness output above.' 'Generate clips, obtain native review, and run replay/phone checks in docs/VOICE_ACCEPTANCE.md.'
