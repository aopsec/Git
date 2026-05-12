#!/usr/bin/env bash
# /usr/local/sbin/openbox-wg-watchdog.sh
# OpenBox v0.1 — verifica handshake WireGuard, restart se > THRESHOLD
set -euo pipefail
shopt -s inherit_errexit

readonly IFACE="${OPENBOX_WG_IFACE:-wg0}"
readonly THRESHOLD="${OPENBOX_WG_THRESHOLD:-180}"   # segundos
readonly NTFY="/usr/local/sbin/openbox-ntfy-send.sh"
readonly UNIT="wg-quick@${IFACE}.service"

if ! command -v wg >/dev/null 2>&1; then
  logger -t openbox-wg-watchdog "wg command absent — skipping watchdog"
  exit 0
fi

if ! systemctl is-enabled --quiet "${UNIT}" 2>/dev/null; then
  # [FIX-AUDIT-WG] Do nothing until the operator intentionally enables wg0.
  logger -t openbox-wg-watchdog "${UNIT} disabled — skipping watchdog"
  exit 0
fi

if ! wg show "${IFACE}" >/dev/null 2>&1; then
  logger -t openbox-wg-watchdog "${IFACE} absent — skipping watchdog"
  exit 0
fi

# Pega timestamp do ultimo handshake
LAST="$(wg show "${IFACE}" latest-handshakes 2>/dev/null | awk '{print $2; exit}' || echo 0)"
NOW="$(date +%s)"
AGE=$(( NOW - LAST ))

if (( LAST == 0 )); then
  logger -t openbox-wg-watchdog "no handshake yet — leaving interface untouched"
  exit 0
fi

if (( AGE > THRESHOLD )); then
  logger -t openbox-wg-watchdog "stale handshake (${AGE}s > ${THRESHOLD}s) — restarting"
  systemctl restart "wg-quick@${IFACE}"
  [[ -x "${NTFY}" ]] && "${NTFY}" "openbox-alerts" "WG ${IFACE} stale (${AGE}s) — restart" || true
  exit 2
fi

exit 0
