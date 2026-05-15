"""[v0.5.6] Coverage-boost tests targeting the gaps surfaced by `verify.sh`.

The 97% gate requires exercising error/edge paths across cli, installer,
welcome, menu, pipeline, bbspider, and a handful of stage modules. Each
test here aims at a single concrete missed-line range from the pytest-cov
``term-missing`` report.
"""
from __future__ import annotations

import argparse
import builtins
import importlib
import importlib.metadata as md
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
from scrapy.http import HtmlResponse, Request, TextResponse

from bbwebscan import __version__
from bbwebscan import cli as cli_mod
from bbwebscan import installer as installer_mod
from bbwebscan import menu as menu_mod
from bbwebscan import pipeline as pipeline_mod
from bbwebscan import welcome as welcome_mod
from bbwebscan.menu import RichMenuIO
from bbwebscan.menu_command import redact_cookie, redact_header, scan_command_args
from bbwebscan.menu_types import ScanSettings
from bbwebscan.models import (
    AuthConfig,
    NormalizedTarget,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
    ToolStatus,
)
from bbwebscan.stages.scrapy import bbspider as bbspider_mod
from bbwebscan.stages.scrapy.bbspider import BbSpider

# ---- __init__.py fallback ----

def test_version_string_is_populated() -> None:
    """The installed version should match pyproject; fallback path tested below."""
    assert __version__
    assert __version__ != "0.0.0+local"


def test_version_fallback_when_package_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reload ``bbwebscan`` with ``importlib.metadata.version`` raising
    ``PackageNotFoundError`` so we hit the editable-before-install fallback."""

    def fake_version(name: str) -> str:
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "version", fake_version)
    monkeypatch.delitem(sys.modules, "bbwebscan", raising=False)
    reloaded = importlib.import_module("bbwebscan")
    assert reloaded.__version__ == "0.0.0+local"
    # Restore the cached version-bearing module so downstream tests see the real one.
    monkeypatch.delitem(sys.modules, "bbwebscan", raising=False)
    importlib.import_module("bbwebscan")


# ---- welcome.py ----

def test_print_welcome_emits_header_and_quick_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    welcome_mod.print_welcome()
    out = capsys.readouterr().out
    assert f"bbWebScan v{__version__}" in out
    assert "Quick commands:" in out
    assert "Toolchain:" in out


def test_build_panel_counts_ready_tools_excluding_suspect() -> None:
    statuses = [
        ToolStatus(name="a", required=True, found=True, identity="verified"),
        ToolStatus(name="b", required=True, found=True, identity="suspect"),
        ToolStatus(name="c", required=True, found=False),
    ]
    panel = welcome_mod.build_panel(statuses)
    assert "1/3 tools ready" in panel


# ---- menu.py — Rich-absent fallback paths ----

def test_richmenuio_falls_back_to_plain_when_rich_imports_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """When ``rich.*`` can't be imported, RichMenuIO must use plain print."""
    real_import = builtins.__import__

    def patched_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("rich"):
            raise ImportError(f"forced: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", patched_import)
    io = RichMenuIO()
    assert io._console is None

    io.print("hello")
    io.panel("title", "body")
    io.table("t", ["c1", "c2"], [["a", "b"]])
    out = capsys.readouterr().out
    assert "hello" in out
    assert "== title ==" in out
    assert "== t ==" in out
    assert "c1 | c2" in out
    assert "a | b" in out


def test_run_menu_prints_invalid_choice_message() -> None:
    """An unrecognised numeric input prompts the user but does not exit."""
    inputs = iter(["99", "8"])

    class _IO:
        def __init__(self) -> None:
            self.messages: list[str] = []
            self.panels: list[tuple[str, str]] = []

        def print(self, message: str = "") -> None:
            self.messages.append(message)

        def panel(self, title: str, body: str) -> None:
            self.panels.append((title, body))

        def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
            pass

    io = _IO()
    rc = menu_mod.run_menu(input_func=lambda _p: next(inputs), io=io)
    assert rc == 0
    assert any("1 to 8" in m for m in io.messages)


