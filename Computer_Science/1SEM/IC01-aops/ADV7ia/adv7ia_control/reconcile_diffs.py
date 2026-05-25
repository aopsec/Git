"""Diff builders for live OpenHands reconciliation."""
from __future__ import annotations

from pathlib import Path

from adv7ia_control.live_state import expand_text
from adv7ia_control.models import ControlPolicy
from adv7ia_control.reconcile_models import LiveRuntime, OpenHandsDesiredState, ReconcileDiff
from adv7ia_control.reconcile_support import (
    blocked_diff,
    parse_openhands_bind,
    recreate_diff,
    render_json,
    resolve_setting_value,
)


def build_security_diffs(
    policy: ControlPolicy,
    desired: OpenHandsDesiredState,
) -> list[ReconcileDiff]:
    """Reject desired states that violate the repo security policy."""
    diffs: list[ReconcileDiff] = []
    allowed_binding = parse_openhands_bind(policy.security_policy.openhands_bind)
    desired_bindings = [
        binding.model_dump(mode="json") for binding in desired.container_spec.published_ports
    ]
    if allowed_binding is None:
        diffs.append(
            blocked_diff(
                "openhands_bind",
                policy.security_policy.openhands_bind,
                "<host_ip>:<host_port>:<container_port>",
                "security policy bind is invalid",
            )
        )
        return diffs
    if (
        desired.container_spec.network_mode == "host"
        and not policy.security_policy.allow_host_network
    ):
        diffs.append(
            blocked_diff("network_mode", "host", "bridge", "host networking is forbidden")
        )
    if desired.container_spec.privileged and not policy.security_policy.allow_privileged:
        diffs.append(
            blocked_diff("privileged", "true", "false", "privileged containers are forbidden")
        )
    expected_bindings = [allowed_binding.model_dump(mode="json")]
    if desired_bindings != expected_bindings:
        diffs.append(
            blocked_diff(
                "published_ports",
                render_json(desired_bindings),
                render_json(expected_bindings),
                "OpenHands publish tuple must match security_policy.openhands_bind",
            )
        )
    return diffs


def build_container_diffs(
    root: Path,
    desired: OpenHandsDesiredState,
    live: LiveRuntime,
) -> list[ReconcileDiff]:
    """Compare the live Docker container with the desired container spec."""
    if live.inspection_status == "missing_container":
        return [
            recreate_diff("container_state", "missing", "running", "container is absent or stopped")
        ]
    diffs: list[ReconcileDiff] = []
    if not live.running:
        diffs.append(
            recreate_diff("container_state", "missing", "running", "container is absent or stopped")
        )
    expected_ports = render_json(
        [binding.model_dump(mode="json") for binding in desired.container_spec.published_ports]
    )
    current_ports = render_json(
        [binding.model_dump(mode="json") for binding in live.published_ports]
    )
    if current_ports != expected_ports:
        diffs.append(
            recreate_diff(
                "published_ports",
                current_ports,
                expected_ports,
                "published ports changed",
            )
        )
    for key, value in sorted(desired.container_spec.required_env.items()):
        desired_value = expand_text(value, root)
        current_value = live.env.get(key, "<missing>")
        if current_value != desired_value:
            diffs.append(
                recreate_diff(f"env.{key}", current_value, desired_value, "container env changed")
            )
    if live.image != desired.container_spec.image:
        diffs.append(
            recreate_diff(
                "image",
                live.image or "<missing>",
                desired.container_spec.image,
                "image drift",
            )
        )
    if live.restart_policy != desired.container_spec.restart_policy:
        diffs.append(
            recreate_diff(
                "restart_policy",
                live.restart_policy or "<missing>",
                desired.container_spec.restart_policy,
                "restart policy changed",
            )
        )
    if live.network_mode != desired.container_spec.network_mode:
        diffs.append(
            recreate_diff(
                "network_mode",
                live.network_mode or "<missing>",
                desired.container_spec.network_mode,
                "network mode changed",
            )
        )
    if live.privileged != desired.container_spec.privileged:
        diffs.append(
            recreate_diff(
                "privileged",
                str(live.privileged).lower(),
                str(desired.container_spec.privileged).lower(),
                "privilege mode changed",
            )
        )
    if live.command != desired.container_spec.command:
        diffs.append(
            recreate_diff(
                "command",
                render_json(live.command),
                render_json(desired.container_spec.command),
                "container command changed",
            )
        )
    for mount in desired.container_spec.required_mounts:
        desired_mount = expand_text(mount, root)
        if desired_mount not in live.mounts:
            diffs.append(
                recreate_diff(
                    f"mount.{desired_mount}",
                    "<missing>",
                    desired_mount,
                    "required bind mount missing",
                )
            )
    for item in desired.container_spec.required_extra_hosts:
        if item not in live.extra_hosts:
            diffs.append(
                recreate_diff(
                    f"extra_host.{item}",
                    "<missing>",
                    item,
                    "required extra host missing",
                )
            )
    for item in desired.container_spec.required_security_opt:
        if item not in live.security_opt:
            diffs.append(
                recreate_diff(
                    f"security_opt.{item}",
                    "<missing>",
                    item,
                    "security option missing",
                )
            )
    return diffs


def build_settings_diffs(desired: OpenHandsDesiredState, live: LiveRuntime) -> list[ReconcileDiff]:
    """Compare the managed persisted OpenHands settings."""
    diffs: list[ReconcileDiff] = []
    for key, spec in sorted(desired.openhands_settings.managed_settings.items()):
        desired_value, blocked = resolve_setting_value(spec)
        if blocked is not None:
            diffs.append(
                blocked_diff(f"setting.{key}", "<unresolved>", blocked, "managed env var missing")
            )
            continue
        current_value = live.settings.get(key, "<missing>")
        if current_value != desired_value:
            diffs.append(
                ReconcileDiff(
                    scope="openhands_settings",
                    key=f"setting.{key}",
                    classification="live_patchable",
                    current=render_json(current_value),
                    desired=render_json(desired_value),
                    reason="persisted setting drift",
                )
            )
    return diffs
