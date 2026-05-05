# Repository Guidelines

## Project Structure & Module Organization

`ObsidianAgent` is a meta-vault, not a standalone app. Keep top-level work focused on vault orchestration:

- `README.md` explains the meta-vault purpose and default CLI flow.
- `.aops-vault.toml` defines the shared vault contract for this repo.
- `Vault/` holds manual notes such as `Vault Home.md` and generated indexes under `Vault/Generated/`.
- `Projects/` contains nested project repos. `Projects/OpenBox0.1v/` is the current proof fixture and holds its own docs, tests, tools, and repo-local vault.

## Build, Test, and Development Commands

Run all commands from the repo root unless noted otherwise.

- `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo .`
  Checks for stale generated notes without writing.
- `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .`
  Regenerates managed notes under `Vault/Generated/`.
- `bash Projects/OpenBox0.1v/tests/phase-b-vault-tool.sh`
  Proves repo-neutral init/check/sync behavior and deterministic output.
- `bash Projects/OpenBox0.1v/tests/validate-obsidian-vault.sh`
  Confirms OpenBox vault state stays synchronized.
- `bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh`
  Runs the broad shell, TOML, Python, and vault verification stack.

## Coding Style & Naming Conventions

Keep manual notes short, title-cased, and link-friendly, for example `Vault Home.md`. Preserve the existing catalog naming in `.aops-vault.toml`, especially `project-parent` title mode for project manifests and overviews. Do not hand-edit files under `Vault/Generated/`; regenerate them with `--sync`.

## Testing Guidelines

After changing `.aops-vault.toml`, `Vault/`, or nested project vault tooling, run `--check` first, then `--sync`, then re-run `--check`. If the change affects shared vault behavior, also run the three OpenBox scripts above. Treat deterministic output as required: the same repo state must produce the same generated files.

## Commit & Pull Request Guidelines

This checkout does not include `.git` metadata, so local history is unavailable here. In a full clone, use short imperative commit subjects scoped to the area changed, for example `vault: update project overview catalog` or `tests: extend init scaffold proof`. PRs should describe the vault contract change, list verification commands run, and mention any regenerated notes.