def test_run_menu_handler_catches_user_facing_errors() -> None:
    """Handler exceptions return None (loop continues) and emit menu prefix."""

    class _IO:
        def __init__(self) -> None:
            self.messages: list[str] = []

        def print(self, message: str = "") -> None:
            self.messages.append(message)

        def panel(self, title: str, body: str) -> None:
            pass

        def table(self, *_a: Any, **_kw: Any) -> None:
            pass

    def failing(_io: Any, _input_func: Any) -> int:
        raise ValueError("boom")

    io = _IO()
    rc = menu_mod._run_menu_handler(failing, io, lambda _p: "")
    assert rc is None
    assert any("[bbwebscan menu] boom" in m for m in io.messages)


# ---- cli.py — error handlers in each subcommand dispatcher ----

def test_cmd_scan_translates_value_error_to_parser_error() -> None:
    """cmd_scan must convert build_run_config ValueError into argparse error (exit 2)."""
    parser = cli_mod.build_parser()
    args = parser.parse_args(["scan", "--mode", "aggressive", "--target", "example.com"])
    with pytest.raises(SystemExit):
        cli_mod.cmd_scan(args, parser)


def test_cmd_install_translates_file_not_found_to_parser_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = cli_mod.build_parser()
    args = parser.parse_args(["install", "--installer", "/no/such/installer.sh"])
    with pytest.raises(SystemExit):
        cli_mod.cmd_install(args, parser)


def test_cmd_doctor_translates_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = cli_mod.build_parser()
    args = parser.parse_args(["doctor", "--profile", "/no/such/profile.yaml"])
    with pytest.raises(SystemExit):
        cli_mod.cmd_doctor(args, parser)


def test_cmd_init_translates_file_exists_to_parser_error(tmp_path: Path) -> None:
    """When the profile file already exists and --force is absent, init raises."""
    parser = cli_mod.build_parser()
    out = tmp_path / "p.yaml"
    out.write_text("name: existing\n", encoding="utf-8")
    args = parser.parse_args(
        ["init", "demo", "--target", "example.com", "--out", str(out)],
    )
    with pytest.raises(SystemExit):
        cli_mod.cmd_init(args, parser)


def test_cmd_history_runs_clean_on_missing_runs_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """cmd_history's normal happy path with an empty runs dir — covers the
    dispatcher entry plus run_history's no-runs branch."""
    parser = cli_mod.build_parser()
    args = parser.parse_args(["history", "--runs-dir", str(tmp_path / "empty")])
    rc = cli_mod.cmd_history(args, parser)
    assert rc == 0
    assert "No completed runs found" in capsys.readouterr().out


def test_cmd_show_translates_errors(tmp_path: Path) -> None:
    parser = cli_mod.build_parser()
    args = parser.parse_args(["show", str(tmp_path / "missing")])
    with pytest.raises(SystemExit):
        cli_mod.cmd_show(args, parser)


def test_cmd_compare_translates_errors(tmp_path: Path) -> None:
    parser = cli_mod.build_parser()
    a = tmp_path / "a"
    b = tmp_path / "b"
    args = parser.parse_args(["compare", str(a), str(b)])
    with pytest.raises(SystemExit):
        cli_mod.cmd_compare(args, parser)


