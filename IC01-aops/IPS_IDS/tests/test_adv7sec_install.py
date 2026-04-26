"""Install and smoke tests for ADV7Sec 1.0."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from adv7sec_1_0.cli import main
from adv7sec_1_0.models import RuntimeTarget


class Adv7SecInstallTests(unittest.TestCase):
    """[FIX-CLI-TESTS] Cover unified install/apply and smoke behavior."""

    def _run_cli(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(list(args))
        return exit_code, buffer.getvalue()

    def test_install_apply_exports_selected_feature_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            exit_code, output = self._run_cli(
                "install",
                "--feature",
                "suricata",
                "--root",
                str(destination),
                "--apply",
            )
            exported_file = destination / "etc/suricata/eve-minimal.yaml"
            generated_file = destination / "etc/default/ipsids-suricata"
            runtime_dir = destination / "var/log/suricata"
            unrelated_file = destination / "etc/aide/aide.conf"
            self.assertEqual(exit_code, 0)
            self.assertTrue(exported_file.is_file())
            self.assertTrue(generated_file.is_file())
            self.assertTrue(runtime_dir.is_dir())
            self.assertFalse(unrelated_file.exists())
            self.assertIn("features=suricata", output)

    def test_install_apply_generates_clamav_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            exit_code, _output = self._run_cli(
                "install",
                "--feature",
                "clamav",
                "--root",
                str(destination),
                "--apply",
            )
            scope_file = destination / "etc/clamav/clamd.d/99-openbox-scope.conf"
            override_file = (
                destination / "etc/systemd/system/clamav-clamonacc.service.d/override.conf"
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(scope_file.is_file())
            self.assertTrue(override_file.is_file())

    def test_install_apply_maps_aide_conf_to_final_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            exit_code, _output = self._run_cli(
                "install",
                "--feature",
                "aide",
                "--root",
                str(destination),
                "--apply",
            )
            final_conf = destination / "etc/aide.conf"
            source_like_path = destination / "etc/aide/aide.conf"
            self.assertEqual(exit_code, 0)
            self.assertTrue(final_conf.is_file())
            self.assertFalse(source_like_path.exists())

    def test_smoke_json_reports_missing_and_present_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            target = destination / "etc/audit/rules.d/50-persistence.rules"
            suricata = destination / "etc/default/ipsids-suricata"
            target.parent.mkdir(parents=True, exist_ok=True)
            suricata.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# ok\n", encoding="utf-8")
            suricata.write_text('SURICATA_INTERFACES="eth0"\n', encoding="utf-8")
            exit_code, output = self._run_cli(
                "smoke",
                "--root",
                str(destination),
                "--format",
                "json",
            )
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertTrue(
            any(
                item["source"] == "smoke:auditd" and item["status"] == "ok"
                for item in payload
            )
        )
        self.assertTrue(
            any(
                item["source"] == "smoke:suricata"
                and "ipsids-suricata" in item["summary"]
                and item["status"] == "ok"
                for item in payload
            )
        )

    def test_real_apply_executes_package_service_and_validation_commands(self) -> None:
        commands: list[list[str]] = []
        target = RuntimeTarget(
            distro_id="arch",
            distro_name="Arch Linux",
            package_manager="pacman",
            init_system="systemd",
            support_tier="native",
            kernel_release="6.12.0-test",
        )

        def fake_runner(
            args: list[str],
            environment: dict[str, str],
        ) -> int:
            commands.append(args)
            self.assertEqual(environment, {})
            return 0

        with patch("adv7sec_1_0.cli.detect_runtime_target", return_value=target), patch(
            "adv7sec_1_0.install.os.geteuid",
            return_value=0,
        ), patch(
            "adv7sec_1_0.executor.os.geteuid",
            return_value=0,
        ), patch(
            "adv7sec_1_0.install.export_resource_map",
            return_value=[],
        ), patch(
            "adv7sec_1_0.install.write_generated_artifacts",
            return_value=[],
        ), patch(
            "adv7sec_1_0.install.create_runtime_directories",
            return_value=[],
        ), patch(
            "adv7sec_1_0.executor.shutil.which",
            return_value="/usr/bin/fake",
        ), patch(
            "adv7sec_1_0.executor._run_returncode",
            side_effect=fake_runner,
        ):
            exit_code, output = self._run_cli(
                "install",
                "--feature",
                "unbound",
                "--root",
                "/",
                "--apply",
                "--yes",
            )
        self.assertEqual(exit_code, 0)
        self.assertIn(["pacman", "-S", "--needed", "--noconfirm", "unbound"], commands)
        self.assertIn(["systemctl", "daemon-reload"], commands)
        self.assertIn(["systemctl", "enable", "--now", "unbound.service"], commands)
        self.assertIn(["unbound-checkconf"], commands)
        self.assertIn("= ok:service:unbound rc=0 daemon reload completed", output)


if __name__ == "__main__":
    unittest.main()
