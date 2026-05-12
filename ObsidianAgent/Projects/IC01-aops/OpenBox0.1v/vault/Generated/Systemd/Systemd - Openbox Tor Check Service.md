---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-tor-check.service
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Tor Check Service

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-tor-check.service`.

## Source
- Path: `systemd/openbox-tor-check.service`
- Open: [source](../../../systemd/openbox-tor-check.service)
- Lines: 8

## Related Notes
- [[README]]
- [[TOR_STREAMING_CAVEAT]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `Description=OpenBox Tor circuit health check`
- `After=tor.service network-online.target`
- `Wants=tor.service`
- `Type=oneshot`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
