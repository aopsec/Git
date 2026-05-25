---
project: ADV7ia
type: source-note
category: Tools
source_path: tools/mcp-git-aider-test
tags:
  - adv7ia
  - tool
  - source-note
---

# Tool - Mcp Git Aider Test

## Role
[FIX-ADV7IA-TOOLS-06] Keep Git MCP tied to the live source repo unless overridden.

## Source
- Path: `tools/mcp-git-aider-test`
- Open: [source](../../../tools/mcp-git-aider-test)
- Lines: 31

## Related Notes
- [[README]]
- [[MCP_FILESYSTEM_OK]]
- [[GIT_MCP_OK]]
- [[RAG_MCP_OK]]

## Highlights
- `shopt -s inherit_errexit`
- `cleanup() {`
- `:`
- `main() {`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
