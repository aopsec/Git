"""Unit tests for the ADV7ia control mesh."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adv7ia_control.service import build_mesh_status, compact_session


class ControlMeshTests(unittest.TestCase):
    """Validate the recursive control-mesh behavior."""

    def test_status_reports_token_pressure_and_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root, prompt_tokens=31400)
            status = build_mesh_status(root)
            self.assertTrue(status.alerts)
            self.assertEqual(status.pending_gates[0].action, "network")
            self.assertTrue(status.pending_gates[0].requires_approval)

    def test_compact_session_rolls_and_writes_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root, prompt_tokens=32000)
            checkpoint, new_session = compact_session(
                root=root,
                session_id="session-demo",
                summary="Compact the demo session.",
                decisions=["Preserve localhost-only OpenHands."],
                artifacts=["deploy/caddy/Caddyfile"],
                blockers=[],
                next_actions=["Requeue the proxy verification."],
                force=False,
            )
            self.assertEqual(checkpoint.phase, "compact")
            note_path = (
                root
                / "vault"
                / "Operations"
                / "Compactions"
                / f"{new_session.session_id}.md"
            )
            self.assertTrue(note_path.is_file())
            self.assertEqual(new_session.parent_session_id, "session-demo")

    def test_status_uses_configured_warning_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root, prompt_tokens=18022, warning_ratio=0.5, freeze_ratio=0.75)
            status = build_mesh_status(root)
            self.assertIn("50%", status.alerts[0])

    def test_status_uses_configured_freeze_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root, prompt_tokens=19661, warning_ratio=0.4, freeze_ratio=0.55)
            status = build_mesh_status(root)
            self.assertIn("55%", status.alerts[0])
            self.assertIn("stop opening new branches", status.alerts[0])

    def _seed_root(
        self,
        root: Path,
        prompt_tokens: int,
        warning_ratio: float = 0.8,
        freeze_ratio: float = 0.9,
        compact_ratio: float = 0.95,
    ) -> None:
        (root / ".aops-vault.toml").write_text("version = 1\n", encoding="utf-8")
        for path in (
            root / "state" / "policy",
            root / "state" / "tasks",
            root / "state" / "sessions",
            root / "state" / "checkpoints",
            root / "vault" / "Operations" / "Compactions",
        ):
            path.mkdir(parents=True, exist_ok=True)
        self._write_json(
            root / "state" / "policy" / "control-mesh.json",
            {
                "policy_name": "demo",
                "token_policy": {
                    "warning_ratio": warning_ratio,
                    "freeze_ratio": freeze_ratio,
                    "compact_ratio": compact_ratio,
                },
                "security_policy": {"gated_actions": ["network"]},
                "roles": [{"name": "planner", "description": "demo", "enabled": True}],
            },
        )
        self._write_json(
            root / "state" / "tasks" / "task-demo.json",
            {
                "task_id": "task-demo",
                "title": "demo",
                "objective": "demo objective",
                "status": "active",
                "current_session_id": "session-demo",
                "risky_actions": ["network"],
            },
        )
        self._write_json(
            root / "state" / "sessions" / "session-demo.json",
            {
                "session_id": "session-demo",
                "task_id": "task-demo",
                "status": "active",
                "current_role": "planner",
                "model": "demo-model",
                "prompt_tokens": prompt_tokens,
                "context_window": 32768,
                "compaction_count": 0,
                "checkpoint_ids": ["checkpoint-demo"],
                "next_actions": ["compact"],
                "opened_at": "2026-04-25T00:00:00+00:00",
                "parent_session_id": None,
                "last_compacted_at": None,
                "summary_note": None,
            },
        )
        self._write_json(
            root / "state" / "checkpoints" / "checkpoint-demo.json",
            {
                "checkpoint_id": "checkpoint-demo",
                "task_id": "task-demo",
                "session_id": "session-demo",
                "phase": "intake",
                "summary": "demo",
                "decisions": [],
                "artifacts": [],
                "blockers": [],
                "next_actions": ["compact"],
                "created_at": "2026-04-25T00:00:00+00:00",
            },
        )

    def _write_json(self, path: Path, payload: object) -> None:
        path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
