---
project: OpenBox
type: source-note
category: Configs
source_path: etc/nftables/openbox-base.nft
tags:
  - openbox
  - config
  - source-note
---

# Config - Nftables - openbox-base.nft

## Role
atomic ruleset com WireGuard kill switch via fwmark 51820.

## Source
- Path: `etc/nftables/openbox-base.nft`
- Open: [source](../../../etc/nftables/openbox-base.nft)
- Lines: 92

## Related Notes
- [[README]]
- [[HARDENING_PLAN_v2]]
- [[RUNBOOK]]
- [[THREAT_MODEL]]

## Highlights
- `define WG_ENDPOINT  = 203.0.113.1            # IP do servidor VPN (resolvido)`
- `define WG_PORT      = 51820`
- `define WG_FWMARK    = 51820`
- `define LAN_NET      = 192.168.0.0/16`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
