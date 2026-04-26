#!/usr/bin/env bash
# [VAULT-C] Phase B/Phase C proof for repo-neutral vault tooling.
set -euo pipefail
shopt -s inherit_errexit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
WRAPPER="${ROOT}/tools/sync_obsidian_vault.py"
FIXTURE_SEED="${ROOT}/tests/fixtures/generic-vault-seed"
FIXTURE_EXPECTED="${ROOT}/tests/fixtures/generic-vault-expected"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT INT

snapshot_tree() {
  local target="$1"
  if [[ ! -d "${target}" ]]; then
    return 0
  fi
  find "${target}" -type f -print0 | sort -z | xargs -0 sha256sum 2>/dev/null
}

cp -R "${FIXTURE_SEED}" "${TMP_DIR}/fixture"
before_check="$(snapshot_tree "${TMP_DIR}/fixture")"
first_check_output="$(python3 "${CLI}" --repo "${TMP_DIR}/fixture" --check 2>&1 >/dev/null || true)"
second_check_output="$(python3 "${CLI}" --repo "${TMP_DIR}/fixture" --check 2>&1 >/dev/null || true)"
[[ "${first_check_output}" == "${second_check_output}" ]] || {
  echo "[FAIL] --check stale detection is not deterministic"
  exit 1
}
if python3 "${CLI}" --repo "${TMP_DIR}/fixture" --check >/dev/null 2>&1; then
  echo "[FAIL] --check should detect missing generated notes"
  exit 1
fi
after_check="$(snapshot_tree "${TMP_DIR}/fixture")"
[[ "${before_check}" == "${after_check}" ]] || {
  echo "[FAIL] --check mutated fixture repo"
  exit 1
}
if python3 "${CLI}" --repo "${TMP_DIR}/fixture" >/dev/null 2>&1; then
  echo "[FAIL] bare CLI should act as conservative check-first when stale"
  exit 1
fi
after_default_check="$(snapshot_tree "${TMP_DIR}/fixture")"
[[ "${before_check}" == "${after_default_check}" ]] || {
  echo "[FAIL] bare CLI mutated fixture repo"
  exit 1
}

python3 "${CLI}" --repo "${TMP_DIR}/fixture" --sync >/dev/null
diff -ru "${FIXTURE_EXPECTED}" "${TMP_DIR}/fixture/vault/Generated"
python3 "${CLI}" --repo "${TMP_DIR}/fixture" --check
python3 "${CLI}" --repo "${TMP_DIR}/fixture"
before_resync="$(snapshot_tree "${TMP_DIR}/fixture/vault/Generated")"
python3 "${CLI}" --repo "${TMP_DIR}/fixture" --sync >/dev/null
after_resync="$(snapshot_tree "${TMP_DIR}/fixture/vault/Generated")"
[[ "${before_resync}" == "${after_resync}" ]] || {
  echo "[FAIL] repeated --sync changed deterministic output"
  exit 1
}

printf '%s\n' '---' 'project: FixtureVault' 'type: source-note' '---' > "${TMP_DIR}/fixture/vault/Generated/Automation/Orphan.md"
if python3 "${CLI}" --repo "${TMP_DIR}/fixture" --sync >/dev/null 2>&1; then
  echo "[FAIL] --sync should refuse managed orphan files"
  exit 1
fi

mkdir -p "${TMP_DIR}/init-repo"
printf '# temp\n' > "${TMP_DIR}/init-repo/README.md"
python3 "${CLI}" --repo "${TMP_DIR}/init-repo" --init >/dev/null
[[ -f "${TMP_DIR}/init-repo/.aops-vault.toml" ]] || {
  echo "[FAIL] --init did not create .aops-vault.toml"
  exit 1
}
grep -q 'plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py' "${TMP_DIR}/init-repo/.aops-vault.toml" || {
  echo "[FAIL] --init did not set shared Obsidian agent default"
  exit 1
}
[[ -f "${TMP_DIR}/init-repo/vault/Vault Home.md" ]] || {
  echo "[FAIL] --init did not scaffold Vault Home.md"
  exit 1
}
grep -q '^# Vault Home$' "${TMP_DIR}/init-repo/vault/Vault Home.md" || {
  echo "[FAIL] --init scaffolded an invalid Vault Home.md"
  exit 1
}
if python3 "${CLI}" --repo "${TMP_DIR}/init-repo" --init >/dev/null 2>&1; then
  echo "[FAIL] --init should not overwrite existing config"
  exit 1
fi
python3 "${CLI}" --repo "${TMP_DIR}/init-repo" --sync >/dev/null
python3 "${CLI}" --repo "${TMP_DIR}/init-repo" --check

