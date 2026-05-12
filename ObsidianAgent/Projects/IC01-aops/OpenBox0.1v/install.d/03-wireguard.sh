#!/usr/bin/env bash
# install.d/03-wireguard.sh — WireGuard com fwmark routing
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

install_wg_ordering_override() {
  local target="/etc/systemd/system/wg-quick@wg0.service.d/openbox-ordering.conf"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    # [FIX-AUDIT-DRYRUN] Skip override creation while simulating.
    printf 'DRY: write %s\n' "${target}"
    return 0
  fi
  cat > "${target}" <<'EOF'
[Unit]
After=nftables.service network-online.target
Wants=network-online.target
Requires=nftables.service
EOF
  chmod 0644 "${target}"
}

run env DEBIAN_FRONTEND=noninteractive apt install -y wireguard wireguard-tools

# Copiar exemplo se nao existir wg0.conf
if [[ ! -f /etc/wireguard/wg0.conf ]]; then
  run install -m 0600 "${OPENBOX_ROOT}/etc/wireguard/wg0.conf.example" /etc/wireguard/wg0.conf
  echo "[03-wireguard] AVISO: edite /etc/wireguard/wg0.conf com chaves reais antes de subir o tunel."
  echo "                       Tambem ajuste WG_ENDPOINT em /etc/nftables/openbox-base.nft"
fi

run chmod 600 /etc/wireguard/wg0.conf

# Systemd ordering: wg-quick After=nftables
run mkdir -p /etc/systemd/system/wg-quick@wg0.service.d
install_wg_ordering_override
run systemctl daemon-reload

# NAO habilita o service por default — usuario tem que editar wg0.conf primeiro
echo "[03-wireguard] Para ativar: edite wg0.conf e execute: sudo systemctl enable --now wg-quick@wg0"
