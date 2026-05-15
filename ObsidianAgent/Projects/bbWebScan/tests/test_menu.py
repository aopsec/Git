from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
import yaml

from bbwebscan import __version__
from bbwebscan.config import build_run_config
from bbwebscan.menu import run_menu
from bbwebscan.menu_command import build_scan_command, scan_settings_to_args
from bbwebscan.menu_profile import ProfileSaveOptions, save_profile
from bbwebscan.menu_scan import collect_scan_settings, run_scan_action_menu
from bbwebscan.menu_types import InputFunc, ScanSettings
from bbwebscan.models import RunConfig


class FakeIO:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.panels: list[tuple[str, str]] = []
        self.tables: list[tuple[str, list[list[str]]]] = []

    def print(self, message: str = "") -> None:
        self.messages.append(message)

    def panel(self, title: str, body: str) -> None:
        self.panels.append((title, body))

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        del columns
        self.tables.append((title, rows))


def _input(values: Iterable[str]) -> InputFunc:
    iterator = iter(values)

    def fake_input(_prompt: str) -> str:
        return next(iterator)

    return fake_input


def test_main_menu_exits_cleanly() -> None:
    io = FakeIO()
    assert run_menu(input_func=_input(["8"]), io=io) == 0
    assert io.panels[0][0] == f"bbWebScan v{__version__}"


def test_scan_wizard_builds_run_config() -> None:
    # [v0.5.3] Wizard now prompts for scrapy_deep / scrapy_max_depth / scrapy_js_render
    # between api_discovery and dry_run. Defaults preserved via empty strings.
    # [v0.5.5] sqlmap_mode prompted after enumerate_subdomains; jwt_analysis +
    # sqlmap_timeout prompted between scrapy_js_render and dry_run.
    # [v0.5.6] port_scan prompted between sqlmap_timeout and dry_run; mode/rate
    # prompts only fire if port_scan is "y".
    settings = collect_scan_settings(input_func=_input([
        "", "example.com", "", "", "", "", "", "n",
        "",                              # sqlmap_mode (default "off")
        "n",                             # port_scan (v0.5.6, default "n")
        "n", "n", "", "", "",
        "5", "10", "", "", "", "", "medium", "y", "n",
        "n", "", "n",                    # scrapy_deep, scrapy_max_depth, scrapy_js_render
        "n", "",                         # jwt_analysis, sqlmap_timeout
        "y", "n", "n",
    ]))
    config = build_run_config(scan_settings_to_args(settings, run_label="test"))
    assert config.target_inputs == ["example.com"]
    assert config.threads == 5
    assert config.rate == 10
    assert config.min_severity == "medium"
    assert config.preflight_dns is True
    assert config.dry_run is True


def test_aggressive_wizard_settings_still_require_authorization() -> None:
    settings = ScanSettings(targets=["example.com"], mode="aggressive", ack_authorized=False)
    with pytest.raises(ValueError, match="ack-authorized"):
        build_run_config(scan_settings_to_args(settings, run_label="test"))


@pytest.mark.parametrize(("choice", "expected_dry_run"), [("2", True), ("3", False)])
def test_action_menu_runs_scan_with_expected_dry_run(
    choice: str,
    expected_dry_run: bool,
) -> None:
    io = FakeIO()
    seen: list[bool] = []

    def fake_scan(config: RunConfig) -> int:
        seen.append(config.dry_run)
        return 0

    settings = ScanSettings(targets=["example.com"])
    rc = run_scan_action_menu(settings, io, input_func=_input([choice]), scan_executor=fake_scan)
    assert rc == 0
    assert seen == [expected_dry_run]


def test_action_menu_preview_redacts_one_off_auth() -> None:
    io = FakeIO()
    settings = ScanSettings(
        targets=["example.com"],
        headers=["Authorization: Bearer secret-token"],
        cookies=["session=secret-cookie"],
    )
    rc = run_scan_action_menu(settings, io, input_func=_input(["1", "6"]))
    assert rc == 0
    preview = io.messages[0]
    assert "secret-token" not in preview
    assert "secret-cookie" not in preview
    assert "Authorization: <redacted>" in preview
    assert "session=<redacted>" in preview


