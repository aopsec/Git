#!/usr/bin/env bash
# /usr/local/sbin/openbox-dnsleak-check.sh
# OpenBox v0.1 — DNS leak check (referencia: macvk/dnsleaktest)
set -euo pipefail
shopt -s inherit_errexit

readonly NTFY="/usr/local/sbin/openbox-ntfy-send.sh"
readonly DEFAULT_QUERY_HOST="${OPENBOX_DNS_TEST_HOST:-example.com}"
readonly ALLOWED_NAMESERVERS="${OPENBOX_ALLOWED_DNS_SERVERS:-127.0.0.1,127.0.0.53,::1}"
declare -a OBSERVED_NAMESERVERS=()

notify_failure() {
  local message="$1"
  logger -t openbox-dnsleak "${message}"
  [[ -x "${NTFY}" ]] && "${NTFY}" "openbox-alerts" "${message}" || true
}

collect_nameservers() {
  local nameserver=""
  if command -v resolvectl >/dev/null; then
    while IFS= read -r nameserver; do
      [[ -n "${nameserver}" ]] || continue
      OBSERVED_NAMESERVERS+=("${nameserver}")
    done < <(resolvectl dns 2>/dev/null | awk '{for (i = 2; i <= NF; i++) print $i}')
  fi
  if (( ${#OBSERVED_NAMESERVERS[@]} == 0 )) && [[ -r /etc/resolv.conf ]]; then
    while IFS= read -r nameserver; do
      [[ -n "${nameserver}" ]] || continue
      OBSERVED_NAMESERVERS+=("${nameserver}")
    done < <(awk '/^nameserver[[:space:]]+/ {print $2}' /etc/resolv.conf)
  fi
}

is_allowed_nameserver() {
  local candidate="$1"
  local allowed=""
  local -a allowed_nameservers=()
  IFS=',' read -r -a allowed_nameservers <<< "${ALLOWED_NAMESERVERS}"
  for allowed in "${allowed_nameservers[@]}"; do
    if [[ "${candidate}" == "${allowed}" ]]; then
      return 0
    fi
  done
  return 1
}

collect_nameservers

if (( ${#OBSERVED_NAMESERVERS[@]} == 0 )); then
  notify_failure "DNS leak check failed: no configured nameservers found"
  exit 1
fi

for nameserver in "${OBSERVED_NAMESERVERS[@]}"; do
  # [FIX-AUDIT-DNS] Validate the trust boundary: the host must forward through
  # local resolvers, not infer leaks from the upstream IP returned by a test site.
  if ! is_allowed_nameserver "${nameserver}"; then
    notify_failure "DNS leak detected: unexpected configured nameserver ${nameserver}"
    exit 1
  fi
done

if ! dig +short +time=2 +tries=1 @127.0.0.1 -p 53 "${DEFAULT_QUERY_HOST}" >/dev/null 2>&1; then
  notify_failure "DNS local-path check failed: 127.0.0.1:53 did not resolve ${DEFAULT_QUERY_HOST}"
  exit 1
fi

if ! ss -tlnu 2>/dev/null | grep -q '127.0.0.1:5053'; then
  notify_failure "DNS local-path check failed: dnscrypt-proxy is not bound to 127.0.0.1:5053"
  exit 1
fi

logger -t openbox-dnsleak "OK — local DNS path is constrained to ${OBSERVED_NAMESERVERS[*]}"
exit 0
