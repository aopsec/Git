#!/usr/bin/env bash
# install.d/07-monitoring.sh — Netdata, Uptime Kuma, Cockpit, Monit, ntfy, Caddy
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

# [FIX-V7] Shared helpers sourced from _lib.sh — eliminates duplication with 06-media.sh.
# shellcheck source=install.d/_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

# Netdata (kickstart oficial — alternativamente apt install netdata)
if ! command -v netdata >/dev/null; then
  echo "[07-monitoring] Para Netdata: baixar e inspecionar https://my-netdata.io/kickstart.sh antes de executar"
  run env DEBIAN_FRONTEND=noninteractive apt install -y netdata
fi
# Bind localhost
run sed -i 's/^[[:space:]]*bind socket to IP.*/    bind socket to IP = 127.0.0.1/' /etc/netdata/netdata.conf || true
run systemctl enable --now netdata

# Cockpit (socket activation — sem RAM idle)
run env DEBIAN_FRONTEND=noninteractive apt install -y cockpit
run systemctl enable --now cockpit.socket

# Monit
run env DEBIAN_FRONTEND=noninteractive apt install -y monit
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-container-running.sh" /usr/local/sbin/openbox-container-running.sh
run install -m 0600 "${OPENBOX_ROOT}/etc/monit/monitrc.d/openbox.conf" /etc/monit/monitrc.d/openbox
run systemctl enable --now monit

# Caddy
if ! command -v caddy >/dev/null; then
  run env DEBIAN_FRONTEND=noninteractive apt install -y debian-keyring debian-archive-keyring apt-transport-https
  # Pipes — needs shell. Static URLs, no untrusted input.
  run_sh "curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg"
  run_sh "curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list"
  run apt update
  run env DEBIAN_FRONTEND=noninteractive apt install -y caddy
fi
run install -d -m 0750 -o caddy -g caddy /var/log/caddy
run install -m 0644 "${OPENBOX_ROOT}/etc/caddy/Caddyfile" /etc/caddy/Caddyfile
run systemctl reload caddy || run systemctl restart caddy

# Fail2ban
run mkdir -p /etc/fail2ban/filter.d
run install -m 0644 "${OPENBOX_ROOT}/etc/fail2ban/filter.d/caddy-openbox-auth.conf" /etc/fail2ban/filter.d/caddy-openbox-auth.conf
run install -m 0644 "${OPENBOX_ROOT}/etc/fail2ban/jail.d/openbox.conf" /etc/fail2ban/jail.d/openbox.conf
run systemctl enable --now fail2ban
run systemctl reload fail2ban

# Uptime Kuma + ntfy via Docker (mesmo container engine de 06-media)
if command -v docker >/dev/null; then
  if ! docker ps -a --format '{{.Names}}' | grep -q '^uptime-kuma$'; then
    run docker volume create uptime-kuma
    run docker run -d --name uptime-kuma --restart=unless-stopped \
      -p 127.0.0.1:3001:3001 \
      -v uptime-kuma:/app/data \
      louislam/uptime-kuma:1
  fi
  if ! docker ps -a --format '{{.Names}}' | grep -q '^ntfy$'; then
    run mkdir -p /var/lib/ntfy
    run docker run -d --name ntfy --restart=unless-stopped \
      -p 127.0.0.1:2586:80 \
      -v /var/lib/ntfy:/var/cache/ntfy \
      binwiederhier/ntfy serve --base-url http://localhost:2586 --cache-file /var/cache/ntfy/cache.db
  fi
fi

# Lynis weekly timer
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-lynis.service" /etc/systemd/system/openbox-lynis.service
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-lynis.timer" /etc/systemd/system/openbox-lynis.timer
run systemctl daemon-reload
run systemctl enable --now openbox-lynis.timer

echo "[07-monitoring] OK"
