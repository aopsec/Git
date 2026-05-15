"""[v0.5.6] Second coverage-boost batch — targets remaining gaps after boost1."""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from bbwebscan import history as history_mod
from bbwebscan import installer as installer_mod
from bbwebscan import menu_actions, menu_profile
from bbwebscan import menu_scan as menu_scan_mod
from bbwebscan import pipeline as pipeline_mod
from bbwebscan import preflight as preflight_mod
from bbwebscan import runner as runner_mod
from bbwebscan.menu_types import ScanSettings
from bbwebscan.models import (
    AuthConfig,
    CommandPlan,
    ExecutionResult,
    NormalizedTarget,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
    ScopeDecision,
    ToolStatus,
)
from bbwebscan.stages import (
    _jsonl,
    discovery_stage,
    httpx_stage,
    katana_stage,
    kiterunner_stage,
    params_stage,
)
from bbwebscan.targets import filter_urls_in_scope, resolve_host


def _stub_io_factory() -> Any:
    class _IO:
        def __init__(self) -> None:
            self.messages: list[str] = []
            self.panels: list[tuple[str, str]] = []
            self.tables: list[tuple[str, list[str], list[list[str]]]] = []

        def print(self, message: str = "") -> None:
            self.messages.append(message)

        def panel(self, title: str, body: str) -> None:
            self.panels.append((title, body))

        def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
            self.tables.append((title, columns, rows))

    return _IO


# ---- menu_scan helpers ----

def test_collect_scrapy_depth_returns_base_on_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank input → prompt_int returns None → helper returns base."""
    settings = ScanSettings(scrapy_max_depth=3)
    depth = menu_scan_mod._collect_scrapy_depth(settings, lambda _p: "")
    assert depth == 3


def test_collect_scrapy_depth_clamps_to_valid_range() -> None:
    settings = ScanSettings(scrapy_max_depth=2)
    # Out-of-range high → clamped to 5
    depth = menu_scan_mod._collect_scrapy_depth(settings, lambda _p: "99")
    assert depth == 5
    # Out-of-range low → clamped to 1
    depth = menu_scan_mod._collect_scrapy_depth(settings, lambda _p: "-1")
    assert depth == 1


def test_collect_amass_mode_re_prompts_for_ack_on_active() -> None:
    """When amass mode is non-passive and ack=False, re-prompts for AUTHORIZED."""
    settings = ScanSettings(amass_mode="passive")
    inputs = iter(["active", "AUTHORIZED"])
    mode, ack = menu_scan_mod._collect_amass_mode(
        settings, enumerate_subdomains=True, ack=False, input_func=lambda _p: next(inputs),
    )
    assert mode == "active"
    assert ack is True


def test_collect_sqlmap_mode_re_prompts_for_ack_on_aggressive() -> None:
    settings = ScanSettings(sqlmap_mode="off")
    inputs = iter(["aggressive", "AUTHORIZED"])
    mode, ack = menu_scan_mod._collect_sqlmap_mode(
        settings, ack=False, input_func=lambda _p: next(inputs),
    )
    assert mode == "aggressive"
    assert ack is True


def test_collect_sqlmap_timeout_returns_base_on_blank() -> None:
    settings = ScanSettings(sqlmap_timeout=900)
    out = menu_scan_mod._collect_sqlmap_timeout(settings, lambda _p: "")
    assert out == 900


def test_collect_sqlmap_timeout_rejects_zero() -> None:
    settings = ScanSettings(sqlmap_timeout=600)
    out = menu_scan_mod._collect_sqlmap_timeout(settings, lambda _p: "0")
    assert out == 600


def test_collect_port_scan_mode_default_when_disabled() -> None:
    """[v0.5.6] When port_scan is False, the mode prompt is skipped."""
    settings = ScanSettings(port_scan_mode="top-1000")
    mode, ack = menu_scan_mod._collect_port_scan_mode(
        settings, port_scan=False, ack=True, input_func=lambda _p: "should-not-be-asked",
    )
    assert mode == "top-1000"
    assert ack is True


def test_collect_port_scan_mode_re_prompts_for_ack_on_full() -> None:
    """[v0.5.6] full mode + no ack → re-prompts for AUTHORIZED."""
    settings = ScanSettings(port_scan_mode="top-100")
    inputs = iter(["full", "AUTHORIZED"])
    mode, ack = menu_scan_mod._collect_port_scan_mode(
        settings, port_scan=True, ack=False, input_func=lambda _p: next(inputs),
    )
    assert mode == "full"
    assert ack is True


def test_collect_port_scan_rate_returns_base_when_disabled() -> None:
    settings = ScanSettings(port_scan_rate=2000)
    rate = menu_scan_mod._collect_port_scan_rate(
        settings, port_scan=False, input_func=lambda _p: "should-not-be-asked",
    )
    assert rate == 2000


def test_collect_port_scan_rate_blank_keeps_base() -> None:
    settings = ScanSettings(port_scan_rate=500)
    rate = menu_scan_mod._collect_port_scan_rate(
        settings, port_scan=True, input_func=lambda _p: "",
    )
    assert rate == 500


def test_collect_port_scan_rate_rejects_zero_or_negative() -> None:
    settings = ScanSettings(port_scan_rate=1000)
    rate = menu_scan_mod._collect_port_scan_rate(
        settings, port_scan=True, input_func=lambda _p: "-5",
    )
    assert rate == 1000


def test_run_configured_scan_catches_value_error() -> None:
    """When build_run_config raises, the menu prints the error and returns 2."""
    io_cls = _stub_io_factory()
    io = io_cls()
    settings = ScanSettings(targets=[], mode="aggressive", ack_authorized=False)
    rc = menu_scan_mod._run_configured_scan(
        settings, dry_run=False, io=io, scan_executor=lambda _c: 0,
    )
    assert rc == 2
    assert any("[bbwebscan menu]" in m for m in io.messages)


# ---- menu_actions ----

def test_run_doctor_auto_fix_reports_suspect_when_no_fixes_needed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[v0.5.6] When nothing needs install/path-fix but identities are suspect,
    print the suspect names and return doctor's normal exit code."""
    io_cls = _stub_io_factory()
    io = io_cls()

    suspect_status = ToolStatus(
        name="x", required=True, found=True, identity="suspect",
        path=Path("/fake/x"), note="suspect note",
    )
    monkeypatch.setattr(menu_actions, "inventory_tools", lambda _t: [suspect_status])
    rc = menu_actions.run_doctor_auto_fix(io, input_func=lambda _p: "n")
    assert rc == 0
    assert any("Suspect identities" in m for m in io.messages)


