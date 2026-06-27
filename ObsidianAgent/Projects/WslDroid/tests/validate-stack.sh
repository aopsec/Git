#!/usr/bin/env bash
# Testes de integracao ao vivo — requer WSL2 + Waydroid em execucao
# Requer: WSL2 com binder_linux, waydroid-container ativo, sessao waydroid ativa
# [INTENCIONAL] set -uo pipefail sem -e para acumular resultados
set -uo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

PASS=0
FAIL=0
WARN=0

ok()   { printf "${GREEN}[PASS]${NC} %s\n" "$1"; PASS=$((PASS+1)); }
nok()  { printf "${RED}[FAIL]${NC} %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; WARN=$((WARN+1)); }

printf 'WslDroid — testes de integracao ao vivo\n\n'

# 1. WSL2 detectado
grep -qi microsoft /proc/version 2>/dev/null \
  && ok "WSL2 detectado (/proc/version)" || nok "WSL2 NAO detectado"

# 2. modulo binder_linux carregado
lsmod 2>/dev/null | grep -q binder_linux \
  && ok "modulo binder_linux carregado" || nok "binder_linux AUSENTE"

# 3. waydroid instalado
command -v waydroid >/dev/null 2>&1 \
  && ok "waydroid instalado" || nok "waydroid NAO instalado"

# 4. waydroid-container ativo
systemctl is-active --quiet waydroid-container 2>/dev/null \
  && ok "waydroid-container ativo" || nok "waydroid-container INATIVO"

# 5. sessao waydroid em execucao (warn — pode so precisar iniciar)
waydroid status 2>/dev/null | grep -qi running \
  && ok "sessao waydroid em execucao" || warn "sessao waydroid parada (rode: waydroid session start)"

# 6. WAYLAND_DISPLAY definido (WSLg)
[[ -n "${WAYLAND_DISPLAY:-}" ]] \
  && ok "WAYLAND_DISPLAY=${WAYLAND_DISPLAY}" || warn "WAYLAND_DISPLAY nao definido (WSLg ausente?)"

# 7. adb instalado
command -v adb >/dev/null 2>&1 \
  && ok "adb instalado" || nok "adb NAO instalado"

# 8. adb enxerga o waydroid (warn — pode precisar de adb connect)
adb devices 2>/dev/null | grep -q 'localhost:5555' \
  && ok "adb conectado ao waydroid (localhost:5555)" || warn "adb sem localhost:5555 (rode: adb connect localhost:5555)"

# 9. sqlite3 disponivel (warn)
command -v sqlite3 >/dev/null 2>&1 \
  && ok "sqlite3 disponivel" || warn "sqlite3 ausente"

# 10. GPU/DRI exposta (warn — render acelerado opcional)
ls /dev/dri/card* 2>/dev/null | grep -q . \
  && ok "GPU/DRI exposta (/dev/dri)" || warn "/dev/dri ausente (render por software)"

printf '\n=== RESULTADO: %s PASS | %s FAIL | %s AVISO ===\n' "${PASS}" "${FAIL}" "${WARN}"
exit $(( FAIL > 0 ? 1 : 0 ))
