"""CLI tests for ADV7Sec 1.0."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from adv7sec_1_0.cli import main
from adv7sec_1_0.models import AnalysisReport, Capability, MonitorRecord, RuntimeTarget, ThreatEvent


class Adv7SecCliTests(unittest.TestCase):
    """[FIX-CLI-TESTS] Cover the unified CLI surface, not only legacy helpers."""

    def _run_cli(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(list(args))
        return exit_code, buffer.getvalue()

    def test_audit_json_emits_current_state(self) -> None:
        exit_code, output = self._run_cli("audit", "--format", "json")
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, [])

    def test_doctor_json_is_deterministic_when_probed(self) -> None:
        target = RuntimeTarget(
            distro_id="ubuntu",
            distro_name="Ubuntu 26.04",
            package_manager="apt",
            init_system="systemd",
            support_tier="adapted",
            kernel_release="6.12.0-test",
        )
        capabilities = [
            Capability(name="systemctl", available=True, detail="/usr/bin/systemctl"),
            Capability(name="btf", available=False, detail="missing"),
        ]
        with patch("adv7sec_1_0.cli.detect_runtime_target", return_value=target), patch(
            "adv7sec_1_0.cli.probe_capabilities",
            return_value=capabilities,
        ):
            exit_code, output = self._run_cli("doctor", "--format", "json")
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["target"]["package_manager"], "apt")
        self.assertEqual(len(payload["capabilities"]), 2)
        self.assertEqual(payload["backend"]["package_manager"], "apt")

    def test_backend_json_exposes_cross_distro_packages(self) -> None:
        target = RuntimeTarget(
            distro_id="fedora",
            distro_name="Fedora 42",
            package_manager="dnf",
            init_system="systemd",
            support_tier="adapted",
            kernel_release="6.12.0-test",
        )
        with patch("adv7sec_1_0.cli.detect_runtime_target", return_value=target):
            exit_code, output = self._run_cli("backend", "--format", "json")
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["package_manager"], "dnf")
        self.assertTrue(any(item["feature"] == "suricata" for item in payload["package_actions"]))

    def test_monitor_text_uses_snapshot_records(self) -> None:
        records = [
            MonitorRecord(
                source="journal:falco-modern-bpf.service",
                status="ok",
                summary="event-1",
            ),
            MonitorRecord(source="/var/log/suricata/eve.json", status="warn", summary="empty"),
        ]
        with patch("adv7sec_1_0.cli.snapshot_monitor", return_value=records):
            exit_code, output = self._run_cli("monitor", "--lines", "3")
        self.assertEqual(exit_code, 0)
        self.assertIn("[ok] journal:falco-modern-bpf.service", output)
        self.assertIn("[warn] /var/log/suricata/eve.json", output)

    def test_resources_export_materializes_packaged_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            exit_code, output = self._run_cli("resources", "--export-dir", str(destination))
            exported_file = destination / "etc/aide/aide.conf"
            self.assertEqual(exit_code, 0)
            self.assertTrue(exported_file.is_file())
            self.assertIn("exported_to=", output)

    def test_respond_preview_outputs_command(self) -> None:
        exit_code, output = self._run_cli("respond", "stop-service", "suricata.service")
        self.assertEqual(exit_code, 0)
        self.assertIn("command=systemctl stop suricata.service", output)

    def test_analyze_json_reports_safe_response_candidates(self) -> None:
        event = ThreatEvent(
            source="/var/log/clamav/clamonacc.log",
            channel="file",
            severity="critical",
            summary="/tmp/evil.bin: Win.Test FOUND",
            raw="/tmp/evil.bin: Win.Test FOUND",
            path="/tmp/evil.bin",
        )
        report = AnalysisReport(
            total_events=1,
            elevated_events=1,
            signals=["1 eventos elevados detectados na amostra atual."],
            events=[event],
            responses=[],
        )
        with patch("adv7sec_1_0.cli.collect_live_events", return_value=[event]), patch(
            "adv7sec_1_0.cli.analyze_events",
            return_value=report,
        ):
            exit_code, output = self._run_cli("analyze", "--format", "json")
        payload = json.loads(output)
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["total_events"], 1)
        self.assertEqual(payload["events"][0]["path"], "/tmp/evil.bin")

if __name__ == "__main__":
    unittest.main()
