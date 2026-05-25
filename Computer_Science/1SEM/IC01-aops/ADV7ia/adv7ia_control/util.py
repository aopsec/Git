"""Small helpers shared across the control-mesh package."""
from __future__ import annotations

from datetime import UTC, datetime

from adv7ia_control.models import GateDecision


def dedupe(items: list[str]) -> list[str]:
    """Preserve order while removing duplicate strings."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def dedupe_gates(items: list[GateDecision]) -> list[GateDecision]:
    """Preserve one gate decision per action."""
    seen: set[str] = set()
    result: list[GateDecision] = []
    for item in items:
        if item.action not in seen:
            result.append(item)
            seen.add(item.action)
    return result


def iso_now() -> str:
    """Return a UTC timestamp in ISO-8601 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stamp() -> str:
    """Return a compact UTC timestamp for filenames and ids."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
