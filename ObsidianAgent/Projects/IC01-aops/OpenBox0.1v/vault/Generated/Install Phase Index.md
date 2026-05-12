---
project: OpenBox
type: generated-index
category: Install Phases
tags:
  - openbox
  - generated-index
---

# Install Phases Index

Generated from the repository by `plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`.

| Note | Source | Role |
|---|---|---|
| [[Install Phase - 00 Base]] | `install.d/00-base.sh` | OpenBox base hardening |
| [[Install Phase - 01 Sysctl]] | `install.d/01-sysctl.sh` | kernel tuning |
| [[Install Phase - 02 Nftables]] | `install.d/02-nftables.sh` | firewall + kill switch |
| [[Install Phase - 03 WireGuard]] | `install.d/03-wireguard.sh` | WireGuard com fwmark routing |
| [[Install Phase - 04 DNS]] | `install.d/04-dns.sh` | dnscrypt-proxy + Pi-hole |
| [[Install Phase - 05 Tor]] | `install.d/05-tor.sh` | Tor hardened |
| [[Install Phase - 06 Media]] | `install.d/06-media.sh` | Jellyfin media server via Docker (armhf nativo) |
| [[Install Phase - 07 Monitoring]] | `install.d/07-monitoring.sh` | Netdata, Uptime Kuma, Cockpit, Monit, ntfy, Caddy |
| [[Install Phase - 08 Watchdogs]] | `install.d/08-watchdogs.sh` | WG, Tor, DNS leak, ntfy |
| [[Install Phase - 09 Validate]] | `install.d/09-validate.sh` | validacao final |
| [[Install Phase - Lib]] | `install.d/_lib.sh` | shared helpers for OpenBox phase scripts. |

## Related Dashboards
- [[OpenBox Vault Home]]
- [[OpenBox Project Dashboard]]