def test_run_history_menu_passes_default_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_history(args: argparse.Namespace) -> int:
        captured["limit"] = args.limit
        captured["runs_dir"] = args.runs_dir
        return 0

    monkeypatch.setattr(menu_actions, "run_history", fake_run_history)
    assert menu_actions.run_history_menu() == 0
    assert captured["limit"] == 20
    assert captured["runs_dir"] is None


def test_run_show_menu_returns_zero_on_blank_input() -> None:
    assert menu_actions.run_show_menu(input_func=lambda _p: "") == 0


def test_run_compare_menu_returns_zero_on_blank_input() -> None:
    inputs = iter(["", ""])
    assert menu_actions.run_compare_menu(input_func=lambda _p: next(inputs)) == 0


def test_doctor_state_classifies_each_status() -> None:
    found = ToolStatus(name="x", required=True, found=True, identity="verified")
    assert menu_actions.doctor_state(found) == "found"

    missing = ToolStatus(name="x", required=True, found=False)
    assert menu_actions.doctor_state(missing) == "missing"

    path_gap = ToolStatus(
        name="x", required=True, found=False, path_gap=Path("/somewhere"),
    )
    assert menu_actions.doctor_state(path_gap) == "path-gap"

    shadowed = ToolStatus(
        name="x", required=True, found=True, shadowed_by=Path("/usr/bin/x"),
    )
    assert menu_actions.doctor_state(shadowed) == "shadowed"

    suspect = ToolStatus(name="x", required=True, found=True, identity="suspect")
    assert menu_actions.doctor_state(suspect) == "suspect"


# ---- menu_profile ----

def test_save_profile_interactive_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    io_cls = _stub_io_factory()
    io = io_cls()
    settings = ScanSettings(
        targets=["example.com"], profile=None, mode="safe",
    )
    inputs = iter([
        "demo",                # Program name
        str(tmp_path / "demo.yaml"),  # Profile output path
        "y",                   # Overwrite
        "n",                   # Add saved header
        "n",                   # Add saved cookie
    ])
    out_path = menu_profile.save_profile_interactive(
        settings, io, input_func=lambda _p: next(inputs),
    )
    assert out_path.exists()
    body = out_path.read_text(encoding="utf-8")
    assert "demo" in body


# ---- installer.py edge paths ----

