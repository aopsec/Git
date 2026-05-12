#!/usr/bin/env bash
# [IPS-PH1] Suricata service runner that applies IPS_IDS config includes and interfaces.
set -euo pipefail
shopt -s inherit_errexit

readonly CONFIG="${IPSIDS_SURICATA_CONFIG:-/etc/suricata/suricata.yaml}"
readonly INCLUDE="${IPSIDS_SURICATA_INCLUDE:-/etc/suricata/eve-minimal.yaml}"
readonly OVERRIDES="${IPSIDS_SURICATA_OVERRIDES:-/etc/suricata/ipsids-overrides.yaml}"
readonly LOG_DIR="${IPSIDS_SURICATA_LOG_DIR:-/var/log/suricata}"
readonly IFACES="${SURICATA_INTERFACES:-}"

build_cmd() {
  local mode="$1"
  local iface=""
  local -i iface_count=0
  local -a cmd=(/usr/bin/suricata -c "${CONFIG}" --include "${INCLUDE}")

  # [IPSIDS-PH1] Workstation overrides (JA3/JA4, exception-policy). ADR 0012.
  if [[ -f "${OVERRIDES}" ]]; then
    cmd+=(--include "${OVERRIDES}")
  fi

  cmd+=(-l "${LOG_DIR}")

  if [[ "${mode}" == "--test" ]]; then
    cmd+=(-T)
  fi

  for iface in ${IFACES}; do
    [[ -n "${iface}" ]] || continue
    cmd+=(--af-packet="${iface}")
    iface_count+=1
  done

  if (( iface_count == 0 )); then
    printf 'SURICATA_INTERFACES is empty; set it in /etc/default/ipsids-suricata\n' >&2
    return 1
  fi

  printf '%s\0' "${cmd[@]}"
}

main() {
  local mode="${1:-run}"
  local -a cmd=()
  local item=""

  while IFS= read -r -d '' item; do
    cmd+=("${item}")
  done < <(build_cmd "${mode}")

  exec "${cmd[@]}"
}

main "$@"
