---
project: OpenBox
type: source-note
category: Configs
source_path: etc/ssh/sshd_config.d/99-openbox.conf
tags:
  - openbox
  - config
  - source-note
---

# Config - Sshd Config D - 99-openbox.conf

## Role
SSH hardening (CIS-aligned)

## Source
- Path: `etc/ssh/sshd_config.d/99-openbox.conf`
- Open: [source](../../../etc/ssh/sshd_config.d/99-openbox.conf)
- Lines: 45

## Related Notes
- [[README]]

## Highlights
- `Port 22`
- `Protocol 2`
- `AddressFamily inet                          # IPv4 only`
- `PermitRootLogin no`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
