#!/usr/bin/env bash
# install.sh — OpenBox v0.1
# Idempotente, fased, com --dry-run e --phase.
# Executar: sudo ./install.sh [--dry-run] [--phase <nome>]

set -euo pipefail
IFS=$'\n\t'

readonly OPENBOX_VERSION="0.2.0"
OPENBOX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly OPENBOX_ROOT
readonly LOG_FILE="/var/log/openbox-install.log"
readonly WG_PLACEHOLDER="203.0.113.1"

DRY_RUN=0
PHASE=""

PHASES=(
  "00-base"
  "01-sysctl"
  "02-nftables"
  "03-wireguard"
  "04-dns"
  "05-tor"
  "06-media"
  "07-monitoring"
  "08-watchdogs"
  "09-validate"
)

# ===== Logging =====
log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date -Iseconds)" "${level}" "$*" | tee -a "${LOG_FILE}"
}

die() { log ERROR "$*"; exit 1; }

# Safe array exec — no shell re-parse. Use for normal command calls.
# [FIX-V7] install.sh retains log-based run()/run_sh() for structured install logging;
# phase scripts source install.d/_lib.sh for their printf-based variants.
run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log DRY "$(printf '%q ' "$@")"
  else
    log RUN "$(printf '%q ' "$@")"
    "$@"
  fi
}

# Explicit shell exec — only for redirects, pipes, env-var prefixes, glob, ||/&&.
# Caller must ensure interpolated values are safe (no untrusted input).
run_sh() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log DRY-SH "$1"
  else
    log RUN-SH "$1"
    bash -c "$1"
  fi
}

# ===== Pre-flight =====
preflight() {
  [[ "${EUID}" -eq 0 ]] || die "Execute como root (sudo)."
  command -v apt >/dev/null || die "apt nao encontrado — Armbian/Debian-based armhf apenas."
  local arch
  arch="$(dpkg --print-architecture 2>/dev/null || echo unknown)"
  [[ "${arch}" == "armhf" ]] || die "Arch nao suportada: ${arch}; esperado armhf (RK3229/Armbian rk322x-box)."
  [[ -d "${OPENBOX_ROOT}/install.d" ]] || die "install.d/ ausente em ${OPENBOX_ROOT}"

  # Refuse to install while WG_ENDPOINT is still TEST-NET-3 placeholder.
  local nft_file="${OPENBOX_ROOT}/etc/nftables/openbox-base.nft"
  if [[ -f "${nft_file}" ]] && grep -qE "^define[[:space:]]+WG_ENDPOINT[[:space:]]*=[[:space:]]*${WG_PLACEHOLDER}\b" "${nft_file}"; then
    die "WG_ENDPOINT ainda e o placeholder ${WG_PLACEHOLDER} em ${nft_file}. Edite com o IP real do servidor VPN antes de instalar."
  fi

  mkdir -p "$(dirname "${LOG_FILE}")"
  log INFO "OpenBox v${OPENBOX_VERSION} install starting (dry-run=${DRY_RUN})"
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

usage() {
  cat <<EOF
OpenBox installer v${OPENBOX_VERSION}

USO: sudo ./install.sh [OPTIONS]

OPTIONS:
  --dry-run         Mostra o que seria feito, sem executar
  --phase <nome>    Executa apenas uma fase (vide lista abaixo)
  --help, -h        Esta ajuda

FASES:
$(printf '  - %s\n' "${PHASES[@]}")
EOF
}

# ===== Execucao de fase =====
exec_phase() {
  local phase="$1"
  local script="${OPENBOX_ROOT}/install.d/${phase}.sh"

  [[ -f "${script}" ]] || die "Fase ausente: ${script}"

  log INFO "===== INICIANDO FASE: ${phase} ====="

  # shellcheck source=/dev/null
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log DRY "(would source ${script})"
  else
    OPENBOX_ROOT="${OPENBOX_ROOT}" DRY_RUN="${DRY_RUN}" bash "${script}"
  fi

  log INFO "===== FASE OK: ${phase} ====="
}

# ===== Main =====
main() {
  parse_args "$@"
  preflight

  if [[ -n "${PHASE}" ]]; then
    exec_phase "${PHASE}"
  else
    for p in "${PHASES[@]}"; do
      exec_phase "${p}"
    done
  fi

  log INFO "OpenBox v${OPENBOX_VERSION} install COMPLETO."
  log INFO "Proximo passo: sudo ${OPENBOX_ROOT}/tests/validate-stack.sh"
}

main "$@"
