#!/usr/bin/env bash
# install.d/00-base.sh — OpenBox base hardening
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

install_unattended_upgrades_config() {
  local target="/etc/apt/apt.conf.d/50unattended-upgrades.local"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    # [FIX-AUDIT-DRYRUN] Do not mutate the target host while simulating.
    printf 'DRY: write %s\n' "${target}"
    return 0
  fi
  # Armbian publishes under origin=Debian — Raspbian origin removed in v0.2.0 retarget.
  cat > "${target}" <<'EOF'
Unattended-Upgrade::Origins-Pattern {
  "origin=Debian,codename=${distro_codename},label=Debian-Security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
  chmod 0644 "${target}"
}

# Atualizacao base
run apt update
run apt full-upgrade -y

# Pacotes essenciais
run env DEBIAN_FRONTEND=noninteractive apt install -y \
  unattended-upgrades apt-listchanges needrestart \
  ca-certificates curl gnupg jq lsb-release \
  auditd aide rkhunter chkrootkit lynis debsecan \
  nftables fail2ban \
  vim htop tmux tree

# SSH hardening
run install -m 0644 "${OPENBOX_ROOT}/etc/ssh/sshd_config.d/99-openbox.conf" /etc/ssh/sshd_config.d/99-openbox.conf
run sshd -t
run systemctl restart ssh

# Unattended upgrades (security only)
install_unattended_upgrades_config
run systemctl enable --now unattended-upgrades

# AIDE baseline (pode demorar varios minutos)
if [[ ! -f /var/lib/aide/aide.db ]]; then
  run aideinit -y -f
  run mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db
fi

# Auditd
run systemctl enable --now auditd

echo "[00-base] OK"
