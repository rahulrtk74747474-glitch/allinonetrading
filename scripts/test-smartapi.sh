#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

required_vars=(
  ANGELONE_API_KEY
  ANGELONE_CLIENT_ID
  ANGELONE_PIN
  ANGELONE_TOTP_SECRET
)

environment_ready=true
for variable_name in "${required_vars[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    environment_ready=false
  fi
done

if [[ ! -f .env && "$environment_ready" != "true" ]]; then
  echo "SmartAPI credentials are not available."
  echo "Create the private, git-ignored file with:"
  echo "  cp .env.example .env"
  echo "  code .env"
  echo "Add rotated credentials to .env, save it, and rerun this script."
  exit 1
fi

if [[ -f .env ]]; then
  chmod 600 .env
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --disable-pip-version-check -q -e services/api
python -m pip install --disable-pip-version-check -q -r services/api/requirements-broker.txt

test_port="${SMARTAPI_TEST_PORT:-8010}"
test_symbol="${SMARTAPI_TEST_SYMBOL:-RELIANCE-EQ}"
test_token="${SMARTAPI_TEST_SYMBOL_TOKEN:-2885}"
test_exchange="${SMARTAPI_TEST_EXCHANGE:-NSE}"
test_url="http://127.0.0.1:$test_port"

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/allinonetrading-smartapi.XXXXXX")"
api_pid=""

cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT INT TERM

PYTHONUNBUFFERED=1 python -m uvicorn app.main:app   --host 127.0.0.1   --port "$test_port"   --app-dir services/api   >"$temp_dir/api.log" 2>&1 &
api_pid=$!

api_ready=false
for _ in {1..40}; do
  if curl --silent --fail "$test_url/health" >"$temp_dir/health.json"; then
    api_ready=true
    break
  fi
  sleep 0.5
done

if [[ "$api_ready" != "true" ]]; then
  echo "Backend did not start. Safe log tail:"
  tail -n 40 "$temp_dir/api.log"
  exit 1
fi

curl --silent --fail   "$test_url/api/v1/broker/status"   >"$temp_dir/configuration.json"

curl --silent --fail   --request POST   "$test_url/api/v1/broker/read-only-connect"   >"$temp_dir/login.json"

curl --silent --fail   --request POST   --header "Content-Type: application/json"   --data "{\"exchange\":\"$test_exchange\",\"symbol\":\"$test_symbol\",\"symbol_token\":\"$test_token\"}"   "$test_url/api/v1/market/ltp"   >"$temp_dir/ltp.json"

python -   "$temp_dir/configuration.json"   "$temp_dir/login.json"   "$temp_dir/ltp.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path


def read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


configuration = read_json(sys.argv[1])
login = read_json(sys.argv[2])
ltp_wrapper = read_json(sys.argv[3])

configured = bool(configuration.get("configured"))
login_ok = bool(login.get("status"))

smartapi_response = ltp_wrapper.get("data")
if not isinstance(smartapi_response, dict):
    smartapi_response = {}

quote = smartapi_response.get("data")
if not isinstance(quote, dict):
    quote = {}

quote_ok = bool(smartapi_response.get("status")) and quote.get("ltp") is not None

print(f"Backend health: PASS")
print(f"Credentials detected: {'PASS' if configured else 'FAIL'}")
print(f"SmartAPI login: {'PASS' if login_ok else 'FAIL'}")
print(f"Login message: {login.get('message', 'No message returned')}")

if not login_ok:
    if login.get("errorCode"):
        print(f"SmartAPI error code: {login['errorCode']}")
    if login.get("error"):
        print(f"Safe error type: {login['error']}")
    raise SystemExit(2)

print(f"Read-only LTP extraction: {'PASS' if quote_ok else 'FAIL'}")
if quote_ok:
    print(f"Symbol: {quote.get('tradingsymbol', 'unknown')}")
    print(f"LTP: {quote.get('ltp')}")
else:
    print(f"Market-data message: {smartapi_response.get('message', ltp_wrapper.get('message', 'No message returned'))}")
    if smartapi_response.get("errorcode"):
        print(f"Market-data error code: {smartapi_response['errorcode']}")
    if ltp_wrapper.get("error"):
        print(f"Safe error type: {ltp_wrapper['error']}")
    raise SystemExit(3)
PY
