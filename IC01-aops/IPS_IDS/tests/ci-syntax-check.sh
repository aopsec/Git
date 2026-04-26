#!/usr/bin/env bash
# [IPS-PH1] CI syntax checks for the IPS/IDS installer tree.
set -euo pipefail
shopt -s inherit_errexit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ROOT
PASS=0
FAIL=0
TEMP_DIRS=()

cleanup() {
  local dir=""
  for dir in "${TEMP_DIRS[@]}"; do
    [[ -n "${dir}" ]] && rm -rf "${dir}"
  done
}
trap cleanup EXIT SIGINT

ok() {
  local message="$1"
  printf '[PASS] %s\n' "${message}"
  PASS=$((PASS + 1))
}

nok() {
  local message="$1"
  printf '[FAIL] %s\n' "${message}"
  FAIL=$((FAIL + 1))
}

echo "===== IPS/IDS CI syntax check ====="
echo "ROOT: ${ROOT}"

echo
echo "--- bash -n ---"
while IFS= read -r -d '' script; do
  if bash -n "${script}" 2>/dev/null; then
    ok "bash -n ${script#${ROOT}/}"
  else
    nok "bash -n ${script#${ROOT}/}"
    bash -n "${script}" || true
  fi
done < <(find "${ROOT}" -type f -name "*.sh" -print0)

echo
echo "--- python compile ---"
if command -v python3 >/dev/null; then
  while IFS= read -r -d '' py_file; do
    if python3 -m py_compile "${py_file}" 2>/dev/null; then
      ok "py_compile ${py_file#${ROOT}/}"
    else
      nok "py_compile ${py_file#${ROOT}/}"
      python3 -m py_compile "${py_file}" || true
    fi
  done < <(find "${ROOT}" -path "${ROOT}/.vendor" -prune -o -type f -name "*.py" -print0)

  if PYTHONPATH="${ROOT}" python3 - "${ROOT}" <<'PY'
from __future__ import annotations

import pathlib
import sys

from adv7sec_1_0.validate import validate_configs

errors = validate_configs(pathlib.Path(sys.argv[1]))
if errors:
    raise SystemExit("\n".join(errors))
PY
  then
    ok "python validate_configs"
  else
    nok "python validate_configs"
  fi

  if PYTHONPATH="${ROOT}" python3 -m unittest discover -s "${ROOT}/tests" -p "test_*.py"; then
    ok "python unittest"
  else
    nok "python unittest"
  fi
fi

echo
echo "--- python quality gate ---"
RUFF_BIN="${ADV7SEC_RUFF_BIN:-}"
MYPY_BIN="${ADV7SEC_MYPY_BIN:-}"
if [[ -z "${RUFF_BIN}" ]] && command -v ruff >/dev/null 2>&1; then
  RUFF_BIN="$(command -v ruff)"
elif [[ -z "${RUFF_BIN}" && -x "${HOME}/.venvs/adv7sec-review/bin/ruff" ]]; then
  RUFF_BIN="${HOME}/.venvs/adv7sec-review/bin/ruff"
fi
if [[ -z "${MYPY_BIN}" ]] && command -v mypy >/dev/null 2>&1; then
  MYPY_BIN="$(command -v mypy)"
elif [[ -z "${MYPY_BIN}" && -x "${HOME}/.venvs/adv7sec-review/bin/mypy" ]]; then
  MYPY_BIN="${HOME}/.venvs/adv7sec-review/bin/mypy"
fi
if [[ -n "${RUFF_BIN}" ]]; then
  if "${RUFF_BIN}" check "${ROOT}/ADV7Sec_1.0v.py" "${ROOT}/adv7sec_1_0"; then
    ok "ruff check adv7sec 1.0"
  else
    nok "ruff check adv7sec 1.0"
  fi
else
  echo "(ruff not installed; skipping)"
fi
if [[ -n "${MYPY_BIN}" ]]; then
  if PYTHONPATH="${ROOT}" "${MYPY_BIN}" --strict "${ROOT}/ADV7Sec_1.0v.py" "${ROOT}/adv7sec_1_0"; then
    ok "mypy --strict adv7sec 1.0"
  else
    nok "mypy --strict adv7sec 1.0"
  fi
else
  echo "(mypy not installed; skipping)"
fi

echo
echo "--- ADV7Sec runtime ---"
if [[ -x "${ROOT}/ADV7Sec_1.0v.py" ]]; then
  ok "ADV7Sec_1.0v.py executable"
