---
project: OpenBox
type: research-queue
tags:
  - openbox
  - research
---

# Experiment Queue

## Network Correctness
- [ ] Validate WireGuard routing with local LAN access preserved and internet egress forced through `wg0`.
- [ ] Capture nftables counters before and after `wg0` stop/start to prove fail-closed behavior.

## DNS
- [ ] Measure resolver behavior with `dnscrypt-proxy` anonymized DNS enabled.
- [ ] Replace resolver-IP leak heuristics with packet-level or firewall-counter evidence.

## Performance
- [ ] Run an `iperf3` baseline without WireGuard.
- [ ] Run an `iperf3` baseline with WireGuard.
- [ ] Run Flent RRUL to observe latency under load once hardware testing starts.

## Monitoring Plane
- [ ] Validate Netdata, Caddy, and Pi-hole exposure boundaries from LAN and non-LAN contexts.
- [ ] Confirm that watchdogs only restart components that are intentionally enabled.
