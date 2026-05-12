from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from bbwebscan.menu_actions import run_doctor_auto_fix
from bbwebscan.menu_types import InputFunc
from bbwebscan.models import ToolStatus


class FakeIO:
    def print(self, message: str = "") -> None:
        del message

    def panel(self, title: str, body: str) -> None:
        del title, body

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        del title, columns, rows


def _input(values: Iterable[str]) -> InputFunc:
    iterator = iter(values)

    def fake_input(_prompt: str) -> str:
        return next(iterator)

    return fake_input


def _fixable_statuses() -> list[ToolStatus]:
    return [
        ToolStatus(
            name="httpx",
            required=True,
            found=False,
            path=Path("/home/aops/go/bin/httpx"),
            path_gap=Path("/home/aops/go/bin/httpx"),
        ),
        ToolStatus(name="katana", required=True, found=False),
    ]


def test_doctor_auto_fix_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bbwebscan.menu_actions.inventory_tools",
        lambda _tools: _fixable_statuses(),
    )
    called: list[str] = []

    def fake_runner(_args: object) -> int:
        called.append("called")
        return 0

    rc = run_doctor_auto_fix(
        FakeIO(),
        input_func=_input(["n"]),
        doctor_runner=fake_runner,
        installer_runner=fake_runner,
    )
    assert rc == 2
    assert called == []


def test_doctor_auto_fix_runs_existing_helpers_after_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bbwebscan.menu_actions.inventory_tools",
        lambda _tools: _fixable_statuses(),
    )
    called: list[str] = []

    def fake_doctor(_args: object) -> int:
        called.append("doctor")
        return 0

    def fake_installer(_args: object) -> int:
        called.append("installer")
        return 0

    rc = run_doctor_auto_fix(
        FakeIO(),
        input_func=_input(["y"]),
        doctor_runner=fake_doctor,
        installer_runner=fake_installer,
    )
    assert rc == 0
    assert called == ["doctor", "installer"]
