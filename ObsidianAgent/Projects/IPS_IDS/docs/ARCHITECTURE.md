# Architecture

Phase 1 is a visibility stack:

```text
auditd -> journald
Falco modern eBPF -> journald + /var/log/falco-events.json
Kunai -> journald
Suricata -> /var/log/suricata/eve.json
Zeek -> zeek logs
Unbound dnstap -> /run/unbound/dnstap.sock
AIDE/ClamAV/YARA/Lynis -> timers and local logs
```

The system is intentionally local-first. It collects evidence without changing firewall policy or blocking execution.

## Trust Boundaries

- Root owns installation and service management.
- Package trust comes from Arch repositories, AUR helper review, and pinned configs in `etc/`.
- Phase 1 logs stay local.
- Phase 3 response must consume tuned events, not raw first-week output.
