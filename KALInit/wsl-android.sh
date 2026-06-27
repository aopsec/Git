#!/bin/bash
# wsl-android.sh — Provisiona WSL2 com Android (Waydroid) via WslDroid
# Parte da colecao KALInit de scripts de provisionamento
# Uso: sudo bash wsl-android.sh [--dry-run] [--phase FASE]
#
# Requer: WSL2 Ubuntu 22.04/24.04, acesso root
# Projeto: ObsidianAgent/Projects/WslDroid/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WSLDROID_DIR="${REPO_ROOT}/ObsidianAgent/Projects/WslDroid"

if [[ ! -f "${WSLDROID_DIR}/install.sh" ]]; then
  printf '[ERRO] WslDroid nao encontrado em: %s\n' "${WSLDROID_DIR}" >&2
  printf '[INFO] Clone o repositorio completo e execute novamente.\n' >&2
  exit 1
fi

printf '[INFO] Iniciando WslDroid a partir do KALInit...\n'
printf '[INFO] Projeto: %s\n' "${WSLDROID_DIR}"
exec bash "${WSLDROID_DIR}/install.sh" "$@"
