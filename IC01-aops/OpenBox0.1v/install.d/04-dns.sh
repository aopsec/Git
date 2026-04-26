#!/usr/bin/env bash
# install.d/04-dns.sh — dnscrypt-proxy + Pi-hole
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"
PIHOLE_ADMIN_PORT="${OPENBOX_PIHOLE_ADMIN_PORT:-8081}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

install_dnscrypt_socket_override() {
  local target="/etc/systemd/system/dnscrypt-proxy.socket.d/openbox-listen.conf"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    # [FIX-AUDIT-DRYRUN] Skip override creation while simulating.
    printf 'DRY: write %s\n' "${target}"
    return 0
  fi
  cat > "${target}" <<'EOF'
[Socket]
ListenStream=
ListenDatagram=
ListenStream=127.0.0.1:5053
ListenDatagram=127.0.0.1:5053
EOF
  chmod 0644 "${target}"
}

# dnscrypt-proxy 2 primeiro
run env DEBIAN_FRONTEND=noninteractive apt install -y dnscrypt-proxy

# Override do socket para nao conflitar com Pi-hole FTL (porta 53 fica para Pi-hole)
run mkdir -p /etc/systemd/system/dnscrypt-proxy.socket.d
install_dnscrypt_socket_override

run install -m 0644 "${OPENBOX_ROOT}/etc/dnscrypt-proxy/dnscrypt-proxy.toml" /etc/dnscrypt-proxy/dnscrypt-proxy.toml
run systemctl daemon-reload
run systemctl enable --now dnscrypt-proxy

# Pi-hole 6.x — install manual (download + verify + inspect)
if ! command -v pihole >/dev/null; then
  echo "[04-dns] Pi-hole nao instalado. Para instalar:"
  echo "         curl -sSL https://install.pi-hole.net -o /tmp/pihole-install.sh"
  echo "         less /tmp/pihole-install.sh    # INSPECIONAR antes de executar"
  echo "         sudo bash /tmp/pihole-install.sh"
  echo "         Durante setup: Upstream DNS = Custom 127.0.0.1#5053"
  echo "         [FIX-AUDIT-PROXY] Configure tambem o admin web em 127.0.0.1:${PIHOLE_ADMIN_PORT}"
  echo "         para que o Caddy possa publicar /pihole sem conflito com :80/:443."
elif ! ss -tln 2>/dev/null | grep -Eq "127\\.0\\.0\\.1:${PIHOLE_ADMIN_PORT}|\\[::1\\]:${PIHOLE_ADMIN_PORT}"; then
  echo "[04-dns] AVISO: Pi-hole instalado, mas o admin web nao parece bound em 127.0.0.1:${PIHOLE_ADMIN_PORT}."
  echo "         O proxy /pihole do Caddy assume esse upstream local dedicado."
fi

# Cron leak test diario
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-dnsleak-check.sh" /usr/local/sbin/openbox-dnsleak-check.sh
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-dnsleak-check.service" /etc/systemd/system/openbox-dnsleak-check.service
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-dnsleak-check.timer" /etc/systemd/system/openbox-dnsleak-check.timer
run systemctl daemon-reload
run systemctl enable --now openbox-dnsleak-check.timer

echo "[04-dns] OK"
