#!/usr/bin/env bash
set -euo pipefail

api_url="${API_URL:-http://127.0.0.1:8000}"
symbol="${1:-RELIANCE}"
exchange="${2:-NSE}"

printf 'Backend health: '
curl --fail --silent --show-error "${api_url}/health" >/dev/null
printf 'PASS\n'

printf 'EODHD configuration:\n'
curl --fail --silent --show-error \
  "${api_url}/api/v1/fundamentals/providers/eodhd/status" \
  | python -m json.tool

printf 'Syncing %s.%s:\n' "${symbol}" "${exchange}"
curl --fail --silent --show-error \
  -X POST "${api_url}/api/v1/fundamentals/providers/eodhd/sync" \
  -H 'Content-Type: application/json' \
  -d "{\"symbols\":[\"${symbol}\"],\"exchange\":\"${exchange}\"}" \
  | python -m json.tool

printf 'Stored snapshot:\n'
curl --fail --silent --show-error \
  "${api_url}/api/v1/fundamentals/${symbol}" \
  | python -m json.tool
