#!/usr/bin/env bash
# /usr/local/sbin/openbox-tune.sh
# OpenBox v0.1 — CAKE qdisc + IRQ affinity. Chamado pela openbox-tuning.service
set -euo pipefail
shopt -s inherit_errexit

# RK3229 retarget (v0.2.0): autodetect default-route iface; default to 95% of 100Mbps NIC.
_default_iface() {
  local i
  i="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}')"
  [[ -z "${i}" ]] && i="$(ip -br link show 2>/dev/null | awk '$1 != "lo" && $2 == "UP" {print $1; exit}')"
  printf '%s' "${i:-eth0}"
}
readonly IFACE="${OPENBOX_IFACE:-$(_default_iface)}"
readonly BANDWIDTH="${OPENBOX_BANDWIDTH:-95mbit}"

# CAKE com flow isolation `flows` (CRITICO para WireGuard — outros modos quebram hash interno)
/sbin/tc qdisc replace dev "${IFACE}" root cake \
  bandwidth "${BANDWIDTH}" \
  diffserv4 \
  flows \
  nat

# CPU governor performance (cpufreq may be absent on some RK3229 BSP kernels)
if [[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
  for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "${gov}" 2>/dev/null || true
  done
fi

# IRQ affinity (TX -> CPU1 = bitmask 2; RX -> CPU2 = bitmask 4)
# [SEC-001] awk -v avoids regex injection from OPENBOX_IFACE env var.
TX_IRQ="$(awk -F: -v iface="${IFACE}" '$0 ~ iface".*[Tt]x" {gsub(/ /,"",$1); print $1; exit}' /proc/interrupts || true)"
RX_IRQ="$(awk -F: -v iface="${IFACE}" '$0 ~ iface".*[Rr]x" {gsub(/ /,"",$1); print $1; exit}' /proc/interrupts || true)"

[[ -n "${TX_IRQ}" && -w "/proc/irq/${TX_IRQ}/smp_affinity" ]] && echo 2 > "/proc/irq/${TX_IRQ}/smp_affinity"
[[ -n "${RX_IRQ}" && -w "/proc/irq/${RX_IRQ}/smp_affinity" ]] && echo 4 > "/proc/irq/${RX_IRQ}/smp_affinity"

logger -t openbox-tune "Applied CAKE (${BANDWIDTH}, flows) on ${IFACE}; IRQ TX=${TX_IRQ:-none} RX=${RX_IRQ:-none}"
exit 0
