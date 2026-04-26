---
project: OpenBox
type: source-note
category: Configs
source_path: etc/wireguard/wg0.conf.example
tags:
  - openbox
  - config
  - source-note
---

# Config - WireGuard - wg0.conf.example

## Role
exemplo. Renomear para wg0.conf e preencher chaves reais.

## Source
- Path: `etc/wireguard/wg0.conf.example`
- Open: [source](../../../etc/wireguard/wg0.conf.example)
- Lines: 35

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[HARDENING_PLAN_v2]]
- [[RUNBOOK]]

## Highlights
- `PrivateKey = REPLACE_WITH_CLIENT_PRIVATE_KEY`
- `Address    = 10.66.66.2/32`
- `DNS        = 127.0.0.1                  # Pi-hole local`
- `MTU        = 1420                        # 1500 - 80 (overhead WG IPv4)`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
