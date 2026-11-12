#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required and was not found on PATH." >&2
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(f"Python 3.10+ is required. Found {sys.version.split()[0]}.")
PY

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is not installed. Installing it for the current user..."
  python3 -m pip install --user poetry
fi

echo "Installing project dependencies..."
poetry install

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add the sandbox API key, secret, and payment page uid before running tests."
fi

cat <<'EOF'

Dependencies are installed. From this folder, run:
  poetry run pytest              # all tests
  poetry run pytest -m api       # API only
  poetry run pytest -m ui        # UI only
  poetry run pytest -m e2e       # end-to-end only
  poetry run pytest --headed     # visible browser
EOF
