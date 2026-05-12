#!/usr/bin/env bash
# /usr/local/sbin/openbox-tor-check.sh
# OpenBox v0.1 — verifica circuito Tor via check.torproject.org
set -euo pipefail
shopt -s inherit_errexit

readonly NTFY="/usr/local/sbin/openbox-ntfy-send.sh"

RESPONSE="$(curl --max-time 30 \
  --socks5-hostname 127.0.0.1:9050 \
  -s https://check.torproject.org/api/ip 2>/dev/null || echo '{"IsTor":false,"error":"curl_failed"}')"

# [SEC-003] Strip control chars and truncate to prevent log injection / arg overflow.
SAFE_RESPONSE="$(printf '%s' "${RESPONSE}" | tr -d '\000-\037' | head -c 200)"

if echo "${SAFE_RESPONSE}" | grep -q '"IsTor":true'; then
  logger -t openbox-tor-check "OK: ${SAFE_RESPONSE}"
  exit 0
else
  logger -t openbox-tor-check "FAIL: ${SAFE_RESPONSE}"
  [[ -x "${NTFY}" ]] && "${NTFY}" "openbox-alerts" "Tor circuit FAIL: ${SAFE_RESPONSE}" || true
  exit 1
fi
