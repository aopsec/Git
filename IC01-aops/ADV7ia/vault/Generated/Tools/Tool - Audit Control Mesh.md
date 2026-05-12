---
project: ADV7ia
type: source-note
category: Tools
source_path: tools/audit-control-mesh
tags:
  - adv7ia
  - tool
  - source-note
---

# Tool - Audit Control Mesh

## Role
[FIX-ADV7IA-CM-05] Audit the control-mesh templates and optionally the live runtime.

## Source
- Path: `tools/audit-control-mesh`
- Open: [source](../../../tools/audit-control-mesh)
- Lines: 209

## Related Notes
- [[README]]
- [[LOCAL_AI_STACK_RUNBOOK]]
- [[LOCAL_AI_STACK_ARCH_LMSTUDIO_GUIDE]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `local label="$1"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
