---
project: OpenBox
type: source-note
category: Validation
source_path: tests/phase-b-vault-tool.sh
tags:
  - openbox
  - validation
  - source-note
---

# Validation - Phase B Vault Tool

## Role
[VAULT-C] Phase B/Phase C proof for repo-neutral vault tooling.

## Source
- Path: `tests/phase-b-vault-tool.sh`
- Open: [source](../../../tests/phase-b-vault-tool.sh)
- Lines: 150

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `resolve_agent_home() {`
- `printf '%s\n' "${AOPS_OBSIDIAN_AGENT_HOME}"`
- `return 0`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