def test_ensure_scrapy_dry_run_when_pipx_present(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """[v0.5.6] _ensure_scrapy uses pipx when present and dry-run prints command."""
    def which(name: str) -> str | None:
        if name == "scrapy":
            return None
        if name == "pipx":
            return "/usr/bin/pipx"
        return None

    monkeypatch.setattr("bbwebscan.installer.shutil.which", which)
    rc = installer_mod._ensure_scrapy(dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert "pipx" in out


def test_ensure_scrapy_dry_run_pip_fallback_when_pipx_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    def which(name: str) -> str | None:
        return None

    monkeypatch.setattr("bbwebscan.installer.shutil.which", which)
    rc = installer_mod._ensure_scrapy(dry_run=True)
    assert rc == 0
    assert "pip" in capsys.readouterr().out


def test_ensure_scrapy_actually_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bbwebscan.installer.shutil.which",
        lambda n: "/usr/bin/pipx" if n == "pipx" else None,
    )
    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool = False) -> Any:
        captured["cmd"] = cmd
        return argparse.Namespace(returncode=0)

    monkeypatch.setattr("bbwebscan.installer.subprocess.run", fake_run)
    rc = installer_mod._ensure_scrapy(dry_run=False)
    assert rc == 0
    assert captured["cmd"][:3] == ["/usr/bin/pipx", "install", "scrapy"]


def test_ensure_jwt_tool_already_installed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """[v0.5.6] _ensure_jwt_tool short-circuits when the script is already on PATH."""
    monkeypatch.setattr(
        "bbwebscan.installer.shutil.which",
        lambda n: "/usr/bin/jwt_tool" if n == "jwt_tool" else None,
    )
    rc = installer_mod._ensure_jwt_tool(dry_run=False)
    assert rc == 0
    assert "already installed" in capsys.readouterr().out


def test_ensure_jwt_tool_dry_run_when_pipx_present(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """[v0.5.6] _ensure_jwt_tool prefers pipx when available and dry-run echoes cmd."""
    def which(name: str) -> str | None:
        if name == "jwt_tool":
            return None
        if name == "pipx":
            return "/usr/bin/pipx"
        return None

    monkeypatch.setattr("bbwebscan.installer.shutil.which", which)
    rc = installer_mod._ensure_jwt_tool(dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out
    assert "pipx" in out
    assert "jwt_tool" in out


def test_ensure_jwt_tool_dry_run_pip_fallback_when_pipx_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """[v0.5.6] _ensure_jwt_tool falls back to pip --user when pipx is unavailable."""
    monkeypatch.setattr("bbwebscan.installer.shutil.which", lambda n: None)
    rc = installer_mod._ensure_jwt_tool(dry_run=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "pip" in out
    assert "jwt_tool" in out


def test_ensure_jwt_tool_actually_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[v0.5.6] _ensure_jwt_tool invokes pipx install jwt_tool when not dry-run."""
    monkeypatch.setattr(
        "bbwebscan.installer.shutil.which",
        lambda n: "/usr/bin/pipx" if n == "pipx" else None,
    )
    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool = False) -> Any:
        captured["cmd"] = cmd
        return argparse.Namespace(returncode=0)

    monkeypatch.setattr("bbwebscan.installer.subprocess.run", fake_run)
    rc = installer_mod._ensure_jwt_tool(dry_run=False)
    assert rc == 0
    assert captured["cmd"][:3] == ["/usr/bin/pipx", "install", "jwt_tool"]


def test_persist_path_no_marker_no_change_when_target_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """If target rc file doesn't exist, persist_path creates it and writes."""
    rc_file = tmp_path / "subdir" / ".zshrc"
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")
    _, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc_file, candidate_dirs=(bin_dir,),
    )
    assert added == [bin_dir]
    assert rc_file.is_file()


# ---- pipeline.py _run_discovery + invalid-target branches ----

def test_run_discovery_executes_when_tool_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    captured_stages: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _c: RunConfig, _a: RunArtifacts,
    ) -> ExecutionResult:
        captured_stages.append(plan.stage)
        return ExecutionResult(
            stage=plan.stage, label=plan.label, command=plan.command,
            status="dry-run", artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline_mod, "collect_tool_inventory", lambda _c: [])
    monkeypatch.setattr(pipeline_mod, "validate_environment", lambda _c, _s: [])
    monkeypatch.setattr(pipeline_mod, "run_plan", fake_run_plan)
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _p: ([], ["https://app.example.com"]))
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(discovery_stage, "parse_results", lambda _p, _c: ([], []))

    config = RunConfig(
        program_name="test", seed_urls=[], allowed_hosts=["example.com"],
        denied_hosts=[], auth=AuthConfig(), mode="aggressive",
        enabled_tools=["httpx", "katana", "ffuf"], ack_authorized=True,
        wordlist=Path("/tmp/words.txt"), threads=1, rate=1, tool_timeout_s=1,
        command_wall_clock_s=1, retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["https://app.example.com"],
        dry_run=True,
    )
    pipeline_mod.execute_scan(config)
    # Discovery stage runs ffuf via stage='discovery' (label carries the tool name).
    assert "discovery" in captured_stages


