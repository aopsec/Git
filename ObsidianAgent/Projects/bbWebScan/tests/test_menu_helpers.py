from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from bbwebscan.menu_command import build_scan_command
from bbwebscan.menu_prompts import choice, collect_repeatable, prompt_bool, validate_tools
from bbwebscan.menu_scan import collect_scan_settings, run_scan_action_menu
from bbwebscan.menu_types import InputFunc, ScanSettings


class FakeIO:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str = "") -> None:
        self.messages.append(message)

    def panel(self, title: str, body: str) -> None:
        del title, body

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        del title, columns, rows


def _input(values: Iterable[str]) -> InputFunc:
    iterator = iter(values)

    def fake_input(_prompt: str) -> str:
        return next(iterator)

    return fake_input


def test_command_builder_covers_optional_flags() -> None:
    settings = ScanSettings(
        profile="profiles/demo.yaml",
        targets=["example.com"],
        input_file="targets.txt",
        ack_authorized=True,
        headers=["X-Test"],
        cookies=["bad-cookie"],
        raw_request="req.txt",
        output_dir="runs/out",
        wordlist="words.txt",
        disable_tool=["katana"],
        threads=1,
        rate=2,
        tool_timeout=3,
        cmd_timeout=4,
        max_attempts=5,
        backoff_s=0.5,
        severity="high",
        quiet=True,
        strict_identity=True,
        dry_run=False,
    )
    command = build_scan_command(settings, dry_run_override=False, redact_auth=False)
    assert "--profile profiles/demo.yaml" in command
    assert "--disable-tool katana" in command
    assert "--severity high" in command
    assert "--quiet" in command
    assert "--strict-identity" in command
    assert "--dry-run" not in command


def test_prompt_helpers_retry_and_reject() -> None:
    assert choice("Mode", ("safe", "aggressive"), "safe", _input(["bad", "safe"])) == "safe"
    assert prompt_bool("Confirm", False, _input(["maybe", "y"])) is True
    assert collect_repeatable("header", [], _input(["y", "X: y", "n"])) == ["X: y"]
    with pytest.raises(ValueError, match="Unsupported"):
        validate_tools(["wfuzz"])


def test_scan_action_invalid_and_save_error(tmp_path: Path) -> None:
    out = tmp_path / "demo.yaml"
    out.write_text("exists", encoding="utf-8")
    io = FakeIO()
    rc = run_scan_action_menu(
        ScanSettings(targets=["example.com"]),
        io,
        input_func=_input(["x", "4", "demo", str(out), "n", "n", "n"]),
    )
    assert rc == 2
    assert any("Choose a number from 1 to 6." in message for message in io.messages)


def test_scan_wizard_collects_active_amass_ack() -> None:
    settings = collect_scan_settings(input_func=_input([
        "", "example.com", "", "", "", "", "", "y", "active", "AUTHORIZED",
        "n", "n", "", "", "", "", "", "", "", "", "", "", "n", "n", "y", "n", "n",
    ]))
    assert settings.enumerate_subdomains is True
    assert settings.amass_mode == "active"
    assert settings.ack_authorized is True