def test_main_dispatches_welcome_when_no_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Bare `bbwebscan` with no argv → menu, but the cmd_welcome path is
    reachable via the smart-default exiter for `--help`-style empty argv."""
    # The flat-CLI rewrites empty argv unchanged; argparse defaults to no
    # command → cmd_menu. Cover cmd_welcome via direct call instead.
    parser = cli_mod.build_parser()
    args = parser.parse_args([])
    rc = cli_mod.cmd_welcome(args, parser)
    assert rc == 0
    out = capsys.readouterr().out
    assert f"bbWebScan v{__version__}" in out


def test_smart_default_passes_through_help_flag() -> None:
    """`-h` and `--help` are not rewritten as scan args."""
    assert cli_mod._rewrite_smart_default(["-h"]) == ["-h"]
    assert cli_mod._rewrite_smart_default(["--help"]) == ["--help"]
    assert cli_mod._rewrite_smart_default(["--version"]) == ["--version"]


def test_smart_default_passes_through_non_dotted_non_flag() -> None:
    """A first arg with no `.` and no leading `-` is not a target — pass through."""
    # E.g. typo'd subcommand "scna" — argparse handles the error.
    assert cli_mod._rewrite_smart_default(["scna", "--foo"]) == ["scna", "--foo"]


def test_smart_default_handles_empty_argv() -> None:
    assert cli_mod._rewrite_smart_default([]) == []


def test_smart_default_rewrites_flag_only_args_as_scan() -> None:
    assert cli_mod._rewrite_smart_default(["--target", "x.com"]) == [
        "scan", "--target", "x.com",
    ]


# ---- installer.py — _ensure_naabu paths ----

def test_ensure_naabu_already_installed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("bbwebscan.installer.shutil.which", lambda name: "/usr/bin/naabu")
    rc = installer_mod._ensure_naabu(dry_run=False)
    assert rc == 0
    assert "already installed" in capsys.readouterr().out


def test_ensure_naabu_skips_when_go_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("bbwebscan.installer.shutil.which", lambda name: None)
    rc = installer_mod._ensure_naabu(dry_run=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "skipping" in out
    assert "`go` not on PATH" in out


def test_ensure_naabu_dry_run_when_go_present(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def which(name: str) -> str | None:
        return "/usr/bin/go" if name == "go" else None

    monkeypatch.setattr("bbwebscan.installer.shutil.which", which)
    rc = installer_mod._ensure_naabu(dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert "naabu@latest" in out


def test_ensure_naabu_runs_go_install(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def which(name: str) -> str | None:
        return "/usr/bin/go" if name == "go" else None

    monkeypatch.setattr("bbwebscan.installer.shutil.which", which)
    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool = False) -> Any:
        captured["cmd"] = cmd
        return argparse.Namespace(returncode=0)

    monkeypatch.setattr("bbwebscan.installer.subprocess.run", fake_run)
    rc = installer_mod._ensure_naabu(dry_run=False)
    assert rc == 0
    assert captured["cmd"][:2] == ["go", "install"]
    assert "naabu@latest" in captured["cmd"][2]


def test_run_installer_chains_helpers_then_bash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    installer_path = tmp_path / "fake_installer.sh"
    installer_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    installer_path.chmod(0o755)
    call_order: list[str] = []

    def fake_ensure_scrapy(*, dry_run: bool) -> int:
        call_order.append("scrapy")
        return 0

    def fake_ensure_naabu(*, dry_run: bool) -> int:
        call_order.append("naabu")
        return 0

    def fake_ensure_jwt_tool(*, dry_run: bool) -> int:
        call_order.append("jwt_tool")
        return 0

    def fake_run(cmd: list[str], check: bool = False) -> Any:
        call_order.append("bash")
        return argparse.Namespace(returncode=0)

    monkeypatch.setattr(installer_mod, "_ensure_scrapy", fake_ensure_scrapy)
    monkeypatch.setattr(installer_mod, "_ensure_naabu", fake_ensure_naabu)
    monkeypatch.setattr(installer_mod, "_ensure_jwt_tool", fake_ensure_jwt_tool)
    monkeypatch.setattr("bbwebscan.installer.subprocess.run", fake_run)
    args = argparse.Namespace(
        installer=str(installer_path),
        dry_run=False,
        persist_path=True,
        update_nuclei_templates=False,
    )
    rc = installer_mod.run_installer(args)
    assert rc == 0
    assert call_order == ["scrapy", "naabu", "jwt_tool", "bash"]


def test_resolve_rc_path_bash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")
    path = installer_mod._resolve_rc_path(None)
    assert path.name == ".bashrc"


def test_resolve_rc_path_zsh_honors_zdotdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setenv("ZDOTDIR", str(tmp_path))
    path = installer_mod._resolve_rc_path(None)
    assert path == tmp_path / ".zshrc"


def test_persist_path_writes_new_block_when_marker_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text("# existing rc\n", encoding="utf-8")
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")
    result_path, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc_file, candidate_dirs=(bin_dir,),
    )
    assert result_path == rc_file
    assert added == [bin_dir]
    body = rc_file.read_text(encoding="utf-8")
    assert installer_mod.PERSIST_MARKER in body
    assert str(bin_dir) in body


def test_persist_path_no_change_when_marker_present(tmp_path: Path) -> None:
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text(installer_mod.PERSIST_MARKER + "\n", encoding="utf-8")
    _, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc_file, candidate_dirs=(tmp_path,),
    )
    assert added == []


def test_persist_path_no_change_when_all_dirs_already_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text("", encoding="utf-8")
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    monkeypatch.setenv("PATH", str(bin_dir))
    _, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc_file, candidate_dirs=(bin_dir,),
    )
    assert added == []


def test_persist_path_skips_nonexistent_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    rc_file = tmp_path / ".zshrc"
    rc_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("PATH", "/usr/bin")
    nonexistent = tmp_path / "does-not-exist"
    _, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc_file, candidate_dirs=(nonexistent,),
    )
    assert added == []


# ---- menu_command.py — every flag-emission branch ----

def test_scan_command_args_emits_every_v056_flag() -> None:
    """One mega-settings object that flips every conditional emission branch."""
    settings = ScanSettings(
        targets=["example.com"],
        ack_authorized=True,
        mode="aggressive",
        severity="medium",
        check_dns=True,
        enumerate_subdomains=True,
        amass_mode="active",
        api_discovery=True,
        scrapy_deep=True,
        scrapy_max_depth=5,
        scrapy_js_render=True,
        jwt_analysis=True,
        sqlmap_mode="aggressive",
        sqlmap_timeout=1234,
        port_scan=True,
        port_scan_mode="full",
        port_scan_rate=2000,
        quiet=True,
        strict_identity=True,
        dry_run=True,
    )
    argv = scan_command_args(settings, dry_run_override=None, redact_auth=True)
    expected_flags = {
        "--ack-authorized",
        "--severity",
        "--check-dns",
        "--enumerate-subdomains",
        "--amass-mode",
        "--api-discovery",
        "--scrapy-deep",
        "--scrapy-max-depth",
        "--scrapy-js-render",
        "--jwt-analysis",
        "--sqlmap-mode",
        "--sqlmap-timeout",
        "--port-scan",
        "--port-scan-mode",
        "--port-scan-rate",
        "--dry-run",
        "--quiet",
        "--strict-identity",
    }
    assert expected_flags.issubset(set(argv)), expected_flags - set(argv)


def test_redact_header_returns_value_unchanged_when_no_colon() -> None:
    assert redact_header("noproblem") == "noproblem"


def test_redact_cookie_returns_value_unchanged_when_no_equals() -> None:
    assert redact_cookie("noproblem") == "noproblem"


# ---- pipeline.py — open_ports re-decision short-circuit + edge cases ----

def test_filter_open_ports_short_circuits_already_decided_host(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Same host:port re-emitted across plans: second sight uses the cached
    decision instead of re-running host_in_scope."""
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    config = RunConfig(
        program_name="t", seed_urls=[], allowed_hosts=["example.com"],
        denied_hosts=[], auth=AuthConfig(), mode="safe", enabled_tools=["naabu"],
        wordlist=Path("/tmp/x"), threads=1, rate=1, tool_timeout_s=1,
        command_wall_clock_s=1, retry=RetryPolicy(), output_dir=tmp_path / "run",
        target_inputs=["https://example.com"], dry_run=True,
    )
    state = pipeline_mod._PipelineState(
        config=config, artifacts=artifacts,
        targets=[NormalizedTarget(
            raw="example.com", host="example.com", seed_url="https://example.com",
        )],
        allowed_hosts=["example.com"], scope_decisions=[],
    )
    # First call: example.com:8080 enters the decision cache as allowed.
    kept = pipeline_mod._filter_open_ports_in_scope(state, ["example.com:8080"])
    assert kept == ["example.com:8080"]
    # Second call with the same host:port: short-circuit via the cache.
    kept2 = pipeline_mod._filter_open_ports_in_scope(state, ["example.com:8080"])
    assert kept2 == ["example.com:8080"]


