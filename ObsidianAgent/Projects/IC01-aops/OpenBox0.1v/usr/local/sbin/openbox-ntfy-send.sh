#!/usr/bin/env bash
# /usr/local/sbin/openbox-ntfy-send.sh
# OpenBox v0.1 — helper para enviar notificacao via ntfy local
# Uso: openbox-ntfy-send.sh <topic> <message> [priority]
set -euo pipefail
shopt -s inherit_errexit

readonly NTFY_URL="${OPENBOX_NTFY_URL:-http://127.0.0.1:2586}"

# [SEC-004] Reject any NTFY_URL that is not a loopback address.
case "${NTFY_URL}" in
  http://127.*|http://localhost*|"http://[::1]"*)
    ;;
  *)
    logger -t openbox-ntfy "Rejected non-local NTFY_URL: ${NTFY_URL}"
    exit 1
    ;;
esac

readonly TOPIC="${1:?topic required}"
readonly MESSAGE="${2:?message required}"
readonly PRIORITY="${3:-default}"

curl -fsS \
  --max-time 5 \
  -H "Title: OpenBox alert" \
  -H "Priority: ${PRIORITY}" \
  -H "Tags: openbox,alert" \
  -d "${MESSAGE}" \
  "${NTFY_URL}/${TOPIC}" >/dev/null 2>&1 || logger -t openbox-ntfy "send failed: ${MESSAGE}"
