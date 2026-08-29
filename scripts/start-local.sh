#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add your rotated values, then run this command again."
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -e services/api
python -m pip install -r services/api/requirements-broker.txt

cleanup() {
  if [[ -n "${api_pid:-}" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir services/api &
api_pid=$!

pnpm --filter @allinone/web dev
