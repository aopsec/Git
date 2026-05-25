---
project: ADV7ia
type: source-note
category: Tools
source_path: tools/bootstrap-adv7ia-rag
tags:
  - adv7ia
  - tool
  - source-note
---

# Tool - Bootstrap Adv7ia Rag

## Role
[FIX-ADV7IA-TOOLS-08] Bootstrap the default ADV7ia repo RAG collection only when needed.

## Source
- Path: `tools/bootstrap-adv7ia-rag`
- Open: [source](../../../tools/bootstrap-adv7ia-rag)
- Lines: 85

## Related Notes
- [[README]]
- [[RAG_QDRANT_OK]]
- [[RAG_MCP_OK]]
- [[LOCAL_AI_STACK_RUNBOOK]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `usage() {`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
