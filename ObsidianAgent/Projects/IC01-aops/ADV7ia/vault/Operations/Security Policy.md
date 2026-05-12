---
project: ADV7ia
type: operations-note
tags:
  - adv7ia
  - security-policy
---

# Security Policy

## Runtime Rules

- OpenHands UI binds to `127.0.0.1:3000`.
- Caddy owns the LAN-facing `adv7ia-control.home.arpa:8443` endpoint.
- Mutual TLS is required for LAN proxy access.
- `--network host` and `privileged=true` remain forbidden.

## Approval Gates

- `edit`
- `network`
- `secret`
- `privileged`
- `destructive`