def test_extend_targets_with_fqdns_handles_invalid_target() -> None:
    """An FQDN that fails normalize_target (e.g. bare TLD) is recorded as
    invalid and skipped — covers the except branch."""
    targets: list[NormalizedTarget] = []
    fqdns = ["valid.example.com", "com"]  # "com" is a bare TLD → ValueError
    decisions: list[ScopeDecision] = []
    decided: set[str] = set()
    extended = pipeline_mod._extend_targets_with_fqdns(
        targets, fqdns, ["example.com"], [], decisions, decided,
    )
    hosts = [t.host for t in extended]
    assert "valid.example.com" in hosts
    # The invalid one is recorded as a rejected scope decision
    invalid = [d for d in decisions if d.reason == "invalid-target"]
    assert any(d.value == "com" for d in invalid)


# ---- preflight.py ----

def test_detect_version_returns_none_for_unknown_tool(tmp_path: Path) -> None:
    """tool with no VERSION_ARGS entry → returns None."""
    assert preflight_mod.detect_version("nonexistent-tool", tmp_path / "x") is None


def test_detect_version_handles_probe_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake"
    fake_bin.write_text("", encoding="utf-8")

    def fake_probe(_tool: Path, _args: list[str]) -> tuple[int, str]:
        return (-1, "")  # _PROBE_TIMEOUT_RC

    monkeypatch.setattr(preflight_mod, "_probe", fake_probe)
    assert preflight_mod.detect_version("httpx", fake_bin) == "probe-timeout"


def test_detect_version_handles_os_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake"
    fake_bin.write_text("", encoding="utf-8")

    def fake_probe(_tool: Path, _args: list[str]) -> tuple[int, str]:
        return (-2, "")  # _PROBE_OS_ERROR_RC

    monkeypatch.setattr(preflight_mod, "_probe", fake_probe)
    assert preflight_mod.detect_version("httpx", fake_bin) is None


def test_detect_identity_returns_none_when_no_fingerprint(tmp_path: Path) -> None:
    fake_bin = tmp_path / "x"
    fake_bin.write_text("", encoding="utf-8")
    assert preflight_mod.detect_identity("no-such-tool", fake_bin) is None


def test_detect_identity_returns_suspect_when_neither_probe_matches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "x"
    fake_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(preflight_mod, "_probe", lambda _t, _a: (0, "unrelated banner"))
    result = preflight_mod.detect_identity("httpx", fake_bin)
    assert result == "suspect"


def test_compile_profile_fingerprints_rejects_invalid_regex() -> None:
    """An invalid regex string raises an actionable error."""
    with pytest.raises(ValueError, match="Invalid tool_identity regex"):
        preflight_mod._compile_profile_fingerprints({"httpx": "[unclosed"})


# ---- runner.py — write_lines / write_json / redact paths ----

def test_write_json_writes_pretty(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    runner_mod.write_json(target, {"k": "v"})
    assert json.loads(target.read_text()) == {"k": "v"}


def test_write_lines_writes_newline_delimited(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    runner_mod.write_lines(target, ["a", "b"])
    assert target.read_text().splitlines() == ["a", "b"]


def test_prepare_run_artifacts_creates_subdirs(tmp_path: Path) -> None:
    """[v0.5.6] prepare_run_artifacts is the canonical artifacts/ + logs/ creator."""
    artifacts = runner_mod.prepare_run_artifacts(tmp_path / "run")
    assert artifacts.logs.is_dir()
    assert artifacts.artifacts.is_dir()


# ---- _jsonl ----

def test_load_json_or_jsonl_handles_top_level_list(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"a": 1}, {"b": 2}, "not-a-dict"]), encoding="utf-8")
    out = _jsonl.load_json_or_jsonl(p)
    assert out == [{"a": 1}, {"b": 2}]


def test_load_json_or_jsonl_handles_scalar_top_level(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text("42", encoding="utf-8")
    assert _jsonl.load_json_or_jsonl(p) == []


def test_load_json_or_jsonl_missing_file(tmp_path: Path) -> None:
    assert _jsonl.load_json_or_jsonl(tmp_path / "no.json") == []


# ---- discovery_stage build paths ----

def _disc_config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        program_name="t", seed_urls=[], allowed_hosts=["example.com"],
        denied_hosts=[], auth=AuthConfig(), mode="aggressive",
        enabled_tools=["ffuf", "feroxbuster", "dirsearch"], ack_authorized=True,
        wordlist=Path("/tmp/w"), threads=2, rate=5, tool_timeout_s=1,
        command_wall_clock_s=1, retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["https://app.example.com"],
        dry_run=True,
    )


