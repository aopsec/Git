#!/usr/bin/env bash
# install.d/_lib.sh — shared helpers for OpenBox phase scripts.
# Source this file; do NOT execute directly. No set -euo pipefail here — callers own that.
# [FIX-V7] Extracted from install.d/06-media.sh and 07-monitoring.sh to eliminate duplication.

# Safe array exec — no shell re-parse. Use for normal command calls.
run() {
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then printf 'DRY:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi
}

# Explicit shell exec — only for redirects, pipes, env-var prefixes, glob, ||/&&.
# Caller must ensure interpolated values are safe (no untrusted input).
run_sh() {
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then printf 'DRY-SH: %s\n' "$1"; else bash -c "$1"; fi
}

# Runtime hardware/distro probes (RK3229 retarget v0.2.0). No multi-platform branching:
# values are derived per-host because hardcoding eth0 / 4GB / arm64 broke on rk322x.
detect_eth_iface() {
  local iface
  iface="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}')"
  if [[ -z "${iface}" ]]; then
    iface="$(ip -br link show 2>/dev/null | awk '$1 != "lo" && $2 == "UP" {print $1; exit}')"
  fi
  printf '%s' "${iface:-eth0}"
}

ram_kb() { awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo; }

has_cpufreq() { [[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; }

arch_is_armhf() { [[ "$(dpkg --print-architecture 2>/dev/null)" == "armhf" ]]; }
