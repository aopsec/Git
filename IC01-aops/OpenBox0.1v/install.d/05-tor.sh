#!/usr/bin/env bash
# install.d/05-tor.sh — Tor hardened
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

run env DEBIAN_FRONTEND=noninteractive apt install -y tor torsocks nyx python3-stem

# Backup do torrc original
[[ -f /etc/tor/torrc.original ]] || run cp /etc/tor/torrc /etc/tor/torrc.original

run install -m 0644 -o debian-tor -g debian-tor "${OPENBOX_ROOT}/etc/tor/torrc.example" /etc/tor/torrc
run tor --verify-config -f /etc/tor/torrc

echo "[05-tor] Controle local usa CookieAuthentication por padrao."
echo "         Para trocar por senha: tor --hash-password 'sua-senha'"

run systemctl restart tor

# Watchdog Tor
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-tor-check.sh" /usr/local/sbin/openbox-tor-check.sh
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-tor-check.service" /etc/systemd/system/openbox-tor-check.service
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-tor-check.timer" /etc/systemd/system/openbox-tor-check.timer
run systemctl daemon-reload
run systemctl enable --now openbox-tor-check.timer

echo "[05-tor] OK"