def test_build_scan_command_preserves_smart_scan_flags() -> None:
    settings = ScanSettings(
        targets=["example.com"],
        enable_tool=["nuclei"],
        enumerate_subdomains=True,
        amass_mode="passive",
        api_discovery=True,
    )
    command = build_scan_command(settings, dry_run_override=True)
    assert "--target example.com" in command
    assert "--enable-tool nuclei" in command
    assert "--enumerate-subdomains" in command
    assert "--api-discovery" in command
    assert "--dry-run" in command


def test_profile_save_uses_env_refs_not_plaintext(tmp_path: Path) -> None:
    out = tmp_path / "profiles" / "demo.yaml"
    settings = ScanSettings(
        targets=["example.com"],
        headers=["Authorization: Bearer plaintext-secret"],
        cookies=["session=plaintext-cookie"],
    )
    save_profile(
        settings,
        out,
        options=ProfileSaveOptions(
            program_name="demo",
            profile_headers={"Authorization": "Bearer ${BBW_TOKEN}"},
            profile_cookies={"session": "${BBW_SESSION}"},
        ),
    )
    body = out.read_text(encoding="utf-8")
    assert "plaintext-secret" not in body
    assert "plaintext-cookie" not in body
    payload = yaml.safe_load(body)
    assert payload["auth"]["headers"]["Authorization"] == "Bearer ${BBW_TOKEN}"
    assert payload["auth"]["cookies"]["session"] == "${BBW_SESSION}"


def test_profile_save_does_not_persist_raw_request_path(tmp_path: Path) -> None:
    out = tmp_path / "profiles" / "demo.yaml"
    save_profile(
        ScanSettings(targets=["example.com"], raw_request="request.txt"),
        out,
        options=ProfileSaveOptions(
            program_name="demo",
            profile_headers={"Authorization": "Bearer ${BBW_TOKEN}"},
            profile_cookies={"session": "${BBW_SESSION}"},
        ),
    )
    body = out.read_text(encoding="utf-8")
    assert "request.txt" not in body
    payload = yaml.safe_load(body)
    assert payload["auth"]["raw_request"] is None


def test_profile_save_rejects_plaintext_saved_auth(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="env-var references"):
        save_profile(
            ScanSettings(targets=["example.com"]),
            tmp_path / "demo.yaml",
            options=ProfileSaveOptions(profile_headers={"Authorization": "Bearer secret"}),
        )


def test_action_menu_save_profile_then_back(tmp_path: Path) -> None:
    out = tmp_path / "demo.yaml"
    io = FakeIO()
    rc = run_scan_action_menu(
        ScanSettings(targets=["example.com"]),
        io,
        input_func=_input([
            "4", "demo", str(out), "n",
            "y", "Authorization", "Bearer ${BBW_TOKEN}", "n",
            "y", "session", "${BBW_SESSION}", "n",
            "6",
        ]),
    )
    assert rc == 0
    assert out.is_file()
    assert "wrote" in io.messages[-1]


def test_action_menu_preview_and_args_keep_one_off_raw_request() -> None:
    io = FakeIO()
    settings = ScanSettings(targets=["example.com"], raw_request="request.txt")
    command = build_scan_command(settings, dry_run_override=True, redact_auth=False)
    assert "--raw-request request.txt" in command
    rc = run_scan_action_menu(settings, io, input_func=_input(["1", "6"]))
    assert rc == 0
    assert "--raw-request request.txt" in io.messages[0]


def test_action_menu_edit_invokes_wizard(monkeypatch: pytest.MonkeyPatch) -> None:
    io = FakeIO()
    edited = ScanSettings(targets=["edited.example.com"])
    calls: list[ScanSettings] = []

    def fake_collect(existing: ScanSettings | None = None, **_kwargs: object) -> ScanSettings:
        assert existing is not None
        calls.append(existing)
        return edited

    monkeypatch.setattr("bbwebscan.menu_scan.collect_scan_settings", fake_collect)
    rc = run_scan_action_menu(
        ScanSettings(targets=["example.com"]),
        io,
        input_func=_input(["5", "6"]),
    )
    assert rc == 0
    assert calls
