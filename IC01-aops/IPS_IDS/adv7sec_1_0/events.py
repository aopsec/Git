"""Live event collection and normalization."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from adv7sec_1_0.models import EventSeverity, ThreatEvent

_JOURNAL_UNITS = (
    "auditd.service",
    "falco-modern-bpf.service",
    "suricata.service",
    "unbound.service",
)
_LOG_FILES = (
    Path("/var/log/suricata/eve.json"),
    Path("/var/log/falco-events.json"),
    Path("/var/log/clamav/clamonacc.log"),
)


def _priority_to_severity(priority: str | int | None) -> EventSeverity:
    numeric = int(priority) if isinstance(priority, str) and priority.isdigit() else priority
    if numeric in {0, 1, 2}:
        return "critical"
    if numeric == 3:
        return "high"
    if numeric == 4:
        return "medium"
    if numeric in {5, 6}:
        return "low"
    return "info"


def _suricata_severity(payload: dict[str, object]) -> EventSeverity:
    alert = payload.get("alert")
    if isinstance(alert, dict):
        severity = alert.get("severity")
        if severity == 1:
            return "critical"
        if severity == 2:
            return "high"
        if severity == 3:
            return "medium"
    return "low"


def _falco_severity(priority: object) -> EventSeverity:
    if not isinstance(priority, str):
        return "medium"
    normalized = priority.lower()
    if normalized in {"emergency", "alert", "critical"}:
        return "critical"
    if normalized == "error":
        return "high"
    if normalized in {"warning", "notice"}:
        return "medium"
    if normalized in {"informational", "info", "debug"}:
        return "low"
    return "medium"


def _normalize_journal(unit: str, line: str) -> ThreatEvent | None:
    payload = json.loads(line)
    message = str(payload.get("MESSAGE", "")).strip()
    if not message:
        return None
    pid_value = payload.get("_PID")
    pid = int(pid_value) if isinstance(pid_value, str) and pid_value.isdigit() else None
    return ThreatEvent(
        source=f"journal:{unit}",
        channel="journal",
        severity=_priority_to_severity(payload.get("PRIORITY")),
        summary=message,
        raw=line,
        pid=pid,
    )


def _normalize_file(path: Path, line: str) -> ThreatEvent | None:
    stripped = line.strip()
    if not stripped:
        return None
    if path.name == "clamonacc.log":
        lowered = stripped.lower()
        path_hint = stripped.split(":")[0] if ":" in stripped else None
        return ThreatEvent(
            source=str(path),
            channel="file",
            severity="critical" if "found" in lowered else "medium",
            summary=stripped,
            raw=stripped,
            path=path_hint,
        )
    payload = json.loads(stripped)
    if path.name == "eve.json":
        alert = payload.get("alert")
        summary = "suricata event"
        rule = None
        if isinstance(alert, dict):
            summary = str(alert.get("signature", summary))
            rule = str(alert.get("signature_id")) if alert.get("signature_id") else None
        return ThreatEvent(
            source=str(path),
            channel="file",
            severity=_suricata_severity(payload),
            summary=summary,
            raw=stripped,
            rule=rule,
        )
    output_fields = payload.get("output_fields")
    pid = None
    path_hint = None
    if isinstance(output_fields, dict):
        proc_pid = output_fields.get("proc.pid")
        fd_name = output_fields.get("fd.name")
        pid = int(proc_pid) if isinstance(proc_pid, str) and proc_pid.isdigit() else None
        path_hint = str(fd_name) if isinstance(fd_name, str) else None
    return ThreatEvent(
        source=str(path),
        channel="file",
        severity=_falco_severity(payload.get("priority", "medium")),
        summary=str(payload.get("output", "falco event")),
        raw=stripped,
        rule=str(payload.get("rule")) if payload.get("rule") else None,
        pid=pid,
        path=path_hint,
    )


def collect_live_events(lines: int) -> list[ThreatEvent]:
    """[FIX-LIVE-PIPELINE] Collect normalized events from local live telemetry."""
    events: list[ThreatEvent] = []
    for unit in _JOURNAL_UNITS:
        result = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "-o", "json", "--no-pager"],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            try:
                event = _normalize_journal(unit, line)
            except json.JSONDecodeError:
                continue
            if event is not None:
                events.append(event)
    for path in _LOG_FILES:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]
        for line in content:
            try:
                event = _normalize_file(path, line)
            except json.JSONDecodeError:
                continue
            if event is not None:
                events.append(event)
    return events
