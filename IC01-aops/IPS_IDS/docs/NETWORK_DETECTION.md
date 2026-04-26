# Network Detection

Network detection uses Suricata, Zeek, and Unbound dnstap.

## Suricata

Phase 1 runs IDS-only. It should monitor the interface that carries the traffic you need to decode:

- physical uplink for outer tunnel health
- tunnel interface for app-layer visibility under full-tunnel VPN

Source configs:

- `etc/suricata/eve-minimal.yaml`
- `etc/suricata/disable.conf`

## Zeek

Zeek is co-equal with Suricata for protocol logs and metadata. Configure `node.cfg` after confirming the active interface.

zkg packages:

- JA4
- HASSH
- passive DNS

## Unbound Dnstap

`etc/unbound/unbound.conf.d/dnstap.conf` exposes structured DNS telemetry for optional collectors.
