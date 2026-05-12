---
project: OpenBox
type: source-note
category: Systemd
source_path: systemd/openbox-dnsleak-check.service
tags:
  - openbox
  - systemd
  - source-note
---

# Systemd - Openbox Dnsleak Check Service

## Role
Source note for `/home/aops/ObsidianAgent/Projects/OpenBox0.1v/systemd/openbox-dnsleak-check.service`.

## Source
- Path: `systemd/openbox-dnsleak-check.service`
- Open: [source](../../../systemd/openbox-dnsleak-check.service)
- Lines: 7

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `Description=OpenBox DNS leak check`
- `After=pihole-FTL.service dnscrypt-proxy.service`
- `Type=oneshot`
- `ExecStart=/usr/local/sbin/openbox-dnsleak-check.sh`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
