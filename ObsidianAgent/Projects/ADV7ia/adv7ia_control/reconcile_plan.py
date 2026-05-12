"""Reconcile planning helpers for live OpenHands drift."""
from __future__ import annotations

import os
from pathlib import Path

from adv7ia_control.live_state import CommandRunner, inspect_live_runtime
from adv7ia_control.reconcile_diffs import (
    build_container_diffs,
    build_security_diffs,
    build_settings_diffs,
)
from adv7ia_control.reconcile_models import ReconcilePlan
from adv7ia_control.reconcile_support import (
    blocked_diff,
    llm_drift_keys,
    resolve_settings_apply_mode,
)
from adv7ia_control.store import load_policy, load_reconcile_state


def build_reconcile_plan(root: Path, command_runner: CommandRunner | None = None) -> ReconcilePlan:
    """Compare the live runtime with the desired OpenHands state."""
    policy = load_policy(root)
    desired = load_reconcile_state(root)
    live = inspect_live_runtime(root, desired, command_runner=command_runner)
    plan = ReconcilePlan(
        desired=desired,
        live=live,
        warnings=list(live.notes),
        settings_apply_mode=resolve_settings_apply_mode(desired),
    )
    plan.diffs.extend(build_security_diffs(policy, desired))
    if live.inspection_status == "unavailable":
        plan.diffs.append(
            blocked_diff(
                "docker_inspection",
                live.inspection_status,
                "ok",
                "docker inspection must succeed before apply-safe reconcile",
            )
        )
        plan.warnings.append(
            "Docker inspection is unavailable; reconcile apply is disabled to avoid "
            "partial settings-only changes."
        )
        plan.actions.append("restore docker inspect access before applying reconcile")
        plan.compliant = False
        plan.can_apply = False
        return plan
    plan.diffs.extend(build_container_diffs(root, desired, live))
    plan.diffs.extend(build_settings_diffs(desired, live))
    if desired.cutover_policy.restart_conversations_on_llm_change and llm_drift_keys(plan):
        plan.warnings.append(
            "LLM setting changes apply to new conversations; restart older threads."
        )
    if any(diff.classification == "blocked" for diff in plan.diffs):
        plan.compliant = False
        plan.can_apply = False
    if any(diff.classification == "recreate_required" for diff in plan.diffs):
        if desired.cutover_policy.allow_recreate:
            plan.actions.append(
                "docker compose -f "
                f"{desired.container_spec.compose_file} up -d --force-recreate --wait "
                f"{desired.container_spec.service_name}"
            )
        else:
            plan.warnings.append("Container drift exists but cutover policy disabled recreate.")
            plan.can_apply = False
    if any(diff.classification == "live_patchable" for diff in plan.diffs):
        api_url = os.environ.get("ADV7IA_OPENHANDS_SETTINGS_API_URL")
        if plan.settings_apply_mode == "api" and not api_url:
            plan.warnings.append(
                "API settings mode requested but ADV7IA_OPENHANDS_SETTINGS_API_URL is unset."
            )
            plan.can_apply = False
        else:
            plan.actions.append(
                f"patch persisted settings via {plan.settings_apply_mode} at {live.settings_file}"
            )
    if not plan.actions:
        plan.actions.append("no drift detected")
    return plan
