#!/usr/bin/env bash
# [IPS-PH2] Preserve AIDE update evidence after pacman transactions; do not auto-promote.
set -euo pipefail
shopt -s inherit_errexit

readonly LOG_DIR="/var/log/aide"
readonly DB_DIR="/var/lib/aide"
readonly ACTIVE_DB_GZ="${DB_DIR}/aide.db.gz"
readonly CANDIDATE_DB_GZ="${DB_DIR}/aide.db.new.gz"

main() {
  local stamp=""
  local report=""
  local candidate=""
  local status=0

  command -v aide >/dev/null 2>&1 || exit 0
  [[ -f "${ACTIVE_DB_GZ}" ]] || exit 0

  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  report="${LOG_DIR}/pacman-aide-update-${stamp}.log"
  candidate="${DB_DIR}/aide.db.candidate-${stamp}.gz"

  install -d -m 0750 "${LOG_DIR}"
  install -d -m 0750 "${DB_DIR}"

  aide --update > "${report}" 2>&1 || status=$?

  if [[ -f "${CANDIDATE_DB_GZ}" ]]; then
    mv -f "${CANDIDATE_DB_GZ}" "${candidate}"
    printf 'AIDE candidate database preserved: %s\n' "${candidate}" >> "${report}"
  else
    printf 'AIDE did not produce %s\n' "${CANDIDATE_DB_GZ}" >> "${report}"
  fi

  printf 'AIDE update exit status: %s\n' "${status}" >> "${report}"
  printf 'Review %s before promoting any candidate database.\n' "${report}" >&2
  exit 0
}

main "$@"
