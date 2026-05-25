---
project: ADV7ia
type: source-note
category: Validation
source_path: tests/validate-control-mesh.sh
tags:
  - adv7ia
  - validation
  - source-note
---

# Validation - Validate Control Mesh

## Role
[FIX-ADV7IA-CM-04] Validate the repo-local control mesh and its security templates.

## Source
- Path: `tests/validate-control-mesh.sh`
- Open: [source](../../../tests/validate-control-mesh.sh)
- Lines: 56

## Related Notes
- [[README]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `trap cleanup EXIT INT`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
