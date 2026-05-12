"""Core control-mesh operations for ADV7ia."""
from __future__ import annotations

from pathlib import Path

from adv7ia_control.models import (
    CheckpointPhase,
    CheckpointRecord,
    GateDecision,
    MeshStatus,
    SessionRecord,
)
from adv7ia_control.render import render_compaction_note
from adv7ia_control.session_alerts import evaluate_session_alerts
from adv7ia_control.store import (
    ensure_runtime_layout,
    load_policy,
    load_sessions,
    load_tasks,
    write_checkpoint,
    write_note,
    write_session,
    write_task,
)
from adv7ia_control.util import dedupe, dedupe_gates, iso_now, stamp


def build_mesh_status(root: Path) -> MeshStatus:
    """Build a current snapshot of the control mesh."""
    ensure_runtime_layout(root)
    policy = load_policy(root)
    tasks = load_tasks(root)
    sessions = load_sessions(root)
    active_tasks = [
        task for task in tasks.values() if task.status in {"queued", "active", "blocked"}
    ]
    active_sessions = [
        session for session in sessions.values() if session.status in {"active", "compact_pending"}
    ]
    alerts: list[str] = []
    pending_gates: list[GateDecision] = []
    for session in active_sessions:
        alerts.extend(
            evaluate_session_alerts(
                session,
                policy.token_policy.warning_ratio,
                policy.token_policy.freeze_ratio,
                policy.token_policy.compact_ratio,
            )
        )
    for task in active_tasks:
        if task.branch_depth >= policy.security_policy.max_recursion_depth:
            alerts.append(
                f"task `{task.task_id}` reached recursion depth {task.branch_depth}; "
                "no automatic requeue allowed."
            )
        if task.retry_count > policy.security_policy.max_retry_count:
            alerts.append(
                f"task `{task.task_id}` exceeded retry cap "
                f"{policy.security_policy.max_retry_count}."
            )
        for action in task.risky_actions:
            pending_gates.append(gate_action(action, root))
    return MeshStatus(
        root=str(root),
        policy=policy,
        active_tasks=active_tasks,
        active_sessions=active_sessions,
        alerts=dedupe(alerts),
        pending_gates=dedupe_gates(pending_gates),
    )


def gate_action(action: str, root: Path) -> GateDecision:
    """Resolve whether one action requires a manual gate."""
    policy = load_policy(root)
    requires = action in policy.security_policy.gated_actions
    reason = (
        "manual approval required by security policy"
        if requires
        else "action allowed inside the current policy"
    )
    return GateDecision(action=action, requires_approval=requires, reason=reason)


def create_checkpoint(
    root: Path,
    task_id: str,
    session_id: str,
    phase: CheckpointPhase,
    summary: str,
    decisions: list[str],
    artifacts: list[str],
    blockers: list[str],
    next_actions: list[str],
) -> CheckpointRecord:
    """Create one checkpoint and update the related task and session."""
    ensure_runtime_layout(root)
    tasks = load_tasks(root)
    sessions = load_sessions(root)
    task = tasks[task_id]
    session = sessions[session_id]
    checkpoint = CheckpointRecord(
        checkpoint_id=f"checkpoint-{stamp()}",
        task_id=task_id,
        session_id=session_id,
        phase=phase,
        summary=summary,
        decisions=decisions,
        artifacts=artifacts,
        blockers=blockers,
        next_actions=next_actions,
        created_at=iso_now(),
    )
    task.last_checkpoint_id = checkpoint.checkpoint_id
    task.next_actions = next_actions
    session.checkpoint_ids.append(checkpoint.checkpoint_id)
    session.next_actions = next_actions
    compact_ratio = load_policy(root).token_policy.compact_ratio
    if session.prompt_tokens >= int(session.context_window * compact_ratio):
        session.status = "compact_pending"
    write_task(root, task)
    write_session(root, session)
    write_checkpoint(root, checkpoint)
    return checkpoint


def compact_session(
    root: Path,
    session_id: str,
    summary: str,
    decisions: list[str],
    artifacts: list[str],
    blockers: list[str],
    next_actions: list[str],
    force: bool = False,
) -> tuple[CheckpointRecord, SessionRecord]:
    """Compact one session into a fresh session and an Obsidian note."""
    ensure_runtime_layout(root)
    policy = load_policy(root)
    tasks = load_tasks(root)
    sessions = load_sessions(root)
    session = sessions[session_id]
    task = tasks[session.task_id]
    compact_floor = int(session.context_window * policy.token_policy.compact_ratio)
    if not force and session.prompt_tokens < compact_floor:
        raise ValueError(
            f"Session `{session_id}` is below the compact threshold `{compact_floor}`."
        )
    checkpoint = create_checkpoint(
        root=root,
        task_id=task.task_id,
        session_id=session.session_id,
        phase="compact",
        summary=summary,
        decisions=decisions,
        artifacts=artifacts,
        blockers=blockers,
        next_actions=next_actions,
    )
    session.status = "rolled"
    session.last_compacted_at = checkpoint.created_at
    new_session = SessionRecord(
        session_id=f"{session.session_id}-roll-{stamp()}",
        task_id=task.task_id,
        status="active",
        current_role="session_manager",
        model=session.model,
        prompt_tokens=max(1024, int(session.context_window * 0.2)),
        context_window=session.context_window,
        compaction_count=session.compaction_count + 1,
        checkpoint_ids=[checkpoint.checkpoint_id],
        next_actions=next_actions,
        opened_at=checkpoint.created_at,
        parent_session_id=session.session_id,
        last_compacted_at=checkpoint.created_at,
    )
    note_path = root / "vault" / "Operations" / "Compactions" / f"{new_session.session_id}.md"
    write_note(note_path, render_compaction_note(checkpoint, session, new_session))
    new_session.summary_note = str(note_path.relative_to(root))
    task.current_session_id = new_session.session_id
    task.last_checkpoint_id = checkpoint.checkpoint_id
    task.next_actions = next_actions
    write_session(root, session)
    write_session(root, new_session)
    write_task(root, task)
    return checkpoint, new_session
