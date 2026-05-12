---
project: OpenBox
type: source-note
category: Configs
source_path: etc/caddy/Caddyfile
tags:
  - openbox
  - config
  - source-note
---

# Config - Caddy - Caddyfile

## Role
reverse proxy com TLS interno para paineis administrativos.

## Source
- Path: `etc/caddy/Caddyfile`
- Open: [source](../../../etc/caddy/Caddyfile)
- Lines: 74

## Related Notes
- [[README]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `local_certs`
- `admin off`
- `openbox.lan {`
- `tls internal`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
