---
project: ADV7ia
type: dashboard
tags:
  - adv7ia
  - dashboard
  - operations
---

# ADV7ia Operations Dashboard

## Operational Docs

- [[README]]
- [[CONTROL_MESH_RUNBOOK]]
- [[LOCAL_AI_STACK_RUNBOOK]]
- [[LOCAL_AI_STACK_ARCH_LMSTUDIO_GUIDE]]

## Runtime Tools

- [[Tool Index]]
- `bash tools/control-mesh status`
- `bash tools/control-mesh compact --session-id session-bootstrap-openhands --force`
- `bash tools/audit-control-mesh`
- `bash tools/ai-stack-status`
- `bash tools/index-aider-test-rag`
- `bash tools/query-aider-test-rag "filesystem MCP and git MCP validation"`

## Validation

- [[Validation Index]]
- `bash tests/validate-project-layout.sh`
- `bash tests/validate-obsidian-vault.sh`
- `bash tests/validate-control-mesh.sh`

## Evidence

- [[Evidence Index]]
- Which checks are current runtime status versus imported proof snapshots?
- Which wrappers operate on `ADV7ia` directly and which still target the live source repo?
- Which runtime findings are policy drift versus acceptable degraded mode?
