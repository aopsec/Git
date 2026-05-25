#!/usr/bin/env bash
# [FIX-ADV7IA-TEST-01] Confirm that the ADV7ia vault wrappers and generated notes stay in sync.
set -euo pipefail
shopt -s inherit_errexit

cleanup() {
  :
}

is_valid_agent_home() {
  local candidate="$1"
  [[ -d "${candidate}" ]] &&
    [[ -d "${candidate}/obsidian_agent" ]] &&
    [[ -f "${candidate}/obsidian_agent/cli.py" ]] &&
    [[ -f "${candidate}/obsidian_agent_cli.py" ]]
}

resolve_agent_home() {
  if [[ -n "${AOPS_OBSIDIAN_AGENT_HOME:-}" ]]; then
    if is_valid_agent_home "${AOPS_OBSIDIAN_AGENT_HOME}"; then
      printf '%s\n' "${AOPS_OBSIDIAN_AGENT_HOME}"
      return 0
    fi
  fi

  local base=""
  base="${ROOT}"
  while true; do
    if is_valid_agent_home "${base}/plugins/aops-agent/obsidian-agent"; then
      printf '%s\n' "${base}/plugins/aops-agent/obsidian-agent"
      return 0
    fi
    if [[ "${base}" == "/" ]]; then
      break
    fi
    base="$(dirname "${base}")"
  done

  if is_valid_agent_home "${HOME}/plugins/aops-agent/obsidian-agent"; then
    printf '%s\n' "${HOME}/plugins/aops-agent/obsidian-agent"
    return 0
  fi

  return 1
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ROOT
SCRIPT="${ROOT}/tools/sync_obsidian_vault.py"
readonly SCRIPT

trap cleanup EXIT INT

if [[ ! -f "${SCRIPT}" ]]; then
  echo "[SKIP] sync wrapper absent"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[SKIP] python3 not installed"
  exit 0
fi

if ! AGENT_HOME="$(resolve_agent_home)"; then
  echo "[SKIP] no valid shared Obsidian agent install found; set AOPS_OBSIDIAN_AGENT_HOME to a valid shared agent root"
  exit 0
fi
readonly AGENT_HOME
CLI="${AGENT_HOME}/obsidian_agent_cli.py"
readonly CLI

python3 -m py_compile "${ROOT}/main.py"
while IFS= read -r -d '' py_file; do
  python3 -m py_compile "${py_file}"
done < <(find "${ROOT}/tools" -type f -name "*.py" -print0)

if [[ -d "${ROOT}/adv7ia_control" ]]; then
  while IFS= read -r -d '' py_file; do
    python3 -m py_compile "${py_file}"
  done < <(find "${ROOT}/adv7ia_control" -type f -name "*.py" -print0)
fi

if [[ -d "${AGENT_HOME}" ]]; then
  while IFS= read -r -d '' py_file; do
    python3 -m py_compile "${py_file}"
  done < <(find "${AGENT_HOME}" -type f -name "*.py" -print0)
fi

python3 "${SCRIPT}" --check
python3 "${CLI}" --repo "${ROOT}" --check
echo "[PASS] ADV7ia vault synchronized"
