from __future__ import annotations

import argparse
from collections.abc import Iterable

import pytest

from bbwebscan import menu_actions as actions_module
from bbwebscan.menu import RichMenuIO
from bbwebscan.menu_actions import (
    doctor_state,
    planned_doctor_fixes,
    run_compare_menu,
    run_init_menu,
    run_install_menu,
    run_show_menu,
)
from bbwebscan.menu_types import InputFunc
from bbwebscan.models import ToolStatus


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
