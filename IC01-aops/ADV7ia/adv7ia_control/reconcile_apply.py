"""Apply helpers for live OpenHands reconcile plans."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from adv7ia_control.live_state import CommandRunner, run_command
from adv7ia_control.reconcile_models import ApplyMode, ApplyResult, JsonValue, ReconcilePlan
from adv7ia_control.reconcile_plan import build_reconcile_plan
from adv7ia_control.reconcile_support import resolve_desired_settings


def apply_reconcile(root: Path, command_runner: CommandRunner | None = None) -> ApplyResult:
    """Apply the planned OpenHands reconcile steps."""
    plan = build_reconcile_plan(root, command_runner=command_runner)
    if not plan.can_apply:
        raise ValueError("Reconcile plan is blocked; inspect `reconcile --plan` before applying.")
    runner = command_runner or run_command
    desired_settings = resolve_desired_settings(plan.desired.openhands_settings.managed_settings)
    executed_steps: list[str] = []
    notes: list[str] = []
    if any(diff.classification == "live_patchable" for diff in plan.diffs):
        applied_mode = apply_settings(plan, desired_settings)
        executed_steps.append(f"patched settings via {applied_mode}")
        if applied_mode == "file":
            notes.append(
                "Persisted settings were updated locally; older OpenHands threads may need restart."
            )
    if any(diff.classification == "recreate_required" for diff in plan.diffs):
        compose_path = root / plan.desired.container_spec.compose_file
        runner(
            [
                "docker",
                "compose",
                "-f",
                str(compose_path),
                "up",
                "-d",
                "--force-recreate",
                "--wait",
                plan.desired.container_spec.service_name,
            ]
        )
        executed_steps.append(f"recreated service `{plan.desired.container_spec.service_name}`")
    if not executed_steps:
        executed_steps.append("no changes required")
    return ApplyResult(plan=plan, executed_steps=executed_steps, notes=notes)


def apply_settings(plan: ReconcilePlan, desired_settings: dict[str, JsonValue]) -> ApplyMode:
    """Apply the managed persisted settings."""
    if plan.settings_apply_mode == "api":
        try:
            push_settings_api(desired_settings)
            return "api"
        except (OSError, urllib.error.HTTPError, urllib.error.URLError):
            if plan.desired.openhands_settings.apply_mode != "auto":
                raise
    settings_path = Path(plan.live.settings_file)
    payload = plan.live.settings | desired_settings
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return "file"


def push_settings_api(payload: dict[str, JsonValue]) -> None:
    """Send the settings payload to the OpenHands settings API."""
    url = os.environ["ADV7IA_OPENHANDS_SETTINGS_API_URL"]
    headers = {"Content-Type": "application/json"}
    if token := os.environ.get("ADV7IA_OPENHANDS_SETTINGS_API_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    if session_key := os.environ.get("ADV7IA_OPENHANDS_SESSION_API_KEY"):
        headers["X-Session-API-Key"] = session_key
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30):
        return None
