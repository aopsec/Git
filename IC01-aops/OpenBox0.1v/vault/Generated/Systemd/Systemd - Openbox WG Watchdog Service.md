---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-wg-watchdog.service
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox WG Watchdog Service

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-wg-watchdog.service`.

## Source
- Path: `systemd/openbox-wg-watchdog.service`
- Open: [source](../../../systemd/openbox-wg-watchdog.service)
- Lines: 8

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]

## Highlights
- `Description=OpenBox WireGuard handshake watchdog`
- `After=wg-quick@wg0.service`
- `Wants=wg-quick@wg0.service`
- `Type=oneshot`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
