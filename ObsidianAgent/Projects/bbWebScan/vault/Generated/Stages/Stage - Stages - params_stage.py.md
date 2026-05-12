---
project: bbWebScan
type: source-note
category: Stages
source_path: bbwebscan/stages/params_stage.py
tags:
  - bb-web-scan
  - bbwebscan-stage
  - source-note
---

# Stage - Stages - params_stage.py

## Role
[FIX-BBW-04] Arjun accepts one --headers value with newline-separated headers.

## Source
- Path: `bbwebscan/stages/params_stage.py`
- Open: [source](../../../bbwebscan/stages/params_stage.py)
- Lines: 65

## Related Notes
- [[README]]

## Highlights
- `from pathlib import Path`
- `from bbwebscan.auth import build_header_lines`
- `from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig`
- `from bbwebscan.stages._jsonl import load_json_or_jsonl`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
