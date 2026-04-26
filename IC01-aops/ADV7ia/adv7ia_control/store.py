"""Filesystem helpers for the ADV7ia control mesh."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from adv7ia_control.models import CheckpointRecord, ControlPolicy, SessionRecord, TaskRecord
from adv7ia_control.reconcile_models import OpenHandsDesiredState

ROOT_MARKER = ".aops-vault.toml"


def discover_root(start: Path) -> Path:
    """Resolve the project root from any descendant path."""
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / ROOT_MARKER).is_file():
            return candidate
    raise FileNotFoundError(f"Could not find `{ROOT_MARKER}` from `{start}`.")


def ensure_runtime_layout(root: Path) -> None:
    """Create the runtime state directories when they are absent."""
    # [FIX-ADV7IA-CM-01] Keep controller state and compactions outside generated vault output.
    for path in (
        root / "state" / "tasks",
        root / "state" / "sessions",
        root / "state" / "checkpoints",
        root / "state" / "policy",
        root / "vault" / "Operations" / "Compactions",
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_policy(root: Path) -> ControlPolicy:
    """Load the repo-local control policy."""
    policy_path = root / "state" / "policy" / "control-mesh.json"
    return load_model(policy_path, ControlPolicy)


def load_tasks(root: Path) -> dict[str, TaskRecord]:
    """Load task records keyed by task id."""
    return load_records(root / "state" / "tasks", TaskRecord, "task_id")


def load_reconcile_state(root: Path) -> OpenHandsDesiredState:
    """Load the desired state for live OpenHands reconciliation."""
    path = root / "state" / "policy" / "openhands-reconcile.json"
    return load_model(path, OpenHandsDesiredState)


def load_sessions(root: Path) -> dict[str, SessionRecord]:
    """Load session records keyed by session id."""
    return load_records(root / "state" / "sessions", SessionRecord, "session_id")


def load_checkpoints(root: Path) -> dict[str, CheckpointRecord]:
    """Load checkpoint records keyed by checkpoint id."""
    return load_records(root / "state" / "checkpoints", CheckpointRecord, "checkpoint_id")


def load_model[ModelT: BaseModel](path: Path, model_cls: type[ModelT]) -> ModelT:
    """Load one JSON document into a typed model."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return model_cls.model_validate(data)


def load_records[ModelT: BaseModel](
    directory: Path,
    model_cls: type[ModelT],
    key_name: str,
) -> dict[str, ModelT]:
    """Load every JSON record in one state directory."""
    records: dict[str, ModelT] = {}
    if not directory.is_dir():
        return records
    for path in sorted(directory.glob("*.json")):
        record = load_model(path, model_cls)
        records[str(getattr(record, key_name))] = record
    return records


def write_task(root: Path, task: TaskRecord) -> Path:
    """Persist one task record."""
    path = root / "state" / "tasks" / f"{task.task_id}.json"
    return write_model(path, task)


def write_session(root: Path, session: SessionRecord) -> Path:
    """Persist one session record."""
    path = root / "state" / "sessions" / f"{session.session_id}.json"
    return write_model(path, session)


def write_checkpoint(root: Path, checkpoint: CheckpointRecord) -> Path:
    """Persist one checkpoint record."""
    path = root / "state" / "checkpoints" / f"{checkpoint.checkpoint_id}.json"
    return write_model(path, checkpoint)


def write_note(path: Path, content: str) -> Path:
    """Write a markdown note with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.rstrip()}\n", encoding="utf-8")
    return path


def write_model(path: Path, model: BaseModel) -> Path:
    """Write one Pydantic model as stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = model.model_dump_json(indent=2)
    path.write_text(f"{rendered}\n", encoding="utf-8")
    return path
