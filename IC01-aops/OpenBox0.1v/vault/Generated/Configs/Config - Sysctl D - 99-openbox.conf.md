---
project: OpenBox
type: source-note
category: Configs
source_path: etc/sysctl.d/99-openbox.conf
tags:
  - openbox
  - config
  - source-note
---

# Config - Sysctl D - 99-openbox.conf

## Role
kernel tuning para streaming + privacidade.

## Source
- Path: `etc/sysctl.d/99-openbox.conf`
- Open: [source](../../../etc/sysctl.d/99-openbox.conf)
- Lines: 49

## Related Notes
- [[README]]
- [[HARDENING_PLAN_v2]]
- [[CASE_STUDY]]

## Highlights
- `net.core.default_qdisc = fq`
- `net.ipv4.tcp_congestion_control = bbr`
- `net.core.rmem_max = 4194304`
- `net.core.wmem_max = 4194304`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
