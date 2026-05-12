# ObsidianAgent

Meta-vault for AOPS project repositories and shared Obsidian workflows.

## Layout

- `Projects/` contains repo-local projects that may each own their own `.aops-vault.toml`.
- `Vault/` contains the shared manual notes and generated indexes for this meta-vault.

## Default CLI

```bash
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --check --repo .
python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .
```
