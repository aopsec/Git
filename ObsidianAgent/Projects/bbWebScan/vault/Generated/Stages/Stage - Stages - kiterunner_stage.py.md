---
project: bbWebScan
type: source-note
category: Stages
source_path: bbwebscan/stages/kiterunner_stage.py
tags:
  - bb-web-scan
  - bbwebscan-stage
  - source-note
---

# Stage - Stages - kiterunner_stage.py

## Role
kiterunner status code → severity. 200/3xx = info (route exists, public);

## Source
- Path: `bbwebscan/stages/kiterunner_stage.py`
- Open: [source](../../../bbwebscan/stages/kiterunner_stage.py)
- Lines: 104

## Related Notes
- [[README]]

## Highlights
- `"""kiterunner scan stage — API route discovery alongside ffuf.`
- `[v0.5.0] Vault citation: hacking-apis p. 124 (`assetnote/kiterunner`).`
- `Command shape derived from observed `kiterunner scan -h` against`
- `kiterunner v1.0.2 (binary name: `kiterunner`, despite docs occasionally`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
