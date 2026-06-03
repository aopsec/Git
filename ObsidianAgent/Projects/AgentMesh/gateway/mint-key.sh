#!/usr/bin/env bash
# Mint a scoped, budgeted LiteLLM virtual key for a user/agent.
#   Usage: ./mint-key.sh <alias> [budget_usd] [duration]   e.g. ./mint-key.sh alice 10 30d
# Prints the new sk-... key (hand it to that user; the master key stays in .env).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ALIAS="${1:?usage: mint-key.sh <alias> [budget_usd] [duration]}"
BUDGET="${2:-10}"
DUR="${3:-30d}"
GW_URL="${MESH_GATEWAY_URL:-http://127.0.0.1:4000}"
MK="$(grep '^LITELLM_MASTER_KEY=' "$HERE/.env" | cut -d= -f2-)"
[ -n "$MK" ] || { echo "[ERROR] LITELLM_MASTER_KEY not found in $HERE/.env" >&2; exit 1; }
curl -fsS "$GW_URL/key/generate" -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' \
  -d "{\"key_alias\":\"$ALIAS\",\"models\":[\"qwen2.5-coder\",\"hermes3\"],\"max_budget\":$BUDGET,\"budget_duration\":\"$DUR\"}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('alias=%s  key=%s  budget=%s/%s'%(d.get('key_alias'),d.get('key'),d.get('max_budget'),d.get('budget_duration')))"
