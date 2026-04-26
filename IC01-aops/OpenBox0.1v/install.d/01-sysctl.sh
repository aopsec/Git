#!/usr/bin/env bash
# install.d/01-sysctl.sh — kernel tuning
set -euo pipefail
shopt -s inherit_errexit

OPENBOX_ROOT="${OPENBOX_ROOT:-$(pwd)}"
DRY_RUN="${DRY_RUN:-0}"

# [FIX-V7] Shared helpers sourced from _lib.sh.
# shellcheck source=install.d/_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

run install -m 0644 "${OPENBOX_ROOT}/etc/sysctl.d/99-openbox.conf" /etc/sysctl.d/99-openbox.conf
run sysctl --system

# CAKE qdisc + IRQ affinity via systemd unit
run install -m 0755 "${OPENBOX_ROOT}/usr/local/sbin/openbox-tune.sh" /usr/local/sbin/openbox-tune.sh
run install -m 0644 "${OPENBOX_ROOT}/systemd/openbox-tuning.service" /etc/systemd/system/openbox-tuning.service
run systemctl daemon-reload
run systemctl enable --now openbox-tuning.service

# CPU governor performance — write directly (redirect to sysfs is not a "command")
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    printf 'DRY: write performance to %s\n' "${cpu}"
  else
    echo performance > "${cpu}"
  fi
done

echo "[01-sysctl] OK — BBR=$(sysctl -n net.ipv4.tcp_congestion_control)"
