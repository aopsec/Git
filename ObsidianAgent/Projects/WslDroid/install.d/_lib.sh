#!/usr/bin/env bash
# _lib.sh — helpers compartilhados para o WslDroid
# Fonte: source "${WSLDROID_ROOT}/install.d/_lib.sh"
# NAO executar diretamente.

# --- Constantes de cor ---------------------------------------------------------
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# --- Funcoes de log ------------------------------------------------------------
log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -Iseconds)" "${level}" "$*" \
    | tee -a "${LOG_FILE:-/tmp/wsldroid-install.log}"
}
die() { log ERRO "$*"; exit 1; }
ok()  { printf "${GREEN}[PASS]${NC} %s\n" "$1"; PASS="${PASS:-0}"; PASS=$((PASS+1)); }
nok() { printf "${RED}[FAIL]${NC} %s\n" "$1"; FAIL="${FAIL:-0}"; FAIL=$((FAIL+1)); }
warn(){ printf "${YELLOW}[AVISO]${NC} %s\n" "$1"; WARN="${WARN:-0}"; WARN=$((WARN+1)); }
info(){ printf "${CYAN}[INFO]${NC} %s\n" "$1"; }

# --- Execucao segura -----------------------------------------------------------
# Safe array exec (no shell re-parse)
run() {
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    log DRY "$(printf '%q ' "$@")"
  else
    log EXEC "$(printf '%q ' "$@")"
    "$@"
  fi
}

# Explicit shell (for pipes/redirects only — caller must ensure values are safe)
run_sh() {
  if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
    log DRY-SH "$1"
  else
    log SHELL "$1"
    bash -c "$1"
  fi
}

# --- Helpers de deteccao -------------------------------------------------------
# Returns 0 if running inside WSL2
detect_wsl2() {
  [[ -f /proc/version ]] \
    && grep -qi 'microsoft' /proc/version \
    && grep -qiE 'WSL2|microsoft-standard-WSL2' /proc/sys/kernel/osrelease 2>/dev/null
}

# Returns 0 if binder_linux kernel module is loaded
detect_binder() {
  lsmod 2>/dev/null | grep -q 'binder_linux'
}

# Returns 0 if a DRI GPU device is present (hardware acceleration)
detect_gpu() {
  [[ -d /dev/dri ]] && ls /dev/dri/card* 2>/dev/null | grep -q .
}

# Returns 0 if Wayland display is available
detect_wayland() {
  [[ -n "${WAYLAND_DISPLAY:-}" ]] && [[ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/wayland-0" ]]
}

# Get Windows host IP from WSL2 resolv.conf
get_win_ip() {
  awk '/^nameserver/{print $2; exit}' /etc/resolv.conf 2>/dev/null || echo "127.0.0.1"
}

# Assert a command exists or die
require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Comando ausente: $1 (instale e tente novamente)"
}

# Print a phase section header
phase_header() {
  printf '\n%s=== %s ===%s\n\n' "${BOLD}" "$1" "${NC}"
}
