---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-tor-check.timer
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Tor Check Timer

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-tor-check.timer`.

## Source
- Path: `systemd/openbox-tor-check.timer`
- Open: [source](../../../systemd/openbox-tor-check.timer)
- Lines: 11

## Related Notes
- [[README]]
- [[TOR_STREAMING_CAVEAT]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `Description=OpenBox Tor check every 30min`
- `OnBootSec=5min`
- `OnUnitActiveSec=30min`
- `Persistent=true`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
