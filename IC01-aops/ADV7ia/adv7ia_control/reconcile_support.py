"""Shared helper functions for live OpenHands reconciliation."""
from __future__ import annotations

import json
import os

from adv7ia_control.reconcile_models import (
    ApplyMode,
    JsonValue,
    ManagedSetting,
    OpenHandsDesiredState,
    PortBinding,
    ReconcileDiff,
    ReconcilePlan,
)


def resolve_desired_settings(settings: dict[str, ManagedSetting]) -> dict[str, JsonValue]:
    """Resolve managed settings into concrete values."""
    resolved: dict[str, JsonValue] = {}
    for key, spec in settings.items():
        value, blocked = resolve_setting_value(spec)
        if blocked is None:
            resolved[key] = value
    return resolved


def resolve_setting_value(setting: ManagedSetting) -> tuple[JsonValue, str | None]:
    """Resolve one managed setting."""
    if setting.mode == "literal":
        return setting.value, None
    if setting.env_var and setting.env_var in os.environ:
        return os.environ[setting.env_var], None
    if setting.default is not None:
        return setting.default, None
    return "", f"env:{setting.env_var or '<unset>'}"


def resolve_settings_apply_mode(desired: OpenHandsDesiredState) -> ApplyMode:
    """Choose the settings apply mode."""
    if desired.openhands_settings.apply_mode != "auto":
        return desired.openhands_settings.apply_mode
    return "api" if os.environ.get("ADV7IA_OPENHANDS_SETTINGS_API_URL") else "file"


def blocked_diff(key: str, current: str, desired: str, reason: str) -> ReconcileDiff:
    """Create one blocked security diff."""
    return ReconcileDiff(
        scope="security_policy",
        key=key,
        classification="blocked",
        current=current,
        desired=desired,
        reason=reason,
    )


def recreate_diff(key: str, current: str, desired: str, reason: str) -> ReconcileDiff:
    """Create one recreate-required diff."""
    return ReconcileDiff(
        scope="container_spec",
        key=key,
        classification="recreate_required",
        current=current,
        desired=desired,
        reason=reason,
    )


def llm_drift_keys(plan: ReconcilePlan) -> list[str]:
    """Return the LLM-related setting keys that drifted."""
    return [diff.key for diff in plan.diffs if diff.key.startswith("setting.llm_")]


def render_json(value: object) -> str:
    """Render one value for human-readable diffs."""
    return json.dumps(value, sort_keys=True)


def parse_openhands_bind(value: str) -> PortBinding | None:
    """Parse one `host_ip:host_port:container_port` tuple."""
    try:
        host_ip, host_port_text, container_port_text = value.rsplit(":", maxsplit=2)
        if not host_ip:
            return None
        return PortBinding(
            host_ip=host_ip,
            host_port=int(host_port_text),
            container_port=int(container_port_text),
        )
    except ValueError:
        return None
