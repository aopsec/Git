# Repository Guidelines
<!-- [INIT-OBSIDIANAGENT-01] Codex initialization guidance for the current ObsidianAgent tree. -->

## Project Structure & Module Organization

`ObsidianAgent` is a meta-vault, not a standalone app. Keep top-level work focused on vault orchestration:

- `README.md` explains the meta-vault purpose and default CLI flow.
- `.aops-vault.toml` defines the shared vault contract for this repo.
- `Vault/` holds manual notes such as `Vault Home.md` and generated indexes under `Vault/Generated/`.
- `Vault/References/CyberPDFs/` holds the generated cyber-only PDF reference vault. Use it only for security, pentest, bug bounty, Linux hardening, and related automation work.
- `Projects/` contains nested project repos. Current project folders include `ADV7ia/`, `IPS_IDS/`, `OpenBox0.1v/`, and `bbWebScan/`.
- `Projects/OpenBox0.1v/` is the canonical vault-tooling proof fixture and holds its own docs, tests, tools, and repo-local vault.
- `Projects/ADV7_0f_Sec_Tools/bbWebScan/` is a Python recon orchestrator. It has its own `pyproject.toml`, package modules, profile templates, and tests.
- `tests/` contains root-level collaboration and Obsidian stack checks.

## Build, Test, and Development Commands

Run all commands from the repo root unless noted otherwise.

- `export LC_ALL=C.UTF-8 LANG=C.UTF-8`
  Keeps generated vault indexes deterministic across machines.
- `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo .`
  Checks for stale generated notes without writing.
- `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .`
  Regenerates managed notes under `Vault/Generated/`.
- `bash tests/validate-collab-stack.sh`
  Runs the root Codex+Claude+Obsidian stack health check. Note that this script expects the canonical checkout path at `$HOME/ObsidianAgent`.
- `python3 tools/extract_cyber_pdf_reference.py --pdf-list tools/cyber_pdf_ref/b00ks_sources.txt --repo . --copy-pdfs --replace`
  Regenerates the cyber PDF reference vault from the curated B00Ks source set and copies the PDFs into the vault. # [REF-CYBERPDF-01]
- `bash Projects/OpenBox0.1v/tests/phase-b-vault-tool.sh`
  Proves repo-neutral init/check/sync behavior and deterministic output.
- `bash Projects/OpenBox0.1v/tests/validate-obsidian-vault.sh`
  Confirms OpenBox vault state stays synchronized.
- `bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh`
  Runs the broad shell, TOML, Python, and vault verification stack.
- `cd Projects/ADV7_0f_Sec_Tools/bbWebScan && ruff check . && mypy && pytest -q`
  Verifies the Python recon orchestrator after code changes in `Projects/ADV7_0f_Sec_Tools/bbWebScan/`.

## Coding Style & Naming Conventions

Keep manual notes short, title-cased, and link-friendly, for example `Vault Home.md`. Preserve the existing catalog naming in `.aops-vault.toml`, especially `project-parent` title mode for project manifests and overviews. Do not hand-edit files under `Vault/Generated/`; regenerate them with `--sync`. Treat nested project guidance as additive: read any project-local `AGENTS.md`, `CLAUDE.md`, or README before editing that project.

## Testing Guidelines

After changing `.aops-vault.toml`, `Vault/`, or nested project vault tooling, run `--check` first, then `--sync`, then re-run `--check`. If the change affects shared vault behavior, also run the three OpenBox scripts above. For `bbWebScan` code changes, run its Python lint/type/test stack from `Projects/ADV7_0f_Sec_Tools/bbWebScan/`. Treat deterministic output as required: the same repo state must produce the same generated files.

## Commit & Pull Request Guidelines

This checkout does not include `.git` metadata, so local history is unavailable here. In a full clone, use short imperative commit subjects scoped to the area changed, for example `vault: update project overview catalog` or `tests: extend init scaffold proof`. PRs should describe the vault contract change, list verification commands run, and mention any regenerated notes.