mkdir -p "${TMP_DIR}/meta-vault/Vault" "${TMP_DIR}/meta-vault/Projects/Alpha" "${TMP_DIR}/meta-vault/Projects/Beta"
printf '# Meta Vault\n' > "${TMP_DIR}/meta-vault/README.md"
printf '# Vault Home\n' > "${TMP_DIR}/meta-vault/Vault/Vault Home.md"
printf '# Alpha\n' > "${TMP_DIR}/meta-vault/Projects/Alpha/README.md"
printf '# Beta\n' > "${TMP_DIR}/meta-vault/Projects/Beta/README.md"
printf 'version = 1\n\n[project]\nname = "Alpha"\ntag = "alpha"\n\n[vault]\nroot = "vault"\ngenerated = "vault/Generated"\n\n[render]\ngenerator_ref = "plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py"\nregenerate_command = "python3 cli.py --sync --repo ."\nstale_message = "stale"\nsummary_fallback = "relative"\n\n[repository_map]\ninclude = true\ncore_documents = ["README"]\nmanual_dashboards = ["Vault Home"]\n\n[related_notes]\ndefaults = ["README"]\n\n[related_notes.match]\nalpha = ["README"]\n\n[[catalog]]\nlabel = "Automation"\nfolder = "Automation"\nnote_prefix = "Automation"\ntag = "automation"\nsource_patterns = ["scripts/*.sh"]\ntitle_mode = "standard"\nindex_name = "Automation Index"\n' > "${TMP_DIR}/meta-vault/Projects/Alpha/.aops-vault.toml"
printf 'version = 1\n\n[project]\nname = "Beta"\ntag = "beta"\n\n[vault]\nroot = "vault"\ngenerated = "vault/Generated"\n\n[render]\ngenerator_ref = "plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py"\nregenerate_command = "python3 cli.py --sync --repo ."\nstale_message = "stale"\nsummary_fallback = "relative"\n\n[repository_map]\ninclude = true\ncore_documents = ["README"]\nmanual_dashboards = ["Vault Home"]\n\n[related_notes]\ndefaults = ["README"]\n\n[related_notes.match]\nbeta = ["README"]\n\n[[catalog]]\nlabel = "Automation"\nfolder = "Automation"\nnote_prefix = "Automation"\ntag = "automation"\nsource_patterns = ["scripts/*.sh"]\ntitle_mode = "standard"\nindex_name = "Automation Index"\n' > "${TMP_DIR}/meta-vault/Projects/Beta/.aops-vault.toml"
printf 'version = 1\n\n[project]\nname = "MetaVault"\ntag = "meta-vault"\n\n[vault]\nroot = "Vault"\ngenerated = "Vault/Generated"\n\n[render]\ngenerator_ref = "plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py"\nregenerate_command = "python3 cli.py --sync --repo ."\nstale_message = "stale"\nsummary_fallback = "relative"\n\n[repository_map]\ninclude = true\ncore_documents = ["README"]\nmanual_dashboards = ["Vault Home"]\n\n[related_notes]\ndefaults = ["README"]\n\n[related_notes.match]\nproject = ["README"]\n\n[[catalog]]\nlabel = "Project Manifests"\nfolder = "Project Manifests"\nnote_prefix = "Project Manifest"\ntag = "project-manifest"\nsource_patterns = ["Projects/*/.aops-vault.toml"]\ntitle_mode = "project-parent"\nindex_name = "Project Manifest Index"\n\n[[catalog]]\nlabel = "Project Overviews"\nfolder = "Project Overviews"\nnote_prefix = "Project Overview"\ntag = "project-overview"\nsource_patterns = ["Projects/*/README.md"]\ntitle_mode = "project-parent"\nindex_name = "Project Overview Index"\n' > "${TMP_DIR}/meta-vault/.aops-vault.toml"
python3 "${CLI}" --repo "${TMP_DIR}/meta-vault" --sync >/dev/null
[[ -f "${TMP_DIR}/meta-vault/Vault/Generated/Project Manifests/Project Manifest - Alpha.md" ]] || {
  echo "[FAIL] project-parent title mode did not create Alpha manifest note"
  exit 1
}
[[ -f "${TMP_DIR}/meta-vault/Vault/Generated/Project Manifests/Project Manifest - Beta.md" ]] || {
  echo "[FAIL] project-parent title mode did not create Beta manifest note"
  exit 1
}
[[ -f "${TMP_DIR}/meta-vault/Vault/Generated/Project Overviews/Project Overview - Alpha.md" ]] || {
  echo "[FAIL] project-parent title mode did not create Alpha overview note"
  exit 1
}
[[ -f "${TMP_DIR}/meta-vault/Vault/Generated/Project Overviews/Project Overview - Beta.md" ]] || {
  echo "[FAIL] project-parent title mode did not create Beta overview note"
  exit 1
}
python3 "${CLI}" --repo "${TMP_DIR}/meta-vault" --check

python3 "${WRAPPER}" --check
python3 "${CLI}" --repo "${ROOT}" --check
echo "[PASS] Phase B vault tool proof"
