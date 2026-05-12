---
project: OpenBox
type: backlog
tags:
  - openbox
  - backlog
  - delivery
---

# OpenBox Delivery Backlog

## Critical
- [ ] Make SSH bootstrap safe: do not ship `AllowUsers openbox` without creating or parameterizing the operator account. Links: [[README]], [[THREAT_MODEL]]
- [ ] Fix the WireGuard full-tunnel routing model so LAN access and fail-closed behavior are coherent. Links: [[HARDENING_PLAN_v2]], [[RUNBOOK]], [[Config Index]]
- [ ] Gate Tor startup on valid controller auth instead of restarting with placeholders. Links: [[TOR_STREAMING_CAVEAT]], [[Systemd Service Index]], [[Config Index]]
- [ ] Gate Caddy startup on a real auth hash and a validated config. Links: [[Config Index]], [[RUNBOOK]]

## High
- [ ] Replace the current DNS leak checker with evidence from allowed egress paths, not upstream resolver IP guesses. Links: [[THREAT_MODEL]], [[Validation Index]]
- [ ] Resolve the Pi-hole and Caddy web port/prefix model so `/pihole` is deliberate and reproducible. Links: [[Config Index]], [[RUNBOOK]]
- [ ] Stop enabling the WireGuard watchdog before WireGuard is intentionally configured. Links: [[Systemd Service Index]], [[Automation Index]]
- [ ] Remove remaining dry-run side effects from installer phases. Links: [[Install Phase Index]]

## Medium
- [ ] Ship missing Fail2Ban filters or disable the custom jails until they exist. Links: [[Config Index]]
- [ ] Upgrade CI from header checks to real unit validation and generated-vault validation. Links: [[Validation Index]]
- [ ] Add decision records for networking, DNS validation, and admin-plane auth. Links: [[ADR Template]]

## Vault-Specific
- [ ] Keep generated note titles stable when repository paths change.
- [ ] Add more operational templates only if they are actually used.