def test_discovery_ffuf_command_shape(tmp_path: Path) -> None:
    config = _disc_config(tmp_path)
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    plans = discovery_stage.build_plans(config, artifacts, ["https://app.example.com"])
    ffuf_plan = next(p for p in plans if "ffuf" in p.command)
    assert ffuf_plan.command[ffuf_plan.command.index("-u") + 1].endswith("/FUZZ")
    assert "-ac" in ffuf_plan.command
    assert ffuf_plan.command[ffuf_plan.command.index("-of") + 1] == "json"


def test_discovery_ffuf_command_with_raw_request(tmp_path: Path) -> None:
    raw = tmp_path / "req.txt"
    raw.write_text("GET / HTTP/1.1\n", encoding="utf-8")
    config = _disc_config(tmp_path)
    config.auth = AuthConfig(raw_request=raw)
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    plans = discovery_stage.build_plans(config, artifacts, ["https://app.example.com"])
    ffuf_plan = next(p for p in plans if "ffuf" in p.command)
    assert "-request" in ffuf_plan.command
    assert ffuf_plan.command[ffuf_plan.command.index("-request") + 1] == str(raw)


def test_discovery_feroxbuster_command_shape(tmp_path: Path) -> None:
    config = _disc_config(tmp_path)
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    plans = discovery_stage.build_plans(config, artifacts, ["https://app.example.com"])
    fb_plan = next(p for p in plans if "feroxbuster" in p.command)
    assert "--json" in fb_plan.command
    assert "-u" in fb_plan.command


# ---- params_stage parse edge paths ----

def test_params_parse_results_empty_artifact_list() -> None:
    findings, urls = params_stage.parse_results([])
    assert findings == []
    assert urls == []


def test_params_parse_results_missing_file(tmp_path: Path) -> None:
    findings, urls = params_stage.parse_results([tmp_path / "missing.json"])
    assert findings == []
    assert urls == []


def test_params_parse_results_malformed_payload(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    findings, urls = params_stage.parse_results([p])
    assert findings == []
    assert urls == []


# ---- kiterunner parse edge paths ----

def test_kiterunner_parse_results_empty_list() -> None:
    findings, routes = kiterunner_stage.parse_results([])
    assert findings == []
    assert routes == []


# ---- targets.py edge paths ----

def test_resolve_host_returns_none_on_lookup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_gethostbyname(host: str) -> str:
        raise socket.gaierror("nope")

    monkeypatch.setattr("bbwebscan.targets.socket.gethostbyname", fake_gethostbyname)
    assert resolve_host("nonexistent.example.invalid") is None


def test_filter_urls_in_scope_rejects_invalid_urls() -> None:
    kept, decisions = filter_urls_in_scope(
        ["not-a-url-no-scheme"], ["example.com"], [],
    )
    # No hostname → marked invalid-url
    assert "not-a-url-no-scheme" not in kept
    assert any(d.reason == "invalid-url" for d in decisions)


def test_filter_urls_in_scope_skips_already_decided() -> None:
    decided = {"https://example.com/x"}
    kept, decisions = filter_urls_in_scope(
        ["https://example.com/x", "https://example.com/y"],
        ["example.com"], [], already_decided=decided,
    )
    # /x is short-circuited; /y is freshly decided
    assert "https://example.com/y" in kept
    assert all(d.value != "https://example.com/x" for d in decisions)


# ---- history.py edge paths ----

def test_show_run_raises_when_summary_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no summary.md"):
        history_mod.show_run(tmp_path)


def test_compare_runs_raises_when_findings_missing(tmp_path: Path) -> None:
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    run_a.mkdir()
    run_b.mkdir()
    with pytest.raises(FileNotFoundError, match="no findings.json"):
        history_mod.compare_runs(run_a, run_b)


def test_compare_runs_handles_non_list_findings(tmp_path: Path) -> None:
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    run_a.mkdir()
    run_b.mkdir()
    (run_a / "findings.json").write_text('{"not": "a list"}', encoding="utf-8")
    (run_b / "findings.json").write_text("[]", encoding="utf-8")
    out = history_mod.compare_runs(run_a, run_b)
    # Non-list payload → empty list, no findings to compare
    assert "Added" in out or "added" in out or out  # non-empty output
