#!/usr/bin/env bash
# [VAULT-B] tests/validate-obsidian-vault.sh — generated Obsidian vault must match repo
set -euo pipefail
shopt -s inherit_errexit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/tools/sync_obsidian_vault.py"

resolve_agent_home() {
  if [[ -n "${AOPS_OBSIDIAN_AGENT_HOME:-}" ]]; then
    printf '%s\n' "${AOPS_OBSIDIAN_AGENT_HOME}"
    return 0
  fi

  local base="${ROOT}"
  while true; do
    if [[ -d "${base}/plugins/aops-agent/obsidian-agent" ]]; then
      printf '%s\n' "${base}/plugins/aops-agent/obsidian-agent"
      return 0
    fi
    if [[ "${base}" == "/" ]]; then
      break
    fi
    base="$(dirname "${base}")"
  done

  printf '%s\n' "${HOME}/plugins/aops-agent/obsidian-agent"
}

AGENT_HOME="$(resolve_agent_home)"
readonly AGENT_HOME
CLI="${AGENT_HOME}/obsidian_agent_cli.py"

if [[ ! -f "${SCRIPT}" ]]; then
  echo "[SKIP] Obsidian sync script ausente"
  exit 0
fi

command -v python3 >/dev/null || {
  echo "[SKIP] python3 nao instalado"
  exit 0
}

while IFS= read -r -d '' py_file; do
  python3 -m py_compile "${py_file}"
done < <(find "${ROOT}/tools" -type f -name "*.py" -print0)
while IFS= read -r -d '' py_file; do
  python3 -m py_compile "${py_file}"
done < <(find "${AGENT_HOME}" -type f -name "*.py" -print0)

python3 "${SCRIPT}" --check
python3 "${CLI}" --repo "${ROOT}" --check
echo "[PASS] Obsidian vault sincronizado"
