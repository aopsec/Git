---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-lynis.service
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Lynis Service

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-lynis.service`.

## Source
- Path: `systemd/openbox-lynis.service`
- Open: [source](../../../systemd/openbox-lynis.service)
- Lines: 7

## Related Notes
- [[README]]

## Highlights
- `Description=OpenBox Lynis security audit (weekly)`
- `Type=oneshot`
- `ExecStart=/usr/sbin/lynis audit system --quiet --no-colors --report-file /var/log/lynis-report.dat`
- `ExecStartPost=/usr/local/sbin/openbox-lynis-notify.sh`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
