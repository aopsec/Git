"""Safe response action planner."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from adv7sec_1_0.models import ActionName, AutoResponseDecision, ResponsePlan


def build_response_plan(action: ActionName, target: str, execute: bool) -> ResponsePlan:
    """[FIX-LIVE-PIPELINE] Build a safe response plan and optionally execute it."""
    command_map = {
        "stop-service": ["systemctl", "stop", target],
        "disable-service": ["systemctl", "disable", "--now", target],
        "kill-pid": ["kill", "-TERM", target],
        "quarantine-path": ["mv", target, f"/var/lib/adv7sec/quarantine/{Path(target).name}"],
    }
    plan = ResponsePlan(action=action, target=target, execute=execute, command=command_map[action])
    if not execute:
        return plan
    if os.geteuid() != 0:
        raise RuntimeError("execute response requires sudo/root")
    _execute_response(plan)
    return plan


def build_response_from_decision(decision: AutoResponseDecision) -> ResponsePlan:
    """[FIX-LIVE-PIPELINE] Materialize an automatic decision into an executable plan."""
    return build_response_plan(decision.action, decision.target, decision.execute)


def _execute_response(plan: ResponsePlan) -> None:
    command = plan.command
    if plan.action in {"stop-service", "disable-service"} and shutil.which("systemctl") is None:
        raise RuntimeError("systemctl not found for service response")
    if plan.action == "quarantine-path":
        target = Path(plan.target)
        if not target.exists():
            raise RuntimeError(f"target path missing: {plan.target}")
        quarantine_dir = Path("/var/lib/adv7sec/quarantine")
        quarantine_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
