"""Basic runtime smoke checks for the unified control plane."""

from __future__ import annotations

from pathlib import Path

from adv7sec_1_0.models import MonitorRecord

_PATH_CHECKS: tuple[tuple[str, str], ...] = (
    ("auditd", "/etc/audit/rules.d/50-persistence.rules"),
    ("suricata", "/etc/suricata/eve-minimal.yaml"),
    ("suricata", "/etc/default/ipsids-suricata"),
    ("unbound", "/etc/unbound/unbound.conf.d/dnstap.conf"),
    ("unbound", "/run/unbound"),
    ("aide", "/etc/aide.conf"),
    ("aide", "/var/lib/aide"),
)


def run_smoke_checks(root_dir: Path) -> list[MonitorRecord]:
    """[FIX-UNIFIED-INSTALL] Verify that exported core artifacts exist."""
    records: list[MonitorRecord] = []
    for feature, file_path in _PATH_CHECKS:
        target = root_dir / file_path.lstrip("/")
        exists = target.exists()
        records.append(
            MonitorRecord(
                source=f"smoke:{feature}",
                status="ok" if exists else "missing",
                summary=f"{target} {'present' if exists else 'missing'}",
            )
        )
    return records
