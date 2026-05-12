---
project: OpenBox
type: source-note
category: Validation
source_path: tests/validate-obsidian-vault.sh
tags:
  - openbox
  - validation
  - source-note
---

# Validation - Validate Obsidian Vault

## Role
generated Obsidian vault must match repo

## Source
- Path: `tests/validate-obsidian-vault.sh`
- Open: [source](../../../tests/validate-obsidian-vault.sh)
- Lines: 53

## Related Notes
- [[README]]
- [[RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `SCRIPT="${ROOT}/tools/sync_obsidian_vault.py"`
- `resolve_agent_home() {`
- `printf '%s\n' "${AOPS_OBSIDIAN_AGENT_HOME}"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
