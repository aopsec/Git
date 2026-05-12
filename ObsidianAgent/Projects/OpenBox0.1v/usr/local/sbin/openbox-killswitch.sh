#!/usr/bin/env bash
# /usr/local/sbin/openbox-killswitch.sh
# OpenBox v0.1 — kill switch helper (re-aplica nftables atomic ruleset)
# Uso: openbox-killswitch.sh {up|down|status}
set -euo pipefail
shopt -s inherit_errexit

readonly RULESET="/etc/nftables/openbox-base.nft"
readonly FILTER_TABLE_FAMILY="inet"
readonly FILTER_TABLE_NAME="openbox"
readonly QOS_TABLE_FAMILY="ip"
readonly QOS_TABLE_NAME="qos"

has_table() {
  local family="$1"
  local name="$2"
  /usr/sbin/nft list table "${family}" "${name}" >/dev/null 2>&1
}

delete_managed_tables() {
  # [FIX-AUDIT-NFT] Replace only OpenBox-owned tables and preserve Docker/fail2ban.
  if has_table "${FILTER_TABLE_FAMILY}" "${FILTER_TABLE_NAME}"; then
    /usr/sbin/nft delete table "${FILTER_TABLE_FAMILY}" "${FILTER_TABLE_NAME}"
  fi
  if has_table "${QOS_TABLE_FAMILY}" "${QOS_TABLE_NAME}"; then
    /usr/sbin/nft delete table "${QOS_TABLE_FAMILY}" "${QOS_TABLE_NAME}"
  fi
}

validate_ruleset() {
  # [FIX-AUDIT-NFT] Validate against a scratch ruleset so current tables do not
  # cause duplicate-object failures during checks.
  printf 'flush ruleset\ninclude "%s"\n' "${RULESET}" | /usr/sbin/nft -c -f -
}

case "${1:-status}" in
  up)
    [[ -f "${RULESET}" ]] || { echo "Ruleset ausente: ${RULESET}" >&2; exit 1; }
    validate_ruleset
    delete_managed_tables
    /usr/sbin/nft -f "${RULESET}"
    logger -t openbox-killswitch "applied"
    echo "Kill switch UP (OpenBox tables reapplied)"
    ;;
  down)
    if has_table "${FILTER_TABLE_FAMILY}" "${FILTER_TABLE_NAME}" || has_table "${QOS_TABLE_FAMILY}" "${QOS_TABLE_NAME}"; then
      delete_managed_tables
      logger -t openbox-killswitch "OpenBox tables removed (other nftables owners preserved)"
      echo "Kill switch DOWN — OpenBox tables removed (dangerous, debug only)"
    else
      echo "Kill switch ja down — OpenBox tables absent"
    fi
    ;;
  status)
    if has_table "${FILTER_TABLE_FAMILY}" "${FILTER_TABLE_NAME}"; then
      echo "OK: inet openbox table present"
    else
      echo "AUSENTE: inet openbox table"
    fi
    if has_table "${QOS_TABLE_FAMILY}" "${QOS_TABLE_NAME}"; then
      echo "OK: ip qos table present"
    else
      echo "AUSENTE: ip qos table"
    fi
    ;;
  *)
    echo "Uso: $0 {up|down|status}" >&2
    exit 1
    ;;
esac
