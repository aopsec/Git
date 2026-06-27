#!/usr/bin/env bash
# CI gate: bash -n + shellcheck em todos os .sh do projeto
# [INTENCIONAL] set -uo pipefail sem -e para acumular falhas
set -uo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# ROOT normalizado via cd+pwd: um '/..' literal no caminho casa com
# o filtro '-not -path "*/.*"' do find e descarta TODOS os resultados.
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly ROOT

PASS=0
FAIL=0
WARN=0

printf 'WslDroid — gate de sintaxe\n\n'

SHELLCHECK_OK=0
command -v shellcheck >/dev/null 2>&1 && SHELLCHECK_OK=1
[[ "${SHELLCHECK_OK}" -eq 0 ]] && printf "${YELLOW}[AVISO]${NC} shellcheck nao instalado — pulando lint\n"

while IFS= read -r -d '' f; do
  if bash -n "${f}" 2>/dev/null; then
    printf "${GREEN}[PASS]${NC} bash -n: %s\n" "${f}"
    PASS=$((PASS+1))
  else
    printf "${RED}[FAIL]${NC} bash -n: %s\n" "${f}"
    FAIL=$((FAIL+1))
  fi
  if [[ "${SHELLCHECK_OK}" -eq 1 ]]; then
    if shellcheck -S warning "${f}" 2>/dev/null; then
      printf "${GREEN}[PASS]${NC} shellcheck: %s\n" "${f}"
      PASS=$((PASS+1))
    else
      printf "${RED}[FAIL]${NC} shellcheck: %s\n" "${f}"
      FAIL=$((FAIL+1))
    fi
  fi
done < <(find "${ROOT}" -name '*.sh' -not -path '*/.*' -print0 | sort -z)

printf '\n=== SINTAXE: %s PASS | %s FAIL | %s AVISO ===\n' "${PASS}" "${FAIL}" "${WARN}"
[[ "${FAIL}" -eq 0 ]] && exit 0 || exit 1
