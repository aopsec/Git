---
project: ADV7ia
type: dashboard
tags:
  - adv7ia
  - vault
  - dashboard
---

# ADV7ia Vault Home

This repository is the curated Obsidian view of the validated local AI stack. The
project files remain canonical; the notes under `vault/` connect runtime checks,
evidence, and documentation around them.

## Start Here

- [[README]]
- [[ADV7ia Control Mesh]]
- [[CONTROL_MESH_RUNBOOK]]
- [[LOCAL_AI_STACK_RUNBOOK]]
- [[ADV7ia Operations Dashboard]]
- [[Repository Map]]

## Generated Catalogs

- [[Project Doc Index]]
- [[Tool Index]]
- [[Validation Index]]
- [[Evidence Index]]

## Working Rules

- Regenerate generated notes after structural changes with `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .`.
- Keep primary technical truth in the project files; use the vault to connect context and evidence.
- Treat `evidence/` as stable proof snapshots, not as live runtime state.
