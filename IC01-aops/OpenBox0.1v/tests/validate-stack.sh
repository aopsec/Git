#!/usr/bin/env bash
# tests/validate-stack.sh — OpenBox v0.1 final validation
# Roda 10 checks objetivos. Exit code 0 = tudo OK.
set -uo pipefail  # [INTENTIONAL] -e omitted: script accumulates PASS/FAIL counts without aborting on first failure.
shopt -s inherit_errexit

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

PASS=0
FAIL=0
WARN=0

ok()    { printf "${GREEN}[PASS]${NC} %s\n" "$1"; PASS=$((PASS+1)); }
nok()   { printf "${RED}[FAIL]${NC} %s\n" "$1"; FAIL=$((FAIL+1)); }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; WARN=$((WARN+1)); }

echo "===== OpenBox v0.1 — Stack Validation ====="

# 1. BBR ativo
[[ "$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)" == "bbr" ]] \
  && ok "TCP BBR ativo" || nok "TCP BBR NAO ativo"

# 2. CAKE qdisc presente (interface autodetectada — eth0 nem sempre existe em rk322x)
PRIMARY_IFACE="$(ip route show default 2>/dev/null | awk '/^default/ {print $5; exit}')"
PRIMARY_IFACE="${PRIMARY_IFACE:-eth0}"
tc -s qdisc show dev "${PRIMARY_IFACE}" 2>/dev/null | grep -q "qdisc cake" \
  && ok "CAKE qdisc ativo em ${PRIMARY_IFACE}" || warn "CAKE qdisc nao ativo (${PRIMARY_IFACE})"

# 3. nftables ruleset OpenBox carregado
nft list table inet openbox &>/dev/null \
  && ok "nftables openbox table presente" || nok "nftables openbox AUSENTE"

# 4. WireGuard handshake recente (< 180s)
if command -v wg >/dev/null && wg show wg0 &>/dev/null; then
  LAST="$(wg show wg0 latest-handshakes | awk '{print $2; exit}')"
  AGE=$(( $(date +%s) - LAST ))
  if (( LAST > 0 && AGE < 180 )); then
    ok "WireGuard handshake recente (${AGE}s)"
  else
    warn "WireGuard sem handshake ou stale (${AGE}s)"
  fi
else
  warn "WireGuard wg0 nao configurado"
fi

# 5. dnscrypt-proxy listening 5053
ss -tlnu 2>/dev/null | grep -q "127.0.0.1:5053" \
  && ok "dnscrypt-proxy bound 127.0.0.1:5053" || nok "dnscrypt-proxy NAO bound"

# 6. Pi-hole FTL listening 53
ss -tlnu 2>/dev/null | grep -q "127.0.0.1:53\|0.0.0.0:53" \
  && ok "Pi-hole FTL bound :53" || warn "Pi-hole FTL nao detectado"

# 7. Tor SOCKS5 listening 9050
ss -tln 2>/dev/null | grep -q "127.0.0.1:9050" \
  && ok "Tor SOCKS5 bound 127.0.0.1:9050" || warn "Tor :9050 nao detectado"

# 8. Tor circuit funcional
RESPONSE="$(curl --max-time 30 --socks5-hostname 127.0.0.1:9050 -s https://check.torproject.org/api/ip 2>/dev/null || echo '')"
if echo "${RESPONSE}" | grep -q '"IsTor":true'; then
  ok "Tor circuit OK (IsTor:true)"
else
  warn "Tor circuit nao verificavel: ${RESPONSE:0:80}"
fi

# 9. CPU governor performance (cpufreq pode estar ausente em alguns kernels rk322x)
if [[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]]; then
  GOV="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)"
  [[ "${GOV}" == "performance" ]] \
    && ok "CPU governor=performance" || warn "CPU governor=${GOV} (esperado performance)"
else
  warn "cpufreq driver ausente (RK3229 BSP kernel?) — pulando check de governor"
fi

# 10. IPv6 desabilitado
[[ "$(sysctl -n net.ipv6.conf.all.disable_ipv6 2>/dev/null)" == "1" ]] \
  && ok "IPv6 desabilitado" || warn "IPv6 habilitado (esperado disable)"

# Lynis quick (opcional)
if command -v lynis >/dev/null; then
  IDX="$(lynis audit system --quick --no-colors 2>/dev/null | grep "Hardening index" | awk '{print $4}' || echo 0)"
  # RK3229 retarget v0.2.0: alvo relaxado de 75 -> 70 (1GB RAM, baseline mais magro)
  if [[ -n "${IDX}" && "${IDX}" -ge 70 ]]; then
    ok "Lynis hardening index = ${IDX} (>= 70)"
  else
    warn "Lynis hardening index = ${IDX:-?} (alvo >= 70)"
  fi
fi

echo
echo "===== RESULTADO: ${PASS} pass · ${WARN} warn · ${FAIL} fail ====="
exit $(( FAIL > 0 ? 1 : 0 ))
