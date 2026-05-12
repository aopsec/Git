---
project: OpenBox
type: source-note
category: Configs
source_path: etc/fail2ban/jail.d/openbox.conf
tags:
  - openbox
  - config
  - source-note
---

# Config - Jail D - openbox.conf

## Role
jails para SSH e auth HTTP via Caddy

## Source
- Path: `etc/fail2ban/jail.d/openbox.conf`
- Open: [source](../../../etc/fail2ban/jail.d/openbox.conf)
- Lines: 32

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]

## Highlights
- `banaction = nftables-multiport`
- `bantime  = 600`
- `maxretry = 5`
- `backend  = systemd`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
