#!/usr/bin/env bash
# install.d/06-validate.sh — verificacao final do stack WslDroid (Waydroid + WSLg + ADB)
# Roda 8 smoke checks acumulando PASS/FAIL/AVISO. Exit code 0 = nenhuma falha.
# [INTENCIONAL] set -uo pipefail sem -e para acumular PASS/FAIL sem abortar na primeira falha.
# Sem 'shopt -s inherit_errexit' por consistencia (so faz sentido junto de -e).
set -uo pipefail

# shellcheck source=_lib.sh
source "${WSLDROID_ROOT:?WSLDROID_ROOT nao definido}/install.d/_lib.sh"

# Helpers de tally locais (independentes do _lib.sh para manter o arquivo auto-contido).
PASS=0
FAIL=0
WARN=0

ok()   { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
nok()  { printf '[FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }
warn() { printf '[AVISO] %s\n' "$1"; WARN=$((WARN + 1)); }

phase_header "06-validate: Verificacao do stack WslDroid"

# 1. Kernel WSL2
if grep -qi 'microsoft' /proc/version 2>/dev/null \
  && grep -qiE 'WSL2|microsoft-standard-WSL2' /proc/sys/kernel/osrelease 2>/dev/null; then
  ok "WSL2 kernel: $(uname -r)"
else
  nok "WSL2 nao detectado — este instalador requer WSL2 (nao WSL1 nem bare-metal)"
fi

# 2. Modulo binder_linux carregado
if lsmod 2>/dev/null | grep -q binder_linux; then
  ok "binder_linux: carregado"
else
  nok "binder_linux ausente — execute a fase 02-kernel e reinicie o WSL2"
fi

# 3. Waydroid instalado
if command -v waydroid >/dev/null 2>&1; then
  ok "waydroid: instalado"
else
  nok "waydroid ausente — execute a fase 03-waydroid"
fi

# 4. Servico waydroid-container ativo
if systemctl is-active --quiet waydroid-container 2>/dev/null; then
  ok "waydroid-container: ativo"
else
  warn "waydroid-container: inativo (inicie com: sudo systemctl start waydroid-container)"
fi

# 5. Display para a GUI (WSLg) — Wayland preferido, X11 aceitavel, ausencia tolerada sob sudo
if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  ok "Display Wayland: ${WAYLAND_DISPLAY} (WSLg)"
elif [[ -n "${DISPLAY:-}" ]]; then
  warn "X11 detectado (${DISPLAY}) — Waydroid prefere Wayland (WSLg)"
else
  warn "nenhum display (normal ao executar como root via sudo)"
fi

# 6. adb disponivel
if command -v adb >/dev/null 2>&1; then
  ok "adb: $(adb version 2>/dev/null | head -1)"
else
  nok "adb ausente — execute a fase 04-adb"
fi

# 7. sqlite3 disponivel (necessario para a fase 05-gapps)
if command -v sqlite3 >/dev/null 2>&1; then
  ok "sqlite3: disponivel"
else
  warn "sqlite3 ausente — necessario para a fase 05-gapps"
fi

# 8. GPU/DRI exposta ao WSL2 (aceleracao opcional; ausencia e limitacao conhecida)
# Glob-array em vez de 'ls | grep' (evita SC2010 e e robusto sob set -u).
_dri_cards=(/dev/dri/card*)
if [[ -d /dev/dri && -e "${_dri_cards[0]}" ]]; then
  ok "GPU/DRI: ${_dri_cards[*]}"
else
  warn "GPU/DRI ausente — limitacao conhecida no WSL2+Waydroid (render por software)"
fi

# --- Resultado final ------------------------------------------------------
printf '\n=== RESULTADO: %s PASS | %s FAIL | %s AVISO ===\n' "${PASS}" "${FAIL}" "${WARN}"
if [[ "${FAIL}" -gt 0 ]]; then
  log ERRO "06-validate: ${FAIL} verificacao(oes) falharam."
  exit 1
else
  log INFO "06-validate OK (${PASS} PASS, ${WARN} avisos)"
fi
