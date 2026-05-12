---
project: OpenBox
type: dashboard
tags:
  - openbox
  - vault
  - dashboard
---

# OpenBox Vault Home

This repository is the Obsidian vault. The source tree stays canonical; the notes under `vault/` organize the engineering context around it.

## Start Here
- [[README]]
- [[OBSIDIAN_VAULT]]
- [[OpenBox Project Dashboard]]
- [[Repository Map]]

## Dashboards
- [[OpenBox Architecture Dashboard]]
- [[OpenBox Operations Dashboard]]
- [[OpenBox Security Dashboard]]
- [[OpenBox Research Dashboard]]
- [[OpenBox Delivery Backlog]]
- [[OpenBox Roadmap]]

## Generated Catalogs
- [[Install Phase Index]]
- [[Systemd Service Index]]
- [[Automation Index]]
- [[Config Index]]
- [[Validation Index]]

## Working Rules
- Regenerate generated notes after structural repo changes with `python3 "${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}" --sync --repo .`.
- Keep `python3 tools/sync_obsidian_vault.py` only as a compatibility wrapper for legacy OpenBox workflows.
- Use the backlog note as the engineering queue, not scattered ad-hoc todos.
- Keep primary technical truth in the repo files; use the vault to connect context, decisions, and research.
