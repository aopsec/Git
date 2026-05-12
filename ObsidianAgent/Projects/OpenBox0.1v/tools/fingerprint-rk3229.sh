#!/usr/bin/env bash
# tools/fingerprint-rk3229.sh — Phase 0 hardware fingerprint runner
# RK3229 retarget v0.2.0. Run on the physical R29_5G_LP3 booted into Armbian rk322x-box.
# Captures the 12 facts the rest of the install/tuning pipeline depends on.
#
# Usage (on the board):
#   sudo bash tools/fingerprint-rk3229.sh > docs/hw/r29_5g_lp3.txt 2>&1
#
# Then commit the resulting docs/hw/r29_5g_lp3.txt and verify the gate criteria
# at the end of the file.

set -uo pipefail   # -e omitted: each probe is best-effort; missing tool != hard fail

DEFAULT_IFACE="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}' || true)"

section() { printf '\n===== %s =====\n' "$*"; }
probe()   { printf '\n--- %s ---\n' "$*"; }

printf '# OpenBox v0.2.0 — Phase 0 hardware fingerprint\n'
printf '# Generated: %s\n' "$(date -Iseconds 2>/dev/null || date)"
printf '# Host: %s\n'      "$(hostname 2>/dev/null || echo unknown)"

section "0.1 — SoC + board DTS"
probe "/proc/device-tree/model"
cat /proc/device-tree/model 2>/dev/null | tr -d '\0'; echo
probe "/proc/device-tree/compatible"
cat /proc/device-tree/compatible 2>/dev/null | tr '\0' '\n'

section "0.2 — Kernel + arch"
uname -a
printf 'arch (uname -m)        : '; uname -m
printf 'arch (dpkg)            : '; dpkg --print-architecture 2>/dev/null || echo "dpkg not available"

section "0.3 — Distro release"
cat /etc/os-release 2>/dev/null || echo "no /etc/os-release"

section "0.4 — RAM"
free -h 2>/dev/null
head -5 /proc/meminfo

section "0.5 — Storage (eMMC + SD)"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL,VENDOR 2>/dev/null
probe "eMMC CID (vendor / serial)"
for cid in /sys/block/mmcblk*/device/cid; do
  [[ -e "${cid}" ]] && printf '%s : ' "${cid}" && cat "${cid}"
done

section "0.6 — Ethernet"
printf 'Default route iface    : %s\n' "${DEFAULT_IFACE:-NONE}"
ip -br link 2>/dev/null
if [[ -n "${DEFAULT_IFACE}" ]] && command -v ethtool >/dev/null 2>&1; then
  probe "ethtool ${DEFAULT_IFACE}"
  ethtool "${DEFAULT_IFACE}" 2>/dev/null
  probe "ethtool -i ${DEFAULT_IFACE} (driver)"
  ethtool -i "${DEFAULT_IFACE}" 2>/dev/null
fi

section "0.7 — WireGuard module"
lsmod 2>/dev/null | grep -E '^wireguard|^nft|^cake|^sch_cake' || echo "(none of wireguard/nft/cake loaded)"
modinfo wireguard 2>/dev/null | head -8 || echo "modinfo wireguard: not found (may need linux-modules-extra-$(uname -r))"

section "0.8 — cpufreq governors"
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_available_governors; do
  [[ -e "${g}" ]] && { printf '%s : ' "${g}"; cat "${g}"; }
done
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  [[ -e "${g}" ]] && { printf '%s : ' "${g}"; cat "${g}"; }
done
[[ ! -e /sys/devices/system/cpu/cpu0/cpufreq ]] && echo "(no cpufreq subsystem present — RK3229 BSP kernel?)"

section "0.9 — Thermal"
for t in /sys/class/thermal/thermal_zone*; do
  [[ -e "${t}/type" ]] && printf '%s : type=%s temp=%s\n' \
    "${t##*/}" "$(cat "${t}/type")" "$(cat "${t}/temp" 2>/dev/null)"
done

section "0.10 — Watchdog"
ls -l /dev/watchdog* 2>/dev/null || echo "(no /dev/watchdog* devices)"
for w in /sys/class/watchdog/watchdog*/identity; do
  [[ -e "${w}" ]] && { printf '%s : ' "${w}"; cat "${w}"; }
done

section "0.11 — Wi-Fi / BT modules"
probe "lsusb"
lsusb 2>/dev/null || echo "(lsusb not available)"
probe "iw dev"
iw dev 2>/dev/null || echo "(iw not available — install: apt install iw)"
probe "rfkill"
rfkill list 2>/dev/null || echo "(rfkill not available)"

section "0.12 — Crypto throughput baseline"
if command -v openssl >/dev/null 2>&1; then
  probe "openssl speed -evp chacha20 -seconds 5 (single-thread)"
  openssl speed -evp chacha20 -seconds 5 2>/dev/null | tail -8
  probe "openssl speed -evp aes-128-gcm -seconds 5"
  openssl speed -evp aes-128-gcm -seconds 5 2>/dev/null | tail -8
else
  echo "openssl not available — install: apt install openssl"
fi

section "GATE — manual verification"
cat <<'GATE'
Pass criteria for Phase 0 (must be confirmed by reading sections above):
  0.1  /proc/device-tree/model contains "rockchip,rk3229" or "rockchip,rk3228"
  0.2  uname -m == armv7l   AND   dpkg --print-architecture == armhf
  0.7  modinfo wireguard returns kernel module info (not "ERROR")
  0.10 At least one /dev/watchdog* exists

If any of the four fail, do NOT proceed to Phase 1 — the chosen Armbian image is
wrong for this PCB. Pick a different rk322x-box variant and re-run this script.
GATE
