#!/usr/bin/env bash
# install.d/06-media.sh — Jellyfin media server via Docker (armhf nativo)
# RK3229 retarget v0.2.0: substituiu Stremio. Jellyfin publica linux/arm/v7,
# Stremio nao. Bound a 127.0.0.1:8096 e fronted por Caddy (mesmo padrao anterior).
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"
# IPTV (Jellyfin Live TV via iptv-org) — opt-in. LAN-expor Jellyfin sem Caddy — opt-in.
OPENBOX_ENABLE_IPTV="${OPENBOX_ENABLE_IPTV:-0}"
OPENBOX_JELLYFIN_LAN="${OPENBOX_JELLYFIN_LAN:-0}"

# shellcheck source=install.d/_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

write_docker_repo_file() {
  local target="/etc/apt/sources.list.d/docker.list"
  local arch
  local codename
  arch="$(dpkg --print-architecture)"
  codename="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME}")"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf 'DRY: write %s\n' "${target}"
    return 0
  fi
  cat > "${target}" <<EOF
deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${codename} stable
EOF
  chmod 0644 "${target}"
}

start_jellyfin_container() {
  # Padrao: loopback (atras do Caddy /jellyfin/). Com OPENBOX_JELLYFIN_LAN=1 publica
  # na LAN (sem Caddy) para acesso direto a Live TV de TVs/celulares.
  local port_bind="127.0.0.1:8096:8096"
  [[ "${OPENBOX_JELLYFIN_LAN}" -eq 1 ]] && port_bind="8096:8096"
  if ! docker ps -a --format '{{.Names}}' | grep -q '^jellyfin$'; then
    run mkdir -p /var/lib/jellyfin/config /var/lib/jellyfin/cache
    run docker run -d \
      --name=jellyfin \
      --restart=unless-stopped \
      --user 1000:1000 \
      -v /var/lib/jellyfin/config:/config \
      -v /var/lib/jellyfin/cache:/cache \
      -p "${port_bind}" \
      jellyfin/jellyfin:latest
  fi
}

# Docker engine
if ! command -v docker >/dev/null; then
  run install -m 0755 -d /etc/apt/keyrings
  run_sh "curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
  run chmod a+r /etc/apt/keyrings/docker.gpg
  write_docker_repo_file
  run apt update
  run env DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  run systemctl enable --now docker
fi

if command -v docker >/dev/null; then
  start_jellyfin_container
elif [[ "${DRY_RUN}" -eq 1 ]]; then
  printf 'DRY: docker run -d --name=jellyfin ... jellyfin/jellyfin:latest\n'
else
  echo "[06-media] docker nao encontrado apos instalacao" >&2
  exit 1
fi

# ===== IPTV (Jellyfin Live TV via iptv-org — canais publicos legais/open-source) =====
run install -d -m 0755 /etc/openbox
run install -m 0644 "${OPENBOX_ROOT}/etc/openbox/iptv.conf" /etc/openbox/iptv.conf
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-iptv-setup.sh" /usr/local/sbin/openbox-iptv-setup.sh
if [[ "${OPENBOX_ENABLE_IPTV}" -eq 1 ]]; then
  run /usr/local/sbin/openbox-iptv-setup.sh
else
  echo "[06-media] IPTV pronto: rode 'sudo openbox-iptv-setup.sh' (ou reinstale com OPENBOX_ENABLE_IPTV=1) para configurar Live TV (iptv-org)."
fi

echo "[06-media] OK — Jellyfin em http://127.0.0.1:8096 (Caddy: https://openbox.lan/jellyfin/; LAN direto via OPENBOX_JELLYFIN_LAN=1 -> http://<box>:8096)"
