---
project: OpenBox
type: generated-index
category: Automation
tags:
  - openbox
  - generated-index
---

# Automation Index

Generated from the repository by `plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py`.

| Note | Source | Role |
|---|---|---|
| [[Automation - Openbox Container Running]] | `usr/local/sbin/openbox-container-running.sh` | [FIX-AUDIT-MONIT] Exit 0 only when a named Docker container exists and is running. |
| [[Automation - Openbox Dnsleak Check]] | `usr/local/sbin/openbox-dnsleak-check.sh` | DNS leak check (referencia: macvk/dnsleaktest) |
| [[Automation - Openbox Killswitch]] | `usr/local/sbin/openbox-killswitch.sh` | kill switch helper (re-aplica nftables atomic ruleset) |
| [[Automation - Openbox Lynis Notify]] | `usr/local/sbin/openbox-lynis-notify.sh` | extract lynis hardening index and send ntfy. |
| [[Automation - Openbox Ntfy Send]] | `usr/local/sbin/openbox-ntfy-send.sh` | helper para enviar notificacao via ntfy local |
| [[Automation - Openbox Tor Check]] | `usr/local/sbin/openbox-tor-check.sh` | verifica circuito Tor via check.torproject.org |
| [[Automation - Openbox Tune]] | `usr/local/sbin/openbox-tune.sh` | CAKE qdisc + IRQ affinity. Chamado pela openbox-tuning.service |
| [[Automation - Openbox WG Watchdog]] | `usr/local/sbin/openbox-wg-watchdog.sh` | verifica handshake WireGuard, restart se > THRESHOLD |

## Related Dashboards
- [[OpenBox Vault Home]]
- [[OpenBox Project Dashboard]]
