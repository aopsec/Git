---
project: bbWebScan
type: source-note
category: Stages
source_path: bbwebscan/stages/discovery_stage.py
tags:
  - bb-web-scan
  - bbwebscan-stage
  - source-note
---

# Stage - Stages - discovery_stage.py

## Role
Source note for `bbwebscan/stages/discovery_stage.py`.

## Source
- Path: `bbwebscan/stages/discovery_stage.py`
- Open: [source](../../../bbwebscan/stages/discovery_stage.py)
- Lines: 125

## Related Notes
- [[README]]

## Highlights
- `from pathlib import Path`
- `from bbwebscan.auth import build_header_args`
- `from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig`
- `from bbwebscan.stages._jsonl import load_json_or_jsonl`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
