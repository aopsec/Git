"""Rendering helpers for control-mesh state and notes."""
from __future__ import annotations

from adv7ia_control.models import CheckpointRecord, MeshStatus, SessionRecord
from adv7ia_control.reconcile_models import ApplyResult, ReconcilePlan


def render_status(status: MeshStatus) -> str:
    """Render the full control-mesh status report."""
    lines: list[str] = []
    lines.append("ADV7ia Control Mesh")
    lines.append(f"root: {status.root}")
    lines.append(f"policy: {status.policy.policy_name}")
    lines.append(f"openhands_local: {status.policy.endpoints.openhands_local_url}")
    lines.append(f"openhands_proxy: {status.policy.endpoints.openhands_proxy_url}")
    lines.append(f"active_tasks: {len(status.active_tasks)}")
    lines.append(f"active_sessions: {len(status.active_sessions)}")
    lines.append("roles:")
    for role in status.policy.roles:
        state = "enabled" if role.enabled else "disabled"
        lines.append(f"  - {role.name}: {state} | {role.description}")
    lines.append("alerts:")
    if status.alerts:
        for alert in status.alerts:
            lines.append(f"  - {alert}")
    else:
        lines.append("  - none")
    lines.append("pending_gates:")
    if status.pending_gates:
        for gate in status.pending_gates:
            lines.append(f"  - {gate.action}: {gate.reason}")
    else:
        lines.append("  - none")
    lines.append("sessions:")
    for session in status.active_sessions:
        lines.append(
            f"  - {session.session_id}: {session.status} | "
            f"{session.prompt_tokens}/{session.context_window} tokens | role={session.current_role}"
        )
    return "\n".join(lines)


def render_brief(status: MeshStatus) -> str:
    """Render a compact human-facing brief."""
    alerts = ", ".join(status.alerts) if status.alerts else "no active alerts"
    alerts = alerts.rstrip(".")
    return (
        f"ADV7ia control mesh: {len(status.active_tasks)} task(s), "
        f"{len(status.active_sessions)} active session(s), {alerts}."
    )


def render_compaction_note(
    checkpoint: CheckpointRecord,
    previous_session: SessionRecord,
    new_session: SessionRecord,
) -> str:
    """Render the Obsidian note for a rolled session."""
    lines = [
        "---",
        "type: control-compaction",
        f"task_id: {checkpoint.task_id}",
        f"session_id: {new_session.session_id}",
        f"previous_session_id: {previous_session.session_id}",
        "---",
        "",
        f"# Session Compaction - {new_session.session_id}",
        "",
        f"Phase: `{checkpoint.phase}`",
        f"Created: `{checkpoint.created_at}`",
        "",
        "## Summary",
        checkpoint.summary,
        "",
        "## Decisions",
    ]
    lines.extend(f"- {item}" for item in checkpoint.decisions or ["No new decisions recorded."])
    lines.extend(["", "## Artifacts"])
    lines.extend(f"- {item}" for item in checkpoint.artifacts or ["No artifacts recorded."])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in checkpoint.blockers or ["No blockers recorded."])
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in checkpoint.next_actions or ["No next actions recorded."])
    lines.extend(
        [
            "",
            "## Session Chain",
            f"- Previous session: `{previous_session.session_id}`",
            f"- New session: `{new_session.session_id}`",
            f"- Parent session: `{new_session.parent_session_id}`",
        ]
    )
    return "\n".join(lines)


def render_reconcile_plan(plan: ReconcilePlan) -> str:
    """Render the live OpenHands reconcile plan."""
    lines = [
        "ADV7ia OpenHands Reconcile",
        f"container: {plan.live.container_name}",
        f"running: {str(plan.live.running).lower()}",
        f"settings_source: {plan.live.settings_source}",
        f"settings_apply_mode: {plan.settings_apply_mode}",
        f"compliant: {str(plan.compliant).lower()}",
        f"can_apply: {str(plan.can_apply).lower()}",
        "warnings:",
    ]
    lines.extend(f"  - {item}" for item in plan.warnings or ["none"])
    lines.append("diffs:")
    if plan.diffs:
        for diff in plan.diffs:
            lines.append(
                f"  - [{diff.classification}] {diff.scope}.{diff.key}: "
                f"{diff.current} -> {diff.desired} ({diff.reason})"
            )
    else:
        lines.append("  - none")
    lines.append("actions:")
    lines.extend(f"  - {item}" for item in plan.actions or ["none"])
    return "\n".join(lines)


def render_apply_result(result: ApplyResult) -> str:
    """Render the executed reconcile steps."""
    lines = [render_reconcile_plan(result.plan), "executed_steps:"]
    lines.extend(f"  - {item}" for item in result.executed_steps or ["none"])
    lines.append("notes:")
    lines.extend(f"  - {item}" for item in result.notes or ["none"])
    return "\n".join(lines)
