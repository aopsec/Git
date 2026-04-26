#!/usr/bin/env bash
# install.d/02-nftables.sh — firewall + kill switch
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

append_openbox_include() {
  local target="/etc/nftables.conf"
  if grep -q 'include "/etc/nftables/openbox-base.nft"' "${target}" 2>/dev/null; then
    return 0
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    # [FIX-AUDIT-DRYRUN] Skip config mutation while simulating.
    printf 'DRY: append OpenBox include to %s\n' "${target}"
    return 0
  fi
  cat >> "${target}" <<'EOF'

# OpenBox v0.1 — base ruleset com WireGuard kill switch
include "/etc/nftables/openbox-base.nft"
EOF
}

run mkdir -p /etc/nftables
run install -m 0644 "${OPENBOX_ROOT}/etc/nftables/openbox-base.nft" /etc/nftables/openbox-base.nft
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-killswitch.sh" /usr/local/sbin/openbox-killswitch.sh

# Incluir no /etc/nftables.conf
append_openbox_include

run systemctl enable --now nftables
run /usr/local/sbin/openbox-killswitch.sh up

# Snapshot do ruleset aplicado
if [[ "${DRY_RUN}" -eq 1 ]]; then
  printf 'DRY: nft list ruleset > /var/log/openbox-nftables-applied.log\n'
else
  nft list ruleset > /var/log/openbox-nftables-applied.log
fi

echo "[02-nftables] OK — ruleset aplicado"
