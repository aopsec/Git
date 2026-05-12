from __future__ import annotations

import argparse
from collections.abc import Iterable

import pytest

from bbwebscan import menu as menu_module
from bbwebscan import menu_actions as actions_module
from bbwebscan.menu import RichMenuIO, run_menu
from bbwebscan.menu_actions import (
    doctor_state,
    planned_doctor_fixes,
    run_compare_menu,
    run_init_menu,
    run_install_menu,
    run_show_menu,
)
from bbwebscan.menu_types import InputFunc, ScanSettings
from bbwebscan.models import ToolStatus


class FakeIO:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.panels: list[str] = []
        self.tables: list[str] = []

    def print(self, message: str = "") -> None:
        self.messages.append(message)

    def panel(self, title: str, body: str) -> None:
        del body
        self.panels.append(title)

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        del columns, rows
        self.tables.append(title)


def _input(values: Iterable[str]) -> InputFunc:
    iterator = iter(values)

    def fake_input(_prompt: str) -> str:
        return next(iterator)

    return fake_input


def test_rich_menu_io_plain_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    io = RichMenuIO()
    io.print("msg")
    io.panel("Title", "Body")
    io.table("Rows", ["A"], [["B"]])
    out = capsys.readouterr().out
    assert "msg" in out
    assert "Title" in out
    assert "Rows" in out


def test_menu_invalid_choice_then_exit() -> None:
    io = FakeIO()
    assert run_menu(input_func=_input(["x", "8"]), io=io) == 0
    assert "Choose a number from 1 to 8." in io.messages


def test_menu_routes_history(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()
    called: list[str] = []

    def fake_history() -> int:
        called.append("history")
        return 0

    monkeypatch.setattr("bbwebscan.menu.run_history_menu", fake_history)
    assert run_menu(input_func=_input(["5", "8"]), io=io) == 0
    assert called == ["history"]


def test_menu_scan_value_error_returns_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()

    def boom(**_kwargs: object) -> ScanSettings:
        raise ValueError("bad tool")

    monkeypatch.setattr(menu_module, "collect_scan_settings", boom)
    assert run_menu(input_func=_input(["1", "8"]), io=io) == 0
    assert any("bad tool" in message for message in io.messages)


def test_menu_show_missing_run_returns_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()

    def boom(*, input_func: InputFunc) -> int:
        del input_func
        raise FileNotFoundError("missing summary.md")

    monkeypatch.setattr(menu_module, "run_show_menu", boom)
    assert run_menu(input_func=_input(["6", "8"]), io=io) == 0
    assert any("missing summary.md" in message for message in io.messages)


def test_menu_compare_missing_findings_returns_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()

    def boom(*, input_func: InputFunc) -> int:
        del input_func
        raise FileNotFoundError("missing findings.json")

    monkeypatch.setattr(menu_module, "run_compare_menu", boom)
    assert run_menu(input_func=_input(["7", "8"]), io=io) == 0
    assert any("missing findings.json" in message for message in io.messages)


def test_menu_init_user_error_returns_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()

    def boom(*, input_func: InputFunc) -> int:
        del input_func
        raise OSError("cannot write profile")

    monkeypatch.setattr(menu_module, "run_init_menu", boom)
    assert run_menu(input_func=_input(["4", "8"]), io=io) == 0
    assert any("cannot write profile" in message for message in io.messages)


def test_install_menu_threads_flags() -> None:
    seen: list[argparse.Namespace] = []

    def fake_runner(args: argparse.Namespace) -> int:
        seen.append(args)
        return 0

    assert run_install_menu(input_func=_input(["", "y", ""]), installer_runner=fake_runner) == 0
    args = seen[0]
    assert args.dry_run is True
    assert args.update_nuclei_templates is True
    assert args.quiet is True


def test_init_menu_threads_existing_init_args() -> None:
    seen: list[argparse.Namespace] = []

    def fake_runner(args: argparse.Namespace) -> int:
        seen.append(args)
        return 0

    rc = run_init_menu(
        input_func=_input(["demo", "a.example.com,b.example.com", "", "y"]),
        init_runner=fake_runner,
    )
    assert rc == 0
    assert seen[0].program_name == "demo"
    assert seen[0].target == ["a.example.com", "b.example.com"]
    assert seen[0].force is True


def test_show_and_compare_menus(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_show(args: argparse.Namespace) -> int:
        seen.append(args.run_dir)
        return 0

    def fake_compare(args: argparse.Namespace) -> int:
        seen.append(f"{args.run_a}->{args.run_b}")
        return 0

    monkeypatch.setattr(actions_module, "run_show", fake_show)
    monkeypatch.setattr(actions_module, "run_compare", fake_compare)
    assert run_show_menu(input_func=_input(["runs/a"])) == 0
    assert run_compare_menu(input_func=_input(["runs/a", "runs/b"])) == 0
    assert run_show_menu(input_func=_input([""])) == 0
    assert run_compare_menu(input_func=_input(["", "runs/b"])) == 0
    assert seen == ["runs/a", "runs/a->runs/b"]


def test_doctor_state_and_plans() -> None:
    assert doctor_state(ToolStatus(name="x", required=True, found=True)) == "found"
    assert doctor_state(ToolStatus(name="x", required=True, found=False)) == "missing"
    assert doctor_state(ToolStatus(
        name="x", required=True, found=True, identity="suspect",
    )) == "suspect"
    assert planned_doctor_fixes(True, True) == [
        "bbwebscan doctor --fix-path",
        "bbwebscan install",
    ]
    assert planned_doctor_fixes(False, False) == []
