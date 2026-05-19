"""Tests for the v0.5.9 form-select scan wizard (``bbwebscan.menu_form``)."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from bbwebscan import menu as menu_mod
from bbwebscan import menu_form
from bbwebscan.menu_collect import prompt_multiselect, prompt_select
from bbwebscan.menu_types import InputFunc
from bbwebscan.models import RunConfig


def _input(values: Iterable[str]) -> InputFunc:
    iterator = iter(values)

    def fake_input(_prompt: str) -> str:
        return next(iterator)

    return fake_input


# ---- prompt_select ----


def test_prompt_select_returns_default_on_empty(capsys: pytest.CaptureFixture[str]) -> None:
    result = prompt_select(
        "Pick mode", ["safe", "aggressive"], default=1, input_func=_input([""]),
    )
    assert result == "safe"
    captured = capsys.readouterr().out
    assert "Pick mode" in captured
    assert "[1] safe" in captured


def test_prompt_select_returns_chosen_option() -> None:
    result = prompt_select(
        "Pick mode", ["safe", "aggressive"], default=1, input_func=_input(["2"]),
    )
    assert result == "aggressive"


def test_prompt_select_reprompts_on_non_numeric(capsys: pytest.CaptureFixture[str]) -> None:
    result = prompt_select(
        "Pick", ["a", "b", "c"], default=1, input_func=_input(["x", "2"]),
    )
    assert result == "b"
    captured = capsys.readouterr().out
    assert "Invalid choice" in captured


def test_prompt_select_reprompts_on_out_of_range(capsys: pytest.CaptureFixture[str]) -> None:
    result = prompt_select(
        "Pick", ["a", "b"], default=2, input_func=_input(["99", "1"]),
    )
    assert result == "a"
    captured = capsys.readouterr().out
    assert "Out of range" in captured


def test_prompt_select_empty_options_raises() -> None:
    with pytest.raises(ValueError, match="at least one option"):
        prompt_select("Empty", [], input_func=_input([]))


def test_prompt_select_invalid_default_raises() -> None:
    with pytest.raises(ValueError, match="default must be"):
        prompt_select("Pick", ["a", "b"], default=5, input_func=_input([]))


# ---- prompt_multiselect ----


def test_prompt_multiselect_comma_separated() -> None:
    result = prompt_multiselect(
        "Tools", ["a", "b", "c", "d"], default_all=False, input_func=_input(["1,3"]),
    )
    assert result == ["a", "c"]


def test_prompt_multiselect_all_alias() -> None:
    result = prompt_multiselect(
        "Tools", ["a", "b", "c"], default_all=False, input_func=_input(["a"]),
    )
    assert result == ["a", "b", "c"]


def test_prompt_multiselect_none_alias() -> None:
    result = prompt_multiselect(
        "Tools", ["a", "b"], default_all=True, input_func=_input(["n"]),
    )
    assert result == []


def test_prompt_multiselect_empty_returns_default() -> None:
    # default_all=True => empty returns all
    result_all = prompt_multiselect(
        "Tools", ["a", "b"], default_all=True, input_func=_input([""]),
    )
    assert result_all == ["a", "b"]
    # default_all=False => empty returns []
    result_none = prompt_multiselect(
        "Tools", ["a", "b"], default_all=False, input_func=_input([""]),
    )
    assert result_none == []


def test_prompt_multiselect_dedup_preserves_first_occurrence() -> None:
    result = prompt_multiselect(
        "Tools",
        ["a", "b", "c"],
        default_all=False,
        input_func=_input(["1,2,1"]),
    )
    assert result == ["a", "b"]


def test_prompt_multiselect_invalid_reprompts(capsys: pytest.CaptureFixture[str]) -> None:
    result = prompt_multiselect(
        "Tools",
        ["a", "b", "c"],
        default_all=False,
        input_func=_input(["bogus", "99", "2"]),
    )
    assert result == ["b"]
    captured = capsys.readouterr().out
    assert "Invalid input" in captured
    assert "Out of range" in captured


def test_prompt_multiselect_empty_options_returns_empty() -> None:
    assert prompt_multiselect(
        "Empty", [], default_all=False, input_func=_input([]),
    ) == []


# ---- run_form_scan ----


def _isolated_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Move CWD to a profile-less temp dir so the wizard sees no saved profiles."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_run_form_scan_cancel_when_target_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _isolated_cwd(monkeypatch, tmp_path)
    rc = menu_form.run_form_scan(input_func=_input([""]))
    assert rc is None


def test_run_form_scan_minimal_safe_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _isolated_cwd(monkeypatch, tmp_path)
    # No profiles dir => only "None" is offered (single option).
    inputs = [
        "example.com",   # target URL
        "1",             # profile choice: None
        "1",             # scan mode: safe
        "n",             # tools multi-select: none
        "1",             # sqlmap mode: off
        "1",             # scrapy extended: no
        "1",             # wordlist: first preset
    ]
    config = menu_form.run_form_scan(input_func=_input(inputs))
    assert isinstance(config, RunConfig)
    assert config.mode == "safe"
    assert config.sqlmap_mode == "off"
    assert config.scrapy_extended is False
    assert config.ack_authorized is False
    assert str(config.wordlist) == "/usr/share/dirb/wordlists/common.txt"
    assert "example.com" in config.target_inputs


def test_run_form_scan_aggressive_sqlmap_triggers_ack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _isolated_cwd(monkeypatch, tmp_path)
    inputs = [
        "example.com",   # target URL
        "1",             # profile: None
        "1",             # scan mode: safe (so we only get the sqlmap ack prompt)
        "n",             # tools: none
        "3",             # sqlmap mode: aggressive (triggers ack)
        "1",             # scrapy extended: no
        "1",             # wordlist: first preset
        "AUTHORIZED",    # ack from collect_authorization_ack(aggressive)
    ]
    config = menu_form.run_form_scan(input_func=_input(inputs))
    assert isinstance(config, RunConfig)
    assert config.sqlmap_mode == "aggressive"
    assert config.ack_authorized is True


def test_run_form_scan_scrapy_extended_yes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _isolated_cwd(monkeypatch, tmp_path)
    inputs = [
        "example.com", "1", "1", "n", "1",
        "2",   # scrapy extended: yes
        "1",   # wordlist preset 1
    ]
    config = menu_form.run_form_scan(input_func=_input(inputs))
    assert isinstance(config, RunConfig)
    assert config.scrapy_extended is True


def test_run_form_scan_custom_wordlist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _isolated_cwd(monkeypatch, tmp_path)
    custom = str(tmp_path / "my-wordlist.txt")
    inputs = [
        "example.com", "1", "1", "n", "1", "1",
        "3",       # wordlist: Custom
        custom,    # custom wordlist path
    ]
    config = menu_form.run_form_scan(input_func=_input(inputs))
    assert isinstance(config, RunConfig)
    assert str(config.wordlist) == custom


def test_run_form_scan_profile_preselects_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    profile_path = profiles_dir / "demo.yaml"
    profile_path.write_text(
        "allowed_hosts:\n- example.com\n"
        "enabled_tools:\n- sqlmap\n- amass\n"
        "sqlmap_mode: smooth\nscrapy_extended: true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    inputs = [
        "example.com",   # target
        "1",             # profile: demo (first option)
        "1",             # mode: safe
        "n",             # tools: none (profile pre-selection kicks in)
        "1",             # sqlmap mode: off (CLI overrides nothing; profile still wins)
        "1",             # scrapy extended: no (CLI override)
        "1",             # wordlist
    ]
    config = menu_form.run_form_scan(input_func=_input(inputs))
    assert isinstance(config, RunConfig)
    # Profile's sqlmap_mode applies when CLI/wizard picks "off" -> "off" wins
    # because the resolution is `cli_sqlmap_mode or profile.sqlmap_mode`, and
    # wizard always supplies an explicit value. So the wizard's "off" stays.
    assert config.sqlmap_mode == "off"
    # tools pre-selected from profile (sqlmap, amass) intersected with OPTIONAL_TOOLS
    assert "sqlmap" in config.enabled_tools
    assert "amass" in config.enabled_tools


def test_main_menu_dispatch_form_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """[v0.5.9] Verify Form Scan is wired into the 7-item main menu at slot 3."""
    calls: list[str] = []

    def fake_form(input_func: Any = None) -> None:
        del input_func
        calls.append("form")

    monkeypatch.setattr(menu_mod, "run_form_scan", fake_form)
    inputs = iter(["3", "7"])  # Pick Form Scan, then Exit
    rc = menu_mod.run_menu(input_func=lambda _: next(inputs), io=_NullIO())
    assert rc == 0
    assert calls == ["form"]


class _NullIO:
    def print(self, message: str = "") -> None:
        del message

    def panel(self, title: str, body: str) -> None:
        del title, body

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        del title, columns, rows
