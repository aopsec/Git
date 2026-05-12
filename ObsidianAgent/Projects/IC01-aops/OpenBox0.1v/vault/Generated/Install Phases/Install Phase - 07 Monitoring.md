---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/07-monitoring.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 07 Monitoring

## Role
Netdata, Uptime Kuma, Cockpit, Monit, ntfy, Caddy

## Source
- Path: `install.d/07-monitoring.sh`
- Open: [source](../../../install.d/07-monitoring.sh)
- Lines: 76

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `shopt -s inherit_errexit`
- `. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"`
- `echo "[07-monitoring] Para Netdata: baixar e inspecionar https://my-netdata.io/kickstart.sh antes de executar"`
- `run env DEBIAN_FRONTEND=noninteractive apt install -y netdata`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
