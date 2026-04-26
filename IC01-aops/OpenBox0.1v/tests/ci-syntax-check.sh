#!/usr/bin/env bash
# [VAULT-B] tests/ci-syntax-check.sh — OpenBox v0.1 sintaxe CI
# Roda: bash -n em todos os scripts, shellcheck se disponivel, nft -c em rulesets
set -euo pipefail
shopt -s inherit_errexit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ROOT
PASS=0
FAIL=0

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

ok()  { printf "[PASS] %s\n" "$1"; PASS=$((PASS+1)); }
nok() { printf "[FAIL] %s\n" "$1"; FAIL=$((FAIL+1)); }

echo "===== OpenBox v0.1 — CI Syntax Check ====="
echo "ROOT: ${ROOT}"

# 1. bash -n em todos os .sh
echo
echo "--- bash -n ---"
while IFS= read -r -d '' script; do
  if bash -n "${script}" 2>/dev/null; then
    ok "bash -n ${script#${ROOT}/}"
  else
    nok "bash -n ${script#${ROOT}/}"
    bash -n "${script}"
  fi
done < <(find "${ROOT}" -type f \( -name "*.sh" -o -name "install.sh" \) -print0)

# 2. shellcheck (opcional)
echo
echo "--- shellcheck (opcional) ---"
if command -v shellcheck >/dev/null; then
  while IFS= read -r -d '' script; do
    if shellcheck -S warning "${script}" 2>/dev/null; then
      ok "shellcheck ${script#${ROOT}/}"
    else
      nok "shellcheck ${script#${ROOT}/}"
    fi
  done < <(find "${ROOT}" -type f \( -name "*.sh" -o -name "install.sh" \) -print0)
else
  echo "(shellcheck nao instalado — pulando)"
fi

# 3. nft -c em rulesets — pula quando nao root (flush ruleset exige privilegio)
echo
echo "--- nft -c ---"
if command -v nft >/dev/null; then
  if [[ "${EUID}" -ne 0 ]]; then
    echo "(nft -c requer root para validar 'flush ruleset' — pulando, rode com sudo)"
  else
    for nft_file in "${ROOT}"/etc/nftables/*.nft; do
      [[ -f "${nft_file}" ]] || continue
      if nft -c -f "${nft_file}" 2>/dev/null; then
        ok "nft -c ${nft_file#${ROOT}/}"
      else
        nok "nft -c ${nft_file#${ROOT}/}"
        nft -c -f "${nft_file}"
      fi
    done
  fi
else
  echo "(nft nao instalado — pulando)"
fi

# 4. systemd unit sintaxe (basico)
echo
echo "--- systemd unit basic ---"
for unit in "${ROOT}"/systemd/*.service "${ROOT}"/systemd/*.timer; do
  [[ -f "${unit}" ]] || continue
  if grep -q "^\[Unit\]\|^\[Service\]\|^\[Timer\]" "${unit}"; then
    ok "systemd unit headers ${unit##*/}"
  else
    nok "systemd unit malformed ${unit##*/}"
  fi
done

# 5. TOML basico (dnscrypt)
echo
echo "--- toml basic ---"
TOML="${ROOT}/etc/dnscrypt-proxy/dnscrypt-proxy.toml"
if [[ -f "${TOML}" ]] && command -v python3 >/dev/null; then
  python3 -c "
try:
  import tomllib as t
except ImportError:
  import tomli as t
with open('${TOML}','rb') as f:
  t.load(f)
print('TOML OK')
" 2>/dev/null && ok "toml parse ${TOML#${ROOT}/}" || nok "toml parse ${TOML#${ROOT}/}"
fi

# 6. Python syntax (vault tooling)
echo
echo "--- python syntax ---"
if command -v python3 >/dev/null; then
  while IFS= read -r -d '' py_file; do
    if python3 -m py_compile "${py_file}" 2>/dev/null; then
      ok "py_compile ${py_file#${ROOT}/}"
    else
      nok "py_compile ${py_file#${ROOT}/}"
      python3 -m py_compile "${py_file}"
    fi
  done < <(find "${ROOT}/tools" -type f -name "*.py" -print0)
  while IFS= read -r -d '' py_file; do
    if python3 -m py_compile "${py_file}" 2>/dev/null; then
      ok "py_compile ${py_file#${AGENT_HOME}/}"
    else
      nok "py_compile ${py_file#${AGENT_HOME}/}"
      python3 -m py_compile "${py_file}"
    fi
  done < <(find "${AGENT_HOME}" -type f -name "*.py" -print0)
else
  echo "(python3 nao instalado — pulando)"
fi

# 7. Obsidian vault generated files
echo
echo "--- obsidian vault ---"
VAULT_TEST="${ROOT}/tests/validate-obsidian-vault.sh"
if [[ -x "${VAULT_TEST}" ]]; then
  if bash "${VAULT_TEST}" 2>/dev/null; then
    ok "obsidian vault sync"
  else
    nok "obsidian vault sync"
    bash "${VAULT_TEST}"
  fi
else
  echo "(validate-obsidian-vault.sh ausente — pulando)"
fi

echo
echo "===== ${PASS} pass · ${FAIL} fail ====="
exit $(( FAIL > 0 ? 1 : 0 ))
