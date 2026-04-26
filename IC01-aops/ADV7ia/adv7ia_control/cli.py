"""CLI for the ADV7ia control mesh."""
from __future__ import annotations

import argparse
from pathlib import Path

from adv7ia_control.reconcile import apply_reconcile, build_reconcile_plan
from adv7ia_control.render import (
    render_apply_result,
    render_brief,
    render_reconcile_plan,
    render_status,
)
from adv7ia_control.service import (
    build_mesh_status,
    compact_session,
    create_checkpoint,
    gate_action,
)
from adv7ia_control.store import discover_root


def build_parser() -> argparse.ArgumentParser:
    """Create the controller CLI parser."""
    parser = argparse.ArgumentParser(description="ADV7ia control-mesh helpers")
    parser.add_argument("--root", default=".", help="Project root or descendant path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Render the full control-mesh status")
    subparsers.add_parser("brief", help="Render a short control-mesh brief")

    gate_parser = subparsers.add_parser("gate", help="Check whether an action is gated")
    gate_parser.add_argument("action", help="Action name to evaluate")

    checkpoint_parser = subparsers.add_parser("checkpoint", help="Create a checkpoint")
    checkpoint_parser.add_argument("--task-id", required=True)
    checkpoint_parser.add_argument("--session-id", required=True)
    checkpoint_parser.add_argument(
        "--phase",
        required=True,
        choices=["intake", "plan", "execute", "verify", "summarize", "compact", "close"],
    )
    checkpoint_parser.add_argument("--summary", required=True)
    checkpoint_parser.add_argument("--decision", action="append", default=[])
    checkpoint_parser.add_argument("--artifact", action="append", default=[])
    checkpoint_parser.add_argument("--blocker", action="append", default=[])
    checkpoint_parser.add_argument("--next-action", action="append", default=[])

    compact_parser = subparsers.add_parser("compact", help="Compact a session into a new one")
    compact_parser.add_argument("--session-id", required=True)
    compact_parser.add_argument(
        "--summary",
        default="Automatic session rollover triggered by the 95% token threshold.",
    )
    compact_parser.add_argument("--decision", action="append", default=[])
    compact_parser.add_argument("--artifact", action="append", default=[])
    compact_parser.add_argument("--blocker", action="append", default=[])
    compact_parser.add_argument("--next-action", action="append", default=[])
    compact_parser.add_argument("--force", action="store_true")

    reconcile_parser = subparsers.add_parser(
        "reconcile",
        help="Plan or apply live OpenHands reconfiguration against the desired state",
    )
    reconcile_mode = reconcile_parser.add_mutually_exclusive_group()
    reconcile_mode.add_argument("--plan", action="store_true", help="Render the reconcile plan")
    reconcile_mode.add_argument("--apply", action="store_true", help="Apply the reconcile plan")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the control-mesh CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    root = discover_root(Path(args.root))

    if args.command == "status":
        print(render_status(build_mesh_status(root)))
        return 0
    if args.command == "brief":
        print(render_brief(build_mesh_status(root)))
        return 0
    if args.command == "gate":
        gate = gate_action(args.action, root)
        print(
            f"action={gate.action} requires_approval={str(gate.requires_approval).lower()} "
            f"reason={gate.reason}"
        )
        return 0
    if args.command == "checkpoint":
        checkpoint = create_checkpoint(
            root=root,
            task_id=args.task_id,
            session_id=args.session_id,
            phase=args.phase,
            summary=args.summary,
            decisions=list(args.decision),
            artifacts=list(args.artifact),
            blockers=list(args.blocker),
            next_actions=list(args.next_action),
        )
        print(f"checkpoint={checkpoint.checkpoint_id} created_at={checkpoint.created_at}")
        return 0
    if args.command == "compact":
        checkpoint, session = compact_session(
            root=root,
            session_id=args.session_id,
            summary=args.summary,
            decisions=list(args.decision),
            artifacts=list(args.artifact),
            blockers=list(args.blocker),
            next_actions=list(args.next_action),
            force=bool(args.force),
        )
        print(f"checkpoint={checkpoint.checkpoint_id} new_session={session.session_id}")
        if session.summary_note:
            print(f"summary_note={session.summary_note}")
        return 0
    if args.command == "reconcile":
        if args.apply:
            print(render_apply_result(apply_reconcile(root)))
            return 0
        print(render_reconcile_plan(build_reconcile_plan(root)))
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
