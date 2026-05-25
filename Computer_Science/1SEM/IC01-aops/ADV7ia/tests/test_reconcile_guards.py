"""Unit tests for reconcile safety guards."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from adv7ia_control.reconcile import apply_reconcile, build_reconcile_plan


class ReconcileGuardTests(unittest.TestCase):
    """Validate inspection and bind-policy guard behavior."""

    def test_unavailable_inspection_blocks_apply_and_preserves_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            settings_path = self._seed_root(root)
            plan = build_reconcile_plan(
                root,
                command_runner=self._failing_runner("permission denied"),
            )
            diff_kinds = {(diff.classification, diff.key) for diff in plan.diffs}
            self.assertFalse(plan.can_apply)
            self.assertIn(("blocked", "docker_inspection"), diff_kinds)
            with self.assertRaises(ValueError):
                apply_reconcile(root, command_runner=self._failing_runner("permission denied"))
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["llm_model"], "legacy")

    def test_missing_container_remains_recreate_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root)
            plan = build_reconcile_plan(
                root,
                command_runner=self._failing_runner("Error: No such object: openhands-app"),
            )
            diff_kinds = {(diff.classification, diff.key) for diff in plan.diffs}
            self.assertTrue(plan.can_apply)
            self.assertIn(("recreate_required", "container_state"), diff_kinds)

    def test_bind_mismatch_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(
                root,
                published_ports=[
                    {"host_ip": "127.0.0.1", "host_port": 4000, "container_port": 3000}
                ],
            )
            plan = build_reconcile_plan(root, command_runner=self._fake_runner())
            diff_kinds = {(diff.classification, diff.key) for diff in plan.diffs}
            self.assertFalse(plan.can_apply)
            self.assertIn(("blocked", "published_ports"), diff_kinds)

    def _seed_root(
        self,
        root: Path,
        published_ports: list[dict[str, object]] | None = None,
    ) -> Path:
        (root / ".aops-vault.toml").write_text("version = 1\n", encoding="utf-8")
        (root / "state" / "policy").mkdir(parents=True, exist_ok=True)
        settings_path = root / "tmp-openhands" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(settings_path, {"llm_model": "legacy", "v1_enabled": False})
        self._write_json(
            root / "state" / "policy" / "control-mesh.json",
            {
                "policy_name": "demo",
                "security_policy": {
                    "gated_actions": ["network"],
                    "openhands_bind": "127.0.0.1:3000:3000",
                },
            },
        )
        self._write_json(
            root / "state" / "policy" / "openhands-reconcile.json",
            {
                "container_spec": {
                    "container_name": "openhands-app",
                    "service_name": "openhands-app",
                    "compose_file": "deploy/openhands/compose.yaml",
                    "image": "docker.openhands.dev/openhands/openhands:1.6",
                    "restart_policy": "unless-stopped",
                    "network_mode": "bridge",
                    "privileged": False,
                    "published_ports": published_ports
                    or [{"host_ip": "127.0.0.1", "host_port": 3000, "container_port": 3000}],
                    "required_env": {"SANDBOX_RUNTIME_BINDING_ADDRESS": "127.0.0.1"},
                    "required_mounts": [],
                    "required_extra_hosts": [],
                    "required_security_opt": [],
                    "command": [
                        "uvicorn",
                        "openhands.server.listen:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "3000",
                    ],
                },
                "openhands_settings": {
                    "settings_file": str(settings_path),
                    "apply_mode": "file",
                    "managed_settings": {
                        "llm_model": {"mode": "literal", "value": "lm_studio/qwen3-coder-local"}
                    },
                },
                "cutover_policy": {"allow_recreate": True, "require_proxy": True},
            },
        )
        return settings_path

    def _fake_runner(self) -> Callable[[list[str]], str]:
        return lambda args: json.dumps(
            [
                {
                    "Config": {
                        "Image": "docker.openhands.dev/openhands/openhands:1.6",
                        "Env": [],
                        "Cmd": [
                            "uvicorn",
                            "openhands.server.listen:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "3000",
                        ],
                    },
                    "HostConfig": {
                        "RestartPolicy": {"Name": "unless-stopped"},
                        "NetworkMode": "bridge",
                        "Privileged": False,
                        "SecurityOpt": [],
                        "Binds": [],
                        "PortBindings": {"3000/tcp": [{"HostIp": "", "HostPort": "3000"}]},
                    },
                    "State": {"Status": "running"},
                }
            ]
        ) if args[:2] == ["docker", "inspect"] else ""

    def _failing_runner(self, detail: str) -> Callable[[list[str]], str]:
        def run(args: list[str]) -> str:
            if args[:2] == ["docker", "inspect"]:
                raise subprocess.CalledProcessError(returncode=1, cmd=args, stderr=detail)
            raise AssertionError(f"Unexpected command: {args}")

        return run

    def _write_json(self, path: Path, payload: object) -> None:
        path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
