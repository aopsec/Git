#!/usr/bin/env bash
# install.d/08-watchdogs.sh — WG, Tor, DNS leak, ntfy
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

# Helper ntfy-send
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-ntfy-send.sh" /usr/local/sbin/openbox-ntfy-send.sh

# WireGuard watchdog
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-wg-watchdog.sh" /usr/local/sbin/openbox-wg-watchdog.sh
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-wg-watchdog.service" /etc/systemd/system/openbox-wg-watchdog.service
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-wg-watchdog.timer" /etc/systemd/system/openbox-wg-watchdog.timer

run systemctl daemon-reload
if [[ "${DRY_RUN}" -eq 1 ]]; then
  # [FIX-AUDIT-WG] Keep the watchdog disabled until wg0 is intentionally enabled.
  printf 'DRY: conditionally enable openbox-wg-watchdog.timer after wg-quick@wg0.service is enabled\n'
elif systemctl is-enabled --quiet wg-quick@wg0.service; then
  run systemctl enable --now openbox-wg-watchdog.timer
else
  echo "[08-watchdogs] AVISO: wg-quick@wg0 ainda nao habilitado; watchdog instalado mas nao ativado."
fi

echo "[08-watchdogs] OK"
