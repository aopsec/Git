# Host Detection

Host detection uses auditd, Falco, Kunai, AIDE, Lynis, chkrootkit, and unhide.

## auditd

Primary role: durable forensic trail for identity, persistence, firewall, time, and module changes.

Source config: `etc/audit/rules.d/50-persistence.rules`.

## Falco

Primary role: runtime behavioral alerts through modern eBPF.

Source configs:

- `etc/falco/falco.local.yaml`
- `etc/falco/rules.d/workstation.yaml`

## Kunai

Primary role: complementary eBPF event stream. It is non-critical in Phase 1 because packaging may drift.

## AIDE

Primary role: file integrity baseline with an Arch pacman hook to prevent routine package upgrades from becoming false-positive floods.