def test_extend_targets_skips_malformed_port_str() -> None:
    targets = [NormalizedTarget(
        raw="example.com", host="example.com", seed_url="https://example.com",
    )]
    extended = pipeline_mod._extend_targets_with_open_ports(
        targets, ["example.com:not-an-int", "example.com:8080"],
    )
    seed_urls = [t.seed_url for t in extended]
    assert "https://example.com:8080" in seed_urls
    # not-an-int line is silently skipped (no new target)
    assert all(":not-an-int" not in u for u in seed_urls)


def test_extend_targets_skips_duplicate_seed_url() -> None:
    targets = [NormalizedTarget(
        raw="example.com:8080", host="example.com",
        seed_url="https://example.com:8080",
    )]
    extended = pipeline_mod._extend_targets_with_open_ports(
        targets, ["example.com:8080"],
    )
    # Already-known seed URL → not duplicated.
    assert len(extended) == 1


# ---- bbspider.py — direct unit tests against the spider ----

def test_bbspider_init_rejects_missing_urls_file() -> None:
    with pytest.raises(ValueError, match="urls_file"):
        BbSpider(urls_file=None)


def test_bbspider_init_rejects_nonexistent_urls_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        BbSpider(urls_file=str(tmp_path / "no.txt"))


def test_bbspider_init_rejects_empty_urls_file(tmp_path: Path) -> None:
    urls = tmp_path / "urls.txt"
    urls.write_text("# only comments\n\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        BbSpider(urls_file=str(urls))


def test_bbspider_init_rejects_non_integer_depth(tmp_path: Path) -> None:
    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com\n", encoding="utf-8")
    with pytest.raises(ValueError, match="integer"):
        BbSpider(urls_file=str(urls), max_depth="not-a-number")


def test_bbspider_init_rejects_depth_out_of_range(tmp_path: Path) -> None:
    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com\n", encoding="utf-8")
    with pytest.raises(ValueError, match="1..5"):
        BbSpider(urls_file=str(urls), max_depth=99)


def _make_spider(tmp_path: Path, **kwargs: Any) -> Any:
    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com\n", encoding="utf-8")
    return BbSpider(urls_file=str(urls), **kwargs)


def test_bbspider_extract_emails_dedupes_and_caps(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    text = "a@b.com a@b.com c@d.org" + " e@f.org" * 100
    emails = spider._extract_emails(text)
    assert "a@b.com" in emails
    assert "c@d.org" in emails
    assert len(emails) <= 50


def test_bbspider_extract_emails_empty_input(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    assert spider._extract_emails("") == []


def test_bbspider_extract_secrets_returns_empty_without_deep_mode(
    tmp_path: Path,
) -> None:
    spider = _make_spider(tmp_path, deep_mode=False)
    assert spider._extract_secrets("aws_access_key_id=AKIA1234567890123456", "u") == []


def test_bbspider_in_scope_matches_allowed_and_subdomains(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    assert spider._in_scope("https://example.com/path") is True
    assert spider._in_scope("https://sub.example.com/path") is True
    assert spider._in_scope("https://evil.test/path") is False
    assert spider._in_scope("not-a-url") is False


def test_bbspider_start_requests_yields_one_per_url(tmp_path: Path) -> None:
    urls = tmp_path / "urls.txt"
    urls.write_text(
        "https://example.com\nhttps://api.example.com\n# comment\n",
        encoding="utf-8",
    )
    spider = BbSpider(urls_file=str(urls), js_render=True)  # exercise js_render branch
    requests = list(spider.start_requests())
    assert len(requests) == 2
    assert all(r.meta.get("playwright") is True for r in requests)


def test_bbspider_truthy_helper_covers_all_branches() -> None:
    assert bbspider_mod._truthy(True) is True
    assert bbspider_mod._truthy(False) is False
    assert bbspider_mod._truthy(1) is True
    assert bbspider_mod._truthy(0) is False
    assert bbspider_mod._truthy(1.5) is True
    assert bbspider_mod._truthy("yes") is True
    assert bbspider_mod._truthy("no") is False
    assert bbspider_mod._truthy("") is False
    assert bbspider_mod._truthy(None) is False
    assert bbspider_mod._truthy(["x"]) is False  # unsupported type → False


def test_bbspider_load_patterns_no_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """When the patterns YAML is missing, _load_patterns returns []."""
    monkeypatch.setattr(bbspider_mod, "_PATTERNS_FILE", tmp_path / "no.yml")
    assert bbspider_mod._load_patterns() == []


def test_bbspider_load_patterns_handles_invalid_regex_and_missing_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    bad = tmp_path / "patterns.yml"
    bad.write_text(
        "patterns:\n"
        "  - name: good\n"
        "    regex: '[a-z]+'\n"
        "    confidence: high\n"
        "  - name: invalid-regex\n"
        "    regex: '[unclosed'\n"
        "    confidence: medium\n"
        "  - regex: 'no-name'\n"
        "  - name: unknown-confidence\n"
        "    regex: 'x'\n"
        "    confidence: stratospheric\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bbspider_mod, "_PATTERNS_FILE", bad)
    patterns = bbspider_mod._load_patterns()
    names = [name for name, _, _ in patterns]
    assert "good" in names
    assert "invalid-regex" not in names  # regex compile failed
    assert "unknown-confidence" in names  # normalized to medium
    # Confidence normalization for the "unknown-confidence" pattern
    for name, _, conf in patterns:
        if name == "unknown-confidence":
            assert conf == "medium"


def test_bbspider_parse_yields_jsonl_payload_for_html(tmp_path: Path) -> None:
    """[v0.5.6] Drive parse() with a fake HtmlResponse; verify the yielded dict
    matches the documented JSONL schema."""
    spider = _make_spider(tmp_path, deep_mode=False)
    body = (
        b"<html><head><title>Hello</title></head><body>"
        b"<a href=\"https://example.com/a\">a</a>"
        b"<a href=\"https://example.com/b.pdf\">doc</a>"
        b"<a href=\"https://example.com/.git/HEAD\">leak</a>"
        b"<a href=\"javascript:foo\">js</a>"
        b"<script src=\"https://example.com/app.js\"></script>"
        b"contact me at admin@example.com"
        b"</body></html>"
    )
    request = Request(url="https://example.com")
    response = HtmlResponse(
        url="https://example.com", request=request, body=body,
        headers={"Content-Type": "text/html"}, encoding="utf-8",
    )
    items = list(spider.parse(response))
    # First yield is the JSONL record; subsequent yields are follow-up requests.
    record = items[0]
    assert record["url"] == "https://example.com"
    assert record["status"] == 200
    assert record["title"] == "Hello"
    assert "https://example.com/a" in record["links"]
    assert any("b.pdf" in d for d in record["documents"])
    assert any(".git" in e for e in record["exposed_paths"])
    assert "admin@example.com" in record["emails"]
    # The script tag → scripts list, not links
    assert any("app.js" in s for s in record["scripts"])
    # Follow-up requests are scrapy.Request instances
    follow_ups = items[1:]
    assert all(hasattr(r, "url") for r in follow_ups)


def test_bbspider_parse_stops_at_max_depth(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path, max_depth=1)
    body = b"<html><body><a href=\"https://example.com/x\">x</a></body></html>"
    request = Request(url="https://example.com")
    response = HtmlResponse(
        url="https://example.com", request=request, body=body,
        headers={"Content-Type": "text/html"}, encoding="utf-8",
    )
    response.meta["depth"] = 1  # at max_depth
    items = list(spider.parse(response))
    # Only the record, no follow-up requests
    assert len(items) == 1
    assert "url" in items[0]


def test_bbspider_parse_handles_non_html_content_type(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    request = Request(url="https://example.com/data.json")
    response = TextResponse(
        url="https://example.com/data.json",
        request=request,
        body=b'{"key": "value", "contact": "x@y.com"}',
        headers={"Content-Type": "application/json"},
        encoding="utf-8",
    )
    items = list(spider.parse(response))
    record = items[0]
    assert record["title"] == ""
    assert record["links"] == []
    assert "x@y.com" in record["emails"]


def test_bbspider_parse_deep_mode_secret_extraction(tmp_path: Path) -> None:
    """[v0.5.6] When deep_mode is on, secrets are detected and emitted with a
    SHA-256 evidence digest (never the raw value)."""
    spider = _make_spider(tmp_path, deep_mode=True)
    # Replace patterns with a known one so we don't depend on the vendored file.
    spider._patterns = [("test-secret", re.compile(r"SECRET_[A-Z0-9]+"), "high")]
    body = b"<html><body>Token: SECRET_ABC123 also SECRET_ABC123</body></html>"
    request = Request(url="https://example.com")
    response = HtmlResponse(
        url="https://example.com", request=request, body=body,
        headers={"Content-Type": "text/html"}, encoding="utf-8",
    )
    record = list(spider.parse(response))[0]
    secrets = record["secrets"]
    assert len(secrets) == 1  # deduped by (name, digest)
    secret = secrets[0]
    assert secret["name"] == "test-secret"
    assert "SECRET_ABC123" not in json.dumps(secret)
    assert len(secret["evidence_sha256"]) == 16
    assert secret["confidence"] == "high"


def test_bbspider_extract_secrets_caps_per_page(tmp_path: Path) -> None:
    """[v0.5.6] _extract_secrets stops at _MAX_SECRETS_PER_PAGE."""
    spider = _make_spider(tmp_path, deep_mode=True)
    # Each match is unique (different digest), so cap kicks in.
    spider._patterns = [("k", re.compile(r"SECRET_\d+"), "low")]
    body = " ".join(f"SECRET_{i}" for i in range(50))
    hits = spider._extract_secrets(body, "u")
    assert len(hits) == 20  # _MAX_SECRETS_PER_PAGE
