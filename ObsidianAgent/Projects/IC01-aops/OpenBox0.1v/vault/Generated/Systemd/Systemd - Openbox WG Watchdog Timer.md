---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-wg-watchdog.timer
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox WG Watchdog Timer

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-wg-watchdog.timer`.

## Source
- Path: `systemd/openbox-wg-watchdog.timer`
- Open: [source](../../../systemd/openbox-wg-watchdog.timer)
- Lines: 10

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]

## Highlights
- `Description=OpenBox WG watchdog every 60s`
- `OnBootSec=2min`
- `OnUnitActiveSec=60s`
- `AccuracySec=10s`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
