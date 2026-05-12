---
project: ADV7ia
type: dashboard
tags:
  - adv7ia
  - control-mesh
  - dashboard
---

# ADV7ia Control Mesh

## Control Plane

- [[CONTROL_MESH_RUNBOOK]]
- [[Task Queue]]
- [[Session Ledger]]
- [[Security Policy]]
- [[Incident Review]]

## Runtime Commands

- `bash tools/control-mesh status`
- `bash tools/control-mesh brief`
- `bash tools/control-mesh compact --session-id session-bootstrap-openhands --force`
- `bash tools/audit-control-mesh`

## Security Boundary

- OpenHands UI: `http://127.0.0.1:3000`
- LAN proxy: `https://adv7ia-control.home.arpa:8443`
- Recursive writes and network changes stay behind approval gates.
