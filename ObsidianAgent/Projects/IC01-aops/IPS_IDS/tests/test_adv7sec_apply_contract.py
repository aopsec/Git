"""Contract tests for install/apply safety semantics."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from adv7sec_1_0.backends import build_backend_plan
from adv7sec_1_0.cli import main
from adv7sec_1_0.executor import execute_operation_plan
from adv7sec_1_0.install import build_install_report
from adv7sec_1_0.models import InstallOperation, RuntimeTarget

_ARCH_TARGET = RuntimeTarget(
    distro_id="arch",
    distro_name="Arch Linux",
    package_manager="pacman",
    init_system="systemd",
    support_tier="native",
    kernel_release="6.12.0-test",
)


class Adv7SecApplyContractTests(unittest.TestCase):
    """[FIX-APPLY-CONTRACT] Cover package coverage and live-apply safety gates."""

    def _run_cli(self, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(list(args))
        return exit_code, buffer.getvalue()

    def test_aide_plan_includes_package_operation(self) -> None:
        report = build_install_report(_ARCH_TARGET, "aide", Path("/tmp/adv7sec-test"), False, False)
        package_ops = [operation for operation in report.operations if operation.kind == "package"]
        self.assertEqual(len(package_ops), 1)
        self.assertEqual(
            package_ops[0].command,
            ["pacman", "-S", "--needed", "--noconfirm", "aide"],
        )

    def test_backend_plan_sets_noninteractive_pacman(self) -> None:
        backend = build_backend_plan(_ARCH_TARGET)
        unbound = next(action for action in backend.package_actions if action.feature == "unbound")
        self.assertIn("--noconfirm", unbound.command)

    def test_live_apply_requires_yes(self) -> None:
        with patch("adv7sec_1_0.cli.detect_runtime_target", return_value=_ARCH_TARGET), patch(
            "adv7sec_1_0.install.os.geteuid",
            return_value=0,
        ):
            exit_code, output = self._run_cli(
                "install",
                "--feature",
                "unbound",
                "--root",
                "/",
                "--apply",
            )
        self.assertEqual(exit_code, 1)
        self.assertIn("requires --yes", output)

    def test_validation_failure_skips_service_enable(self) -> None:
        operations = [
            InstallOperation(
                kind="validate",
                feature="unbound",
                summary="Validate unbound runtime",
                command=["unbound-checkconf"],
            ),
            InstallOperation(
                kind="service",
                feature="unbound",
                summary="Enable service unbound.service",
                command=["systemctl", "enable", "--now", "unbound.service"],
            ),
        ]

        def fake_runner(command: list[str], environment: dict[str, str]) -> int:
            del environment
            return 1 if command == ["unbound-checkconf"] else 0

        results = execute_operation_plan(
            operations,
            present=lambda _command: True,
            runner=fake_runner,
        )
        self.assertEqual(results[0].status, "failed")
        self.assertEqual(results[1].status, "skipped")


if __name__ == "__main__":
    unittest.main()
