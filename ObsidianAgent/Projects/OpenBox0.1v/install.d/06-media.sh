#!/usr/bin/env bash
# install.d/06-media.sh — Jellyfin media server via Docker (armhf nativo)
# RK3229 retarget v0.2.0: substituiu Stremio (sem build ARM). NOTA: jellyfin:latest
# dropou 32-bit ARM — usamos um tag fixo com arm/v7 (OPENBOX_JELLYFIN_IMAGE). Docker via
# docker.io (distro), pois o repo docker-ce nao cobre o codename do Armbian base Ubuntu.
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"
# IPTV (Jellyfin Live TV via iptv-org) — opt-in. LAN-expor Jellyfin sem Caddy — opt-in.
OPENBOX_ENABLE_IPTV="${OPENBOX_ENABLE_IPTV:-0}"
OPENBOX_JELLYFIN_LAN="${OPENBOX_JELLYFIN_LAN:-0}"
# jellyfin/jellyfin:latest dropou linux/arm/v7; 10.10.7 e o tag mais novo que ainda
# publica arm/v7 (necessario no RK3229/Cortex-A7/armhf). Em arm64 pode usar :latest.
OPENBOX_JELLYFIN_IMAGE="${OPENBOX_JELLYFIN_IMAGE:-jellyfin/jellyfin:10.10.7}"

# shellcheck source=install.d/_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

start_jellyfin_container() {
  # Padrao: loopback (atras do Caddy /jellyfin/). Com OPENBOX_JELLYFIN_LAN=1 publica
  # na LAN (sem Caddy) para acesso direto a Live TV de TVs/celulares.
  local port_bind="127.0.0.1:8096:8096"
  [[ "${OPENBOX_JELLYFIN_LAN}" -eq 1 ]] && port_bind="8096:8096"
  if ! docker ps -a --format '{{.Names}}' | grep -q '^jellyfin$'; then
    run mkdir -p /var/lib/jellyfin/config /var/lib/jellyfin/cache
    # Container roda como uid:gid 1000:1000 — os volumes precisam pertencer a esse uid,
    # senao o Jellyfin nao cria /config/log e sai (UnauthorizedAccessException).
    run chown -R 1000:1000 /var/lib/jellyfin/config /var/lib/jellyfin/cache
    run docker run -d \
      --name=jellyfin \
      --restart=unless-stopped \
      --user 1000:1000 \
      -v /var/lib/jellyfin/config:/config \
      -v /var/lib/jellyfin/cache:/cache \
      -p "${port_bind}" \
      "${OPENBOX_JELLYFIN_IMAGE}"
  fi
}

# Docker engine — docker.io (pacote da distro). Robusto em Debian E em Armbian de base
# Ubuntu: o repo docker-ce nao cobre todos os codenames (ex.: base 'resolute' nao existe
# em download.docker.com), enquanto docker.io vem dos repos do proprio SO.
if ! command -v docker >/dev/null; then
  run env DEBIAN_FRONTEND=noninteractive apt install -y docker.io
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
