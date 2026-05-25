---
project: ADV7ia
type: source-note
category: Validation
source_path: tests/validate-project-layout.sh
tags:
  - adv7ia
  - validation
  - source-note
---

# Validation - Validate Project Layout

## Role
[FIX-ADV7IA-TEST-02] Verify that the curated ADV7ia import kept required files and excluded ephemeral state.

## Source
- Path: `tests/validate-project-layout.sh`
- Open: [source](../../../tests/validate-project-layout.sh)
- Lines: 129

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `printf '  [ok]   %s\n' "$1"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
