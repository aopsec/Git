#!/usr/bin/env bash
# [FIX-ADV7IA-TEST-02] Verify that the curated ADV7ia import kept required files and excluded ephemeral state.
set -euo pipefail
shopt -s inherit_errexit

PASS=0
FAIL=0

cleanup() {
  :
}

ok() {
  printf '  [ok]   %s\n' "$1"
  PASS=$((PASS + 1))
}

nok() {
  printf '  [FAIL] %s\n' "$1" >&2
  FAIL=$((FAIL + 1))
}

assert_file() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    ok "file: ${path}"
  else
    nok "missing file: ${path}"
  fi
}

assert_dir() {
  local path="$1"
  if [[ -d "${path}" ]]; then
    ok "dir: ${path}"
  else
    nok "missing dir: ${path}"
  fi
}

assert_exec() {
  local path="$1"
  if [[ -x "${path}" ]]; then
    ok "exec: ${path}"
  else
    nok "not executable: ${path}"
  fi
}

assert_absent() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    ok "absent: ${path}"
  else
    nok "unexpected path present: ${path}"
  fi
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ROOT

trap cleanup EXIT INT

assert_file "${ROOT}/README.md"
assert_file "${ROOT}/.aops-vault.toml"
assert_file "${ROOT}/main.py"
assert_file "${ROOT}/.aider.conf.yml"
assert_file "${ROOT}/pyproject.toml"

assert_dir "${ROOT}/docs"
assert_dir "${ROOT}/adv7ia_control"
assert_dir "${ROOT}/deploy"
assert_dir "${ROOT}/tools"
assert_dir "${ROOT}/tests"
assert_dir "${ROOT}/evidence"
assert_dir "${ROOT}/state"
assert_dir "${ROOT}/vault"
assert_dir "${ROOT}/vault/Operations"

assert_file "${ROOT}/docs/AIDER_TEST_SOURCE_README.md"
assert_file "${ROOT}/docs/CONTROL_MESH_RUNBOOK.md"
assert_file "${ROOT}/docs/LOCAL_AI_STACK_RUNBOOK.md"
assert_file "${ROOT}/docs/LOCAL_AI_STACK_ARCH_LMSTUDIO_GUIDE.md"
assert_file "${ROOT}/evidence/ai-stack-status.stable.2026-04-24-153505.log"
assert_file "${ROOT}/evidence/audit-local-ai-stack.final.2026-04-24-041947.log"
assert_file "${ROOT}/evidence/audit-local-ai-stack.known-good.2026-04-24-045236.log"
assert_file "${ROOT}/deploy/bin/restart-openhands-local"
assert_file "${ROOT}/deploy/bin/check-openhands-local.sh"
assert_file "${ROOT}/deploy/bin/install-caddy-lan-proxy"
assert_file "${ROOT}/deploy/bin/install-vmtst-reverse-tunnel"
assert_file "${ROOT}/deploy/openhands/compose.yaml"
assert_file "${ROOT}/deploy/systemd/openhands-docker-proxy.service"
assert_file "${ROOT}/deploy/systemd-user/openhands-docker-proxy.service"
assert_file "${ROOT}/deploy/systemd-user/adv7ia-caddy-lan-proxy.service"
assert_file "${ROOT}/deploy/systemd-guest/adv7ia-vmtst-reverse-tunnel.service"
assert_file "${ROOT}/deploy/caddy/Caddyfile"
assert_file "${ROOT}/state/policy/control-mesh.json"
assert_file "${ROOT}/state/policy/openhands-reconcile.json"
assert_file "${ROOT}/state/tasks/task-bootstrap-local-control-mesh.json"
assert_file "${ROOT}/state/sessions/session-bootstrap-openhands.json"
assert_file "${ROOT}/state/checkpoints/checkpoint-bootstrap-intake.json"
assert_file "${ROOT}/vault/Dashboards/ADV7ia Control Mesh.md"
assert_file "${ROOT}/vault/Operations/Task Queue.md"
assert_file "${ROOT}/vault/Operations/Session Ledger.md"
assert_file "${ROOT}/vault/Operations/Security Policy.md"
assert_file "${ROOT}/vault/Operations/Incident Review.md"

assert_exec "${ROOT}/tools/ai-stack-status"
assert_exec "${ROOT}/tools/audit-local-ai-stack"
assert_exec "${ROOT}/tools/audit-control-mesh"
assert_exec "${ROOT}/tools/control-mesh"
assert_exec "${ROOT}/tools/control_mesh.py"
assert_exec "${ROOT}/tools/index-aider-test-rag"
assert_exec "${ROOT}/tools/query-aider-test-rag"
assert_exec "${ROOT}/tools/bootstrap-adv7ia-rag"
assert_exec "${ROOT}/tools/mcp-filesystem-aider-test"
assert_exec "${ROOT}/tools/mcp-git-aider-test"
assert_exec "${ROOT}/tools/mcp-rag-aider-test"
assert_exec "${ROOT}/tests/validate-obsidian-vault.sh"
assert_exec "${ROOT}/tests/validate-project-layout.sh"
assert_exec "${ROOT}/tests/validate-control-mesh.sh"
assert_exec "${ROOT}/deploy/bin/install-caddy-lan-proxy"
assert_exec "${ROOT}/deploy/bin/install-vmtst-reverse-tunnel"

assert_absent "${ROOT}/.git"
assert_absent "${ROOT}/.aider.chat.history.md"
assert_absent "${ROOT}/.aider.input.history"
assert_absent "${ROOT}/.aider.tags.cache.v4"
assert_absent "${ROOT}/evidence/manual-2026-04-24-153508"

printf 'pass=%d fail=%d\n' "${PASS}" "${FAIL}"
(( FAIL == 0 ))