else
  nok "ADV7Sec_1.0v.py executable"
fi
if python3 "${ROOT}/ADV7Sec_1.0v.py" audit >/dev/null; then
  ok "ADV7Sec_1.0v.py audit"
else
  nok "ADV7Sec_1.0v.py audit"
fi
if python3 "${ROOT}/ADV7Sec_1.0v.py" plan --format json >/dev/null; then
  ok "ADV7Sec_1.0v.py plan json"
else
  nok "ADV7Sec_1.0v.py plan json"
fi
adv7sec10_extract="$(mktemp -d)"
TEMP_DIRS+=("${adv7sec10_extract}")
if python3 "${ROOT}/ADV7Sec_1.0v.py" resources --export-dir "${adv7sec10_extract}" >/dev/null \
  && [[ -s "${adv7sec10_extract}/etc/aide/aide.conf" ]] \
  && [[ -s "${adv7sec10_extract}/usr/local/sbin/ipsids-suricata-run.sh" ]]; then
  ok "ADV7Sec_1.0v.py resources export"
else
  nok "ADV7Sec_1.0v.py resources export"
fi

echo
echo "--- shellcheck ---"
if command -v shellcheck >/dev/null; then
  while IFS= read -r -d '' script; do
    if shellcheck -S warning "${script}" 2>/dev/null; then
      ok "shellcheck ${script#${ROOT}/}"
    else
      nok "shellcheck ${script#${ROOT}/}"
      shellcheck -S warning "${script}" || true
    fi
  done < <(find "${ROOT}" -type f -name "*.sh" -print0)
else
  echo "(shellcheck not installed; skipping)"
fi

echo
echo "--- yaml ---"
if command -v python3 >/dev/null; then
  while IFS= read -r -d '' yaml_file; do
    if python3 - "${yaml_file}" <<'PY'
from __future__ import annotations

import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "\t" in text:
    raise SystemExit("tabs are not allowed in YAML")
if not text.strip():
    raise SystemExit("empty YAML file")
PY
    then
      ok "yaml basic ${yaml_file#${ROOT}/}"
    else
      nok "yaml basic ${yaml_file#${ROOT}/}"
    fi
  done < <(find "${ROOT}" -type f \( -name "*.yaml" -o -name "*.yml" \) -print0)
fi

echo
echo "--- systemd headers ---"
while IFS= read -r -d '' unit; do
  if grep -q '^\[Unit\]' "${unit}" && grep -Eq '^\[(Service|Timer)\]' "${unit}"; then
    ok "systemd headers ${unit#${ROOT}/}"
  else
    nok "systemd headers ${unit#${ROOT}/}"
  fi
done < <(find "${ROOT}/adv7sec_1_0/resource_files/etc/systemd/system" -type f \( -name "*.service" -o -name "*.timer" \) -print0)

echo
echo "--- required active resources ---"
required_configs=(
  "adv7sec_1_0/resource_files/etc/audit/rules.d/50-persistence.rules"
  "adv7sec_1_0/resource_files/etc/falco/falco.local.yaml"
  "adv7sec_1_0/resource_files/etc/falco/rules.d/workstation.yaml"
  "adv7sec_1_0/resource_files/etc/suricata/eve-minimal.yaml"
  "adv7sec_1_0/resource_files/etc/suricata/disable.conf"
  "adv7sec_1_0/resource_files/etc/suricata/ipsids-overrides.yaml"
  "adv7sec_1_0/resource_files/etc/systemd/system/suricata.service.d/ipsids.conf"
  "adv7sec_1_0/resource_files/etc/unbound/unbound.conf.d/dnstap.conf"
  "adv7sec_1_0/resource_files/etc/aide/aide.conf"
  "adv7sec_1_0/resource_files/etc/pacman.d/hooks/90-aide-update.hook"
  "adv7sec_1_0/resource_files/usr/local/sbin/ipsids-suricata-run.sh"
  "adv7sec_1_0/resource_files/usr/local/sbin/ipsids-aide-pacman-hook.sh"
)
for rel in "${required_configs[@]}"; do
  if [[ -s "${ROOT}/${rel}" ]]; then
    ok "required ${rel}"
  else
    nok "required ${rel}"
  fi
done

echo
echo "===== ${PASS} pass · ${FAIL} fail ====="
exit $((FAIL > 0 ? 1 : 0))
