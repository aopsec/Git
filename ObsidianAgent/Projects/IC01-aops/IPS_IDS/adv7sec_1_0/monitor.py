"""Snapshot-based monitoring helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from adv7sec_1_0.models import MonitorRecord, MonitorStatus


def _tail_text(path: Path, lines: int) -> str:
    if not path.is_file():
        return "file missing"
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    tail = "\n".join(content[-lines:])
    return tail if tail else "file present but empty"


def snapshot_monitor(lines: int) -> list[MonitorRecord]:
    """Return a one-shot snapshot of local live sources."""
    records: list[MonitorRecord] = []
    journal_units = (
        "auditd.service",
        "falco-modern-bpf.service",
        "suricata.service",
        "unbound.service",
    )
    for unit in journal_units:
        result = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager"],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            journal_status: MonitorStatus = (
                "warn" if result.stdout.strip() == "-- No entries --" else "ok"
            )
            records.append(
                MonitorRecord(
                    source=f"journal:{unit}",
                    status=journal_status,
                    summary=result.stdout.strip(),
                )
            )
        elif result.returncode == 0:
            records.append(
                MonitorRecord(
                    source=f"journal:{unit}",
                    status="warn",
                    summary="unit found but no recent lines",
                )
            )
        else:
            records.append(
                MonitorRecord(
                    source=f"journal:{unit}",
                    status="missing",
                    summary=result.stderr.strip() or "journal unavailable",
                )
            )
    files = (
        Path("/var/log/suricata/eve.json"),
        Path("/var/log/falco-events.json"),
        Path("/var/log/clamav/clamonacc.log"),
    )
    for path in files:
        summary = _tail_text(path, lines)
        status: MonitorStatus = (
            "ok" if path.is_file() and summary not in {"file present but empty"} else "warn"
        )
        if not path.exists():
            status = "missing"
        records.append(MonitorRecord(source=str(path), status=status, summary=summary))
    return records
