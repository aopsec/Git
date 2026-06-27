#!/usr/bin/env bash
# install.sh — WslDroid v0.1
# Orquestrador faseado para instalar Waydroid (Android 13 LXC) em WSL2 Ubuntu
# com GUI via WSLg, Play Store e ADB. Idempotente, com --dry-run e --phase.
# Executar: sudo bash install.sh [--dry-run] [--phase <fase>]

set -euo pipefail
shopt -s inherit_errexit

readonly WSLDROID_VERSION="0.1.0"
# Declare e atribui separadamente para nao mascarar o exit code do cd/dirname (SC2155).
WSLDROID_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly WSLDROID_ROOT
readonly LOG_FILE="/tmp/wsldroid-install.log"
readonly PHASES=("00-base" "01-gui" "02-kernel" "03-waydroid" "04-adb" "05-gapps" "06-validate")

DRY_RUN=0
PHASE=""

# ===== Logging =====
log() {
  printf '[%s] [%s] %s\n' "$(date -Iseconds)" "${1}" "${*:2}" | tee -a "${LOG_FILE}"
}

die() {
  log ERRO "$*"
  exit 1
}

# ===== Uso =====
usage() {
  cat >&2 <<EOF
WslDroid installer v${WSLDROID_VERSION}

USO: sudo bash install.sh [OPCOES]

OPCOES:
  --dry-run         Mostra o que seria feito, sem executar
  --phase <fase>    Executa apenas uma fase (vide lista abaixo)
  --help, -h        Esta ajuda

FASES:
$(printf '  - %s\n' "${PHASES[@]}")

EXEMPLO:
  sudo bash install.sh --phase 03-waydroid
EOF
}

# ===== Pre-flight =====
preflight() {
  [[ "${EUID}" -eq 0 ]] || die "Execute como root (sudo bash install.sh)"

  grep -qi 'microsoft' /proc/version 2>/dev/null \
    || die "Requer WSL2 (distribucao Linux no Windows)"
  grep -qi 'WSL2\|WSL_2\|microsoft-standard-WSL2' /proc/sys/kernel/osrelease 2>/dev/null \
    || die "Requer WSL2 (WSL1 detectado — converta com: wsl --set-version <distro> 2)"

  command -v apt-get >/dev/null 2>&1 \
    || die "apt-get nao encontrado — apenas Ubuntu/Debian suportados"

  [[ -d "${WSLDROID_ROOT}/install.d" ]] \
    || die "install.d/ ausente — repositorio incompleto"
}

# ===== Argumentos =====
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=1; shift ;;
      --phase)   PHASE="$2"; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      *) die "Argumento desconhecido: $1 (use --help)" ;;
    esac
  done
}

# ===== Execucao de fase =====
exec_phase() {
  local script="${WSLDROID_ROOT}/install.d/${1}.sh"

  [[ -f "${script}" ]] || die "Script de fase ausente: ${script}"

  log INFO "===== INICIANDO FASE: ${1} ====="
  WSLDROID_ROOT="${WSLDROID_ROOT}" DRY_RUN="${DRY_RUN}" bash "${script}"
  log INFO "===== FASE OK: ${1} ====="
}

# ===== Main =====
main() {
  parse_args "$@"

  log INFO "WslDroid v${WSLDROID_VERSION} iniciando (DRY_RUN=${DRY_RUN})"
  preflight

  if [[ -n "${PHASE}" ]]; then
    exec_phase "${PHASE}"
  else
    for p in "${PHASES[@]}"; do
      exec_phase "$p"
    done
  fi

  log INFO "WslDroid v${WSLDROID_VERSION} instalacao COMPLETA. Log: ${LOG_FILE}"
}

main "$@"
