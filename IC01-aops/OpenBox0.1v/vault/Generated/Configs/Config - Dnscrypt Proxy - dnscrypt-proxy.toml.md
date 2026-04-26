---
project: OpenBox
type: source-note
category: Configs
source_path: etc/dnscrypt-proxy/dnscrypt-proxy.toml
tags:
  - openbox
  - config
  - source-note
---

# Config - Dnscrypt Proxy - dnscrypt-proxy.toml

## Role
DoH/DoT/DoQ + DNSSEC + anonymized relays

## Source
- Path: `etc/dnscrypt-proxy/dnscrypt-proxy.toml`
- Open: [source](../../../etc/dnscrypt-proxy/dnscrypt-proxy.toml)
- Lines: 78

## Related Notes
- [[README]]

## Highlights
- `listen_addresses = ['127.0.0.1:5053']`
- `max_clients = 250`
- `ipv4_servers = true`
- `ipv6_servers = false                    # IPv6 desativado consistente com sysctl`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
