---
project: ADV7ia
type: source-note
category: Tools
source_path: tools/audit-local-ai-stack
tags:
  - adv7ia
  - tool
  - source-note
---

# Tool - Audit Local Ai Stack

## Role
[FIX-ADV7IA-TOOLS-02] Remove hardcoded source paths and use repo-local tools by default.

## Source
- Path: `tools/audit-local-ai-stack`
- Open: [source](../../../tools/audit-local-ai-stack)
- Lines: 183

## Related Notes
- [[README]]
- [[LOCAL_AI_STACK_RUNBOOK]]
- [[LOCAL_AI_STACK_ARCH_LMSTUDIO_GUIDE]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `print_service_state() {`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
