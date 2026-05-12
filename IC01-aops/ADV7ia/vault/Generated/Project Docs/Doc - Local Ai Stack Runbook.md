---
project: ADV7ia
type: source-note
category: Project Docs
source_path: docs/LOCAL_AI_STACK_RUNBOOK.md
tags:
  - adv7ia
  - project-doc
  - source-note
---

# Doc - Local Ai Stack Runbook

## Role
Qdrant persistence validation

## Source
- Path: `docs/LOCAL_AI_STACK_RUNBOOK.md`
- Open: [source](../../../docs/LOCAL_AI_STACK_RUNBOOK.md)
- Lines: 41

## Related Notes
- [[README]]

## Highlights
- `Qdrant persistence is validated when Docker inspect shows a bind mount or volume with:`
- ````text`
- `Destination: /qdrant/storage`
- `RW: true`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
