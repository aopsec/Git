---
project: OpenBox
type: source-note
category: Install Phases
source_path: install.d/04-dns.sh
tags:
  - openbox
  - install-phase
  - source-note
---

# Install Phase - 04 DNS

## Role
dnscrypt-proxy + Pi-hole

## Source
- Path: `install.d/04-dns.sh`
- Open: [source](../../../install.d/04-dns.sh)
- Lines: 63

## Related Notes
- [[README]]
- [[THREAT_MODEL]]
- [[RUNBOOK]]
- [[REFERENCES]]

## Highlights
- `shopt -s inherit_errexit`
- `PIHOLE_ADMIN_PORT="${OPENBOX_PIHOLE_ADMIN_PORT:-8081}"`
- `install_dnscrypt_socket_override() {`
- `local target="/etc/systemd/system/dnscrypt-proxy.socket.d/openbox-listen.conf"`

## Review Angle
- What this file changes in the stack.
- What can fail if this file is misconfigured.
- Which operational docs should be updated when this file changes.
