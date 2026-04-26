---
project: OpenBox
type: generated-index
category: Configs
tags:
  - openbox
  - generated-index
---

# Configs Index

Generated from the repository by `plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`.

| Note | Source | Role |
|---|---|---|
| [[Config - Nftables - openbox-base.nft]] | `etc/nftables/openbox-base.nft` | atomic ruleset com WireGuard kill switch via fwmark 51820. |
| [[Config - Tor - torrc.example]] | `etc/tor/torrc.example` | OpenBox v0.1 |
| [[Config - Dnscrypt Proxy - dnscrypt-proxy.toml]] | `etc/dnscrypt-proxy/dnscrypt-proxy.toml` | DoH/DoT/DoQ + DNSSEC + anonymized relays |
| [[Config - Caddy - Caddyfile]] | `etc/caddy/Caddyfile` | reverse proxy com TLS interno para paineis administrativos. |
| [[Config - Sshd Config D - 99-openbox.conf]] | `etc/ssh/sshd_config.d/99-openbox.conf` | SSH hardening (CIS-aligned) |
| [[Config - Jail D - openbox.conf]] | `etc/fail2ban/jail.d/openbox.conf` | jails para SSH e auth HTTP via Caddy |
| [[Config - Monitrc D - openbox.conf]] | `etc/monit/monitrc.d/openbox.conf` | auto-restart de servicos criticos |
| [[Config - Sysctl D - 99-openbox.conf]] | `etc/sysctl.d/99-openbox.conf` | kernel tuning para streaming + privacidade. |
| [[Config - WireGuard - wg0.conf.example]] | `etc/wireguard/wg0.conf.example` | exemplo. Renomear para wg0.conf e preencher chaves reais. |

## Related Dashboards
- [[OpenBox Vault Home]]
- [[OpenBox Project Dashboard]]
