"""Unit tests for live OpenHands reconcile planning."""
from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from adv7ia_control.reconcile import apply_reconcile, build_reconcile_plan


class ReconcileTests(unittest.TestCase):
    """Validate live settings and Docker drift handling."""

    def test_reconcile_plan_classifies_settings_and_container_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root)
            settings_path = root / "tmp-openhands" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_json(
                settings_path,
                {
                    "llm_model": "wrong-model",
                    "llm_base_url": "http://127.0.0.1:9999/v1",
                    "v1_enabled": False,
                },
            )
            self._seed_reconcile_policy(root, settings_path)
            plan = build_reconcile_plan(root, command_runner=self._fake_runner())
            diff_kinds = {(diff.classification, diff.key) for diff in plan.diffs}
            self.assertIn(("live_patchable", "setting.llm_model"), diff_kinds)
            self.assertIn(("recreate_required", "published_ports"), diff_kinds)
            self.assertTrue(plan.can_apply)

    def test_apply_reconcile_updates_settings_and_runs_compose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            self._seed_root(root)
            settings_path = root / "tmp-openhands" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_json(settings_path, {"llm_model": "legacy", "v1_enabled": False})
            self._seed_reconcile_policy(root, settings_path)
            commands: list[list[str]] = []
            apply_reconcile(root, command_runner=self._fake_runner(commands))
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["llm_model"], "lm_studio/qwen3-coder-local")
            self.assertTrue(any(command[:3] == ["docker", "compose", "-f"] for command in commands))

    def _seed_root(self, root: Path) -> None:
        (root / ".aops-vault.toml").write_text("version = 1\n", encoding="utf-8")
        (root / "state" / "policy").mkdir(parents=True, exist_ok=True)
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

    def _seed_reconcile_policy(
        self,
        root: Path,
        settings_path: Path,
        published_ports: list[dict[str, object]] | None = None,
    ) -> None:
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
                    "required_env": {
                        "SANDBOX_USER_ID": "1000",
                        "SANDBOX_RUNTIME_BINDING_ADDRESS": "127.0.0.1",
                        "USE_HOST_NETWORK": "false",
                        "SANDBOX_VOLUMES": "${ADV7IA_ROOT}:/workspace/adv7ia:rw",
                    },
                    "required_mounts": [
                        "${HOME}/.openhands:/.openhands",
                        "${HOME}/.openhands:/home/openhands/.openhands",
                        "${HOME}/.openhands:/root/.openhands",
                        "/var/run/docker.sock:/var/run/docker.sock",
                    ],
                    "required_extra_hosts": ["host.docker.internal:host-gateway"],
                    "required_security_opt": ["no-new-privileges:true"],
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
                        "llm_model": {"mode": "literal", "value": "lm_studio/qwen3-coder-local"},
                        "llm_base_url": {
                            "mode": "literal",
                            "value": "http://host.docker.internal:1234/v1",
                        },
                        "v1_enabled": {"mode": "literal", "value": True},
                    },
                },
                "cutover_policy": {"allow_recreate": True, "require_proxy": True},
            },
        )

    def _fake_runner(self, commands: list[list[str]] | None = None) -> Callable[[list[str]], str]:
        def run(args: list[str]) -> str:
            if commands is not None:
                commands.append(args)
            if args[:2] == ["docker", "inspect"]:
                return json.dumps(
                    [
                        {
                            "Config": {
                                "Image": "docker.openhands.dev/openhands/openhands:1.6",
                                "Env": [
                                    "SANDBOX_USER_ID=1000",
                                    "SANDBOX_RUNTIME_BINDING_ADDRESS=127.0.0.1",
                                    "USE_HOST_NETWORK=false",
                                    "SANDBOX_VOLUMES=/tmp/legacy:/workspace:rw",
                                ],
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
                                "SecurityOpt": ["no-new-privileges:true"],
                                "Binds": [
                                    f"{Path.home() / '.openhands'}:/.openhands",
                                    f"{Path.home() / '.openhands'}:/home/openhands/.openhands",
                                    f"{Path.home() / '.openhands'}:/root/.openhands",
                                    "/var/run/docker.sock:/var/run/docker.sock",
                                ],
                                "ExtraHosts": ["host.docker.internal:host-gateway"],
                                "PortBindings": {
                                    "3000/tcp": [{"HostIp": "", "HostPort": "3000"}]
                                },
                            },
                            "State": {"Status": "running"},
                        }
                    ]
                )
            if args[:3] == ["docker", "compose", "-f"]:
                return ""
            raise AssertionError(f"Unexpected command: {args}")

        return run

    def _write_json(self, path: Path, payload: object) -> None:
        path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
