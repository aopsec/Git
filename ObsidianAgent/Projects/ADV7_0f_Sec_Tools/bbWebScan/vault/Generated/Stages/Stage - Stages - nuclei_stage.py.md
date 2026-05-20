---
project: bbWebScan
type: source-note
category: Stages
source_path: bbwebscan/stages/nuclei_stage.py
tags:
  - bb-web-scan
  - bbwebscan-stage
  - source-note
---

# Stage - Stages - nuclei_stage.py

## Role
[SEC-BBW-03] Apply target cap to prevent target explosion and timeouts.

## Source
- Path: `bbwebscan/stages/nuclei_stage.py`
- Open: [source](../../../bbwebscan/stages/nuclei_stage.py)
- Lines: 57

## Related Notes
- [[README]]

## Highlights
- `import sys`
- `from pathlib import Path`
- `from bbwebscan.auth import build_header_args`
- `from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
