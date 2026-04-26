---
project: ADV7ia
type: source-note
category: Validation
source_path: tests/validate-obsidian-vault.sh
tags:
  - adv7ia
  - validation
  - source-note
---

# Validation - Validate Obsidian Vault

## Role
[FIX-ADV7IA-TEST-01] Confirm that the ADV7ia vault wrappers and generated notes stay in sync.

## Source
- Path: `tests/validate-obsidian-vault.sh`
- Open: [source](../../../tests/validate-obsidian-vault.sh)
- Lines: 91

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `is_valid_agent_home() {`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
