---
project: ADV7ia
type: source-note
category: Tools
source_path: tools/mcp-rag-aider-test
tags:
  - adv7ia
  - tool
  - source-note
---

# Tool - Mcp Rag Aider Test

## Role
[FIX-ADV7IA-TOOLS-07] Add repo-local safeguards and env overrides to the RAG MCP wrapper.

## Source
- Path: `tools/mcp-rag-aider-test`
- Open: [source](../../../tools/mcp-rag-aider-test)
- Lines: 31

## Related Notes
- [[README]]
- [[RAG_QDRANT_OK]]
- [[RAG_MCP_OK]]
- [[LOCAL_AI_STACK_RUNBOOK]]
- [[MCP_FILESYSTEM_OK]]
- [[GIT_MCP_OK]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `main() {`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
