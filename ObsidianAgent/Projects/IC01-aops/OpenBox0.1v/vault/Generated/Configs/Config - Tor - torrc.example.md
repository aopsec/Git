---
project: OpenBox
type: source-note
category: Configs
source_path: etc/tor/torrc.example
tags:
  - openbox
  - config
  - source-note
---

# Config - Tor - torrc.example

## Role
OpenBox v0.1

## Source
- Path: `etc/tor/torrc.example`
- Open: [source](../../../etc/tor/torrc.example)
- Lines: 49

## Related Notes
- [[README]]
- [[TOR_STREAMING_CAVEAT]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `ControlPort 127.0.0.1:9051`
- `CookieAuthentication 1`
- `AvoidDiskWrites 1`
- `DisableAllSwap 1`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
