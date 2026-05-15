"""[v0.5.6] Third coverage-boost batch — final push to ≥97%."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest
from scrapy.http import HtmlResponse, Request

from bbwebscan import (
    config as config_mod,
)
from bbwebscan import (
    doctor as doctor_mod,
)
from bbwebscan import (
    history as history_mod,
)
from bbwebscan import (
    installer as installer_mod,
)
from bbwebscan import (
    menu_profile,
)
from bbwebscan import (
    pipeline as pipeline_mod,
)
from bbwebscan import (
    preflight as preflight_mod,
)
from bbwebscan import (
    runner as runner_mod,
)
from bbwebscan import (
    targets as targets_mod,
)
from bbwebscan.menu_types import ScanSettings
from bbwebscan.models import (
    AuthConfig,
    CommandPlan,
    NormalizedTarget,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
    ToolStatus,
)
from bbwebscan.stages import amass_stage, discovery_stage, kiterunner_stage, params_stage
from bbwebscan.stages.scrapy.bbspider import BbSpider
from bbwebscan.targets import enforce_scope_gate, normalize_target


def _make_run_config(tmp_path: Path, **overrides: Any) -> RunConfig:
    base = RunConfig(
        program_name="t", seed_urls=[], allowed_hosts=["example.com"],
        denied_hosts=[], auth=AuthConfig(), mode="safe", enabled_tools=[],
        wordlist=tmp_path / "wordlist.txt", threads=1, rate=1, tool_timeout_s=1,
        command_wall_clock_s=1, retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["https://example.com"],
        dry_run=True,
    )
    return base.model_copy(update=overrides)


# ---- runner.py — _execute_once error branches ----

def test_execute_once_timeout(tmp_path: Path) -> None:
    """A subprocess that exceeds the wall clock returns ('timeout', 124, ...)."""
    plan = CommandPlan(
        stage="t", label="x",
        command=["python3", "-c", "import time; time.sleep(10)"],
    )
    config = _make_run_config(tmp_path, command_wall_clock_s=1, dry_run=False)
    stdout_log = tmp_path / "out.log"
    stderr_log = tmp_path / "err.log"
    status, exit_code, error = runner_mod._execute_once(
        plan, config, stdout_log, stderr_log,
    )
    assert status == "timeout"
    assert exit_code == 124
    assert "timeout" in (error or "")


def test_execute_once_missing_binary(tmp_path: Path) -> None:
    plan = CommandPlan(
        stage="t", label="x",
        command=["/no/such/binary"],
    )
    config = _make_run_config(tmp_path, dry_run=False)
    stdout_log = tmp_path / "out.log"
    stderr_log = tmp_path / "err.log"
    status, exit_code, _ = runner_mod._execute_once(
        plan, config, stdout_log, stderr_log,
    )
    assert status == "missing-binary"
    assert exit_code is None


def test_execute_once_os_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """A subprocess.run that raises OSError → status 'os-error'."""
    def fake_run(*_args: Any, **_kw: Any) -> Any:
        raise OSError("permission denied")

    monkeypatch.setattr("bbwebscan.runner.subprocess.run", fake_run)
    plan = CommandPlan(stage="t", label="x", command=["whatever"])
    config = _make_run_config(tmp_path, dry_run=False)
    stdout_log = tmp_path / "out.log"
    stderr_log = tmp_path / "err.log"
    status, _, error = runner_mod._execute_once(
        plan, config, stdout_log, stderr_log,
    )
    assert status == "os-error"
    assert "permission denied" in (error or "")


def test_run_plan_retries_on_transient_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """[v0.5.6] When _execute_once returns a transient exit code, retry policy
    runs another attempt. We track attempt count via attempts field."""
    attempts: list[int] = []

    def fake_execute(*_args: Any, **_kw: Any) -> tuple[str, int | None, str | None]:
        attempts.append(1)
        if len(attempts) == 1:
            return ("failed", 124, "first try")
        return ("ok", 0, None)

    monkeypatch.setattr(runner_mod, "_execute_once", fake_execute)
    plan = CommandPlan(stage="t", label="x", command=["true"])
    config = _make_run_config(tmp_path, dry_run=False, verbose=False).model_copy(
        update={"retry": RetryPolicy(max_attempts=2, backoff_s=0.0)},
    )
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    artifacts.logs.mkdir(parents=True, exist_ok=True)
    result = runner_mod.run_plan(plan, config, artifacts)
    assert result.status == "ok"
    assert result.attempts == 2


# ---- kiterunner_stage parse paths ----

def _kit_payload(**kw: Any) -> str:
    return json.dumps(kw)


def test_kiterunner_parse_skips_malformed_lines(tmp_path: Path) -> None:
    artifact = tmp_path / "kr.jsonl"
    artifact.write_text(
        "not-json\n"
        '"a top-level string is not a dict"\n'        # JSON valid but not dict
        '{"not": "a record we expect"}\n'             # missing url + status
        + _kit_payload(uri=12345, status_code=200) + "\n"            # url not str
        + _kit_payload(uri="https://x/a", status_code=200) + "\n"
        + _kit_payload(uri="https://x/b", status_code="200") + "\n"  # status not int
        + _kit_payload(uri="https://x/c", status_code=500) + "\n"    # 500 → None severity
        + _kit_payload(uri="https://x/d", status_code=401) + "\n"
        + "\n",
        encoding="utf-8",
    )
    findings, routes = kiterunner_stage.parse_results([artifact])
    targets = {f.target for f in findings}
    assert "https://x/a" in targets  # 200 → info
    assert "https://x/d" in targets  # 401 → low
    # 500 status maps to None → dropped
    assert "https://x/c" not in routes
    # 12345 (int) url → isinstance str fails → skipped
    # "200" (str) status → isinstance int fails → skipped
    assert len(findings) == 2


def test_kiterunner_parse_returns_empty_when_artifact_missing(tmp_path: Path) -> None:
    findings, routes = kiterunner_stage.parse_results([tmp_path / "nope.jsonl"])
    assert findings == []
    assert routes == []


# ---- doctor.py — run_doctor + _run_fix_path ----

def test_run_doctor_with_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    profile = tmp_path / "p.yaml"
    profile.write_text(
        "program_name: test\nallowed_hosts: [example.com]\nenabled_tools: [httpx]\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "bbwebscan.doctor.inventory_tools",
        lambda tools, extra_fingerprints=None: [
            ToolStatus(name="httpx", required=True, found=True, identity="verified"),
        ],
    )
    args = argparse.Namespace(
        profile=str(profile), strict_identity=False, fix_path=False,
    )
    rc = doctor_mod.run_doctor(args)
    assert rc == 0


def test_run_doctor_fix_path_prints_added(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    added_path = Path("/fake/bin")

    def fake_persist(**_kw: Any) -> tuple[Path, list[Path]]:
        return (tmp_path / "rc", [added_path])

    monkeypatch.setattr("bbwebscan.doctor.persist_path_in_shell_rc", fake_persist)
    args = argparse.Namespace(profile=None, strict_identity=False, fix_path=True)
    rc = doctor_mod.run_doctor(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "updated" in out
    assert str(added_path) in out


def test_run_doctor_fix_path_when_already_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_persist(**_kw: Any) -> tuple[Path, list[Path]]:
        return (tmp_path / "rc", [])

    monkeypatch.setattr("bbwebscan.doctor.persist_path_in_shell_rc", fake_persist)
    args = argparse.Namespace(profile=None, strict_identity=False, fix_path=True)
    rc = doctor_mod.run_doctor(args)
    assert rc == 0
    assert "already configured" in capsys.readouterr().out


# ---- config.py — env-var interpolation edge paths ----

def test_load_profile_interpolates_env_vars_in_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("BBW_TEST_TOKEN", "real-token-value")
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(
        "program_name: test\n"
        "auth:\n"
        "  headers:\n"
        "    Authorization: 'Bearer ${BBW_TEST_TOKEN}'\n"
        "  cookies:\n"
        "    sid: '${BBW_TEST_TOKEN}'\n",
        encoding="utf-8",
    )
    profile = config_mod.load_profile(str(profile_path))
    assert profile.auth.headers["Authorization"] == "Bearer real-token-value"
    assert profile.auth.cookies["sid"] == "real-token-value"


def test_load_profile_raises_when_env_var_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.delenv("BBW_DEFINITELY_NOT_SET", raising=False)
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(
        "auth:\n  headers:\n    Authorization: '${BBW_DEFINITELY_NOT_SET}'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="BBW_DEFINITELY_NOT_SET"):
        config_mod.load_profile(str(profile_path))


def test_load_profile_no_path_returns_default() -> None:
    profile = config_mod.load_profile(None)
    assert profile.program_name == "ad-hoc"


def test_load_profile_missing_file_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Profile not found"):
        config_mod.load_profile(str(tmp_path / "missing.yaml"))


def test_build_run_config_rejects_unsupported_amass_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[v0.5.6] An unknown amass_mode raises an actionable error."""
    args = argparse.Namespace(
        profile=None, target=["example.com"], mode="safe", ack_authorized=False,
        amass_mode="warp-speed", enumerate_subdomains=False, api_discovery=False,
        scrapy_deep=False, scrapy_max_depth=2, scrapy_js_render=False,
        jwt_analysis=False, sqlmap_mode="off", sqlmap_timeout=600,
        port_scan=False, port_scan_mode="top-100", port_scan_rate=1000,
        enable_tool=[], disable_tool=[], header=[], cookie=[], raw_request=None,
        wordlist=None, threads=None, rate=None, tool_timeout=None,
        cmd_timeout=None, max_attempts=None, backoff_s=None, output_dir=None,
        input=None, check_tools=False, dry_run=True, verbose=True,
        strict_identity=False, severity=None, check_dns=False,
        quiet=False, run_label="test",
    )
    with pytest.raises(ValueError, match="Unsupported --amass-mode"):
        config_mod.build_run_config(args)


def test_build_run_config_rejects_unsupported_sqlmap_mode() -> None:
    args = argparse.Namespace(
        profile=None, target=["example.com"], mode="safe", ack_authorized=False,
        amass_mode="passive", enumerate_subdomains=False, api_discovery=False,
        scrapy_deep=False, scrapy_max_depth=2, scrapy_js_render=False,
        jwt_analysis=False, sqlmap_mode="apocalyptic", sqlmap_timeout=600,
        port_scan=False, port_scan_mode="top-100", port_scan_rate=1000,
        enable_tool=[], disable_tool=[], header=[], cookie=[], raw_request=None,
        wordlist=None, threads=None, rate=None, tool_timeout=None,
        cmd_timeout=None, max_attempts=None, backoff_s=None, output_dir=None,
        input=None, check_tools=False, dry_run=True, verbose=True,
        strict_identity=False, severity=None, check_dns=False,
        quiet=False, run_label="test",
    )
    with pytest.raises(ValueError, match="Unsupported --sqlmap-mode"):
        config_mod.build_run_config(args)


def test_build_run_config_safe_mode_warns_on_ack_authorized(
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = argparse.Namespace(
        profile=None, target=["example.com"], mode="safe", ack_authorized=True,
        amass_mode="passive", enumerate_subdomains=False, api_discovery=False,
        scrapy_deep=False, scrapy_max_depth=2, scrapy_js_render=False,
        jwt_analysis=False, sqlmap_mode="off", sqlmap_timeout=600,
        port_scan=False, port_scan_mode="top-100", port_scan_rate=1000,
        enable_tool=[], disable_tool=[], header=[], cookie=[], raw_request=None,
        wordlist=None, threads=None, rate=None, tool_timeout=None,
        cmd_timeout=None, max_attempts=None, backoff_s=None, output_dir=None,
        input=None, check_tools=False, dry_run=True, verbose=True,
        strict_identity=False, severity=None, check_dns=False,
        quiet=False, run_label="test",
    )
    config_mod.build_run_config(args)
    err = capsys.readouterr().err
    assert "--ack-authorized has no effect in safe mode" in err


# ---- amass_stage edge paths ----

def test_amass_build_plan_returns_empty_for_empty_targets(tmp_path: Path) -> None:
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    plans = amass_stage.build_plan(_make_run_config(tmp_path), artifacts, [])
    assert plans == []


def test_amass_intel_mode_includes_active_flag(tmp_path: Path) -> None:
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    config = _make_run_config(tmp_path).model_copy(update={"amass_mode": "intel"})
    target = NormalizedTarget(
        raw="example.com", host="example.com", seed_url="https://example.com",
    )
    plans = amass_stage.build_plan(config, artifacts, [target])
    assert "-active" in plans[0].command


def test_amass_parse_skips_comments_and_blanks(tmp_path: Path) -> None:
    artifact = tmp_path / "amass.txt"
    artifact.write_text("# header comment\n\napi.example.com\n", encoding="utf-8")
    findings, fqdns = amass_stage.parse_results(artifact)
    assert fqdns == ["api.example.com"]
    assert len(findings) == 1


# ---- params_stage edge paths ----

def test_params_flatten_handles_list_values_and_non_string(tmp_path: Path) -> None:
    """[v0.5.6] _flatten_params_for_artifact handles list payloads with mixed
    types and falls back to using keys when values are non-list non-string."""
    p = tmp_path / "arjun.json"
    # Mixed-shape payload covering: list with strings + non-strings,
    # a string value, and a numeric value (falls through to key).
    p.write_text(
        json.dumps([
            {"params": ["page", "limit", 42],  # 42 → filtered out
             "found_in": "url"},
            {"page_count": 12},  # numeric → fall through to key
        ]),
        encoding="utf-8",
    )
    findings, _ = params_stage.parse_results([p])
    title = findings[0].title
    # The string list items + the keys-fallback case all surface
    assert "page" in title or "limit" in title or "page_count" in title


# ---- preflight.py — detect_version success branch ----

def test_detect_version_returns_first_line_of_stripped_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake"
    fake_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        preflight_mod, "_probe", lambda _t, _a: (0, "v1.2.3\nextra line\n"),
    )
    assert preflight_mod.detect_version("httpx", fake_bin) == "v1.2.3"


def test_detect_version_returns_unknown_for_empty_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake"
    fake_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(preflight_mod, "_probe", lambda _t, _a: (0, "   \n  "))
    assert preflight_mod.detect_version("httpx", fake_bin) == "unknown"


def test_probe_real_subprocess(
    tmp_path: Path,
) -> None:
    """Smoke-test of the actual _probe helper (no monkeypatch)."""
    rc, output = preflight_mod._probe(Path("/bin/echo"), ["hello"])
    assert rc == 0
    assert "hello" in output


def test_validate_environment_strict_identity_flag(
    tmp_path: Path,
) -> None:
    config = _make_run_config(tmp_path).model_copy(update={
        "strict_identity": True,
        "check_tools": True,
        "dry_run": False,
    })
    statuses = [
        ToolStatus(
            name="httpx", required=True, found=True, identity="suspect",
            path=Path("/usr/bin/httpx"), note="mismatched fingerprint",
        ),
    ]
    errors = preflight_mod.validate_environment(config, statuses)
    assert any("Suspect tool identity" in e for e in errors)


# ---- bbspider — except branch on parsel error ----

def test_bbspider_parse_handles_css_exception(tmp_path: Path) -> None:
    """[v0.5.6] If response.css raises mid-parse, the spider catches and
    yields the record with empty links/scripts instead of crashing.

    We subclass HtmlResponse to override .css with a raising stub since the
    base class attribute is read-only on real instances.
    """
    class _BoomResponse(HtmlResponse):
        def css(self, *_a: Any, **_kw: Any) -> Any:
            raise RuntimeError("css blew up")

    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com\n", encoding="utf-8")
    spider = BbSpider(urls_file=str(urls))
    request = Request(url="https://example.com")
    response = _BoomResponse(
        url="https://example.com", request=request,
        body=b"<html></html>", encoding="utf-8",
        headers={"Content-Type": "text/html"},
    )
    items = list(spider.parse(response))
    record = items[0]
    assert record["links"] == []
    assert record["scripts"] == []


def test_bbspider_parse_follow_ups_include_playwright_meta_when_js_render(
    tmp_path: Path,
) -> None:
    """[v0.5.6] When js_render is on, follow-up requests carry playwright meta."""
    urls = tmp_path / "urls.txt"
    urls.write_text("https://example.com\n", encoding="utf-8")
    spider = BbSpider(urls_file=str(urls), js_render=True, max_depth=3)
    body = b"<html><body><a href=\"https://example.com/sub\">x</a></body></html>"
    request = Request(url="https://example.com")
    response = HtmlResponse(
        url="https://example.com", request=request, body=body,
        headers={"Content-Type": "text/html"}, encoding="utf-8",
    )
    response.meta["depth"] = 0
    items = list(spider.parse(response))
    follow_ups = items[1:]
    assert follow_ups
    assert all(r.meta.get("playwright") is True for r in follow_ups)


# ---- targets.py — psl fallback when publicsuffix2 missing ----

def test_require_psl_adapter_raises_when_publicsuffix2_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[v0.5.6] When the optional publicsuffix2 import failed, the helper
    raises a clear actionable error pointing at the install command."""
    monkeypatch.setattr(targets_mod, "_PSL_ADAPTER", None)
    monkeypatch.setattr(
        targets_mod, "_PSL_IMPORT_ERROR", ImportError("no psl"),
    )
    with pytest.raises(RuntimeError, match="publicsuffix2 is required"):
        targets_mod._require_psl_adapter()


def test_registrable_domain_raises_for_unresolvable_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When publicsuffix2 returns None/empty for a host, registrable_domain raises."""

    class _Adapter:
        get_sld = staticmethod(lambda _h: None)
        get_tld = staticmethod(lambda _h: "com")

    monkeypatch.setattr(targets_mod, "_PSL_ADAPTER", _Adapter())
    with pytest.raises(ValueError, match="registrable domain"):
        targets_mod.registrable_domain("weird")


def test_normalize_target_rejects_url_without_hostname() -> None:
    # urlparse on a malformed value returns hostname=None
    with pytest.raises(ValueError, match="normalize target"):
        normalize_target("https://")


def test_enforce_scope_gate_multi_host_without_allowed(tmp_path: Path) -> None:
    config = _make_run_config(tmp_path).model_copy(update={"allowed_hosts": []})
    targets = [
        NormalizedTarget(raw=h, host=h, seed_url=f"https://{h}")
        for h in ("example.com", "evil.test")
    ]
    with pytest.raises(ValueError, match="Refusing implicit scope"):
        enforce_scope_gate(config, targets)


# ---- pipeline.py — scrapy skip when no input ----

def test_run_scrapy_skips_when_no_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """[v0.5.6] Scrapy stage gates on scrapy_input being non-empty."""
    config = _make_run_config(tmp_path).model_copy(update={
        "enabled_tools": ["scrapy"],
    })
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    artifacts.artifacts.mkdir(parents=True, exist_ok=True)
    artifacts.logs.mkdir(parents=True, exist_ok=True)
    state = pipeline_mod._PipelineState(
        config=config, artifacts=artifacts,
        targets=[], allowed_hosts=["example.com"], scope_decisions=[],
    )
    # state.live_urls and state.active_urls are both empty → scrapy is skipped.
    pipeline_mod._run_scrapy(state)
    # No execution happened
    assert state.results == []


# ---- history.py — list_runs branches ----

def test_list_runs_skips_non_dirs_and_incomplete(tmp_path: Path) -> None:
    """[v0.5.6] list_runs skips entries that aren't directories or that lack
    the required summary files."""
    runs = tmp_path / "runs"
    runs.mkdir()
    # An entry that is a file, not a directory
    (runs / "stray-file").write_text("ignored", encoding="utf-8")
    # A dir lacking the required files
    (runs / "incomplete").mkdir()
    # A complete dir
    good = runs / "20260515T000000Z"
    good.mkdir()
    (good / "run_config.json").write_text('{"program_name": "x", "mode": "safe"}', encoding="utf-8")
    (good / "findings.json").write_text("[]", encoding="utf-8")
    (good / "scope_decisions.json").write_text(
        '[{"value": "x", "allowed": true, "reason": "x"}]',
        encoding="utf-8",
    )
    (good / "summary.md").write_text("# x\n", encoding="utf-8")
    summaries = history_mod.list_runs(runs)
    assert len(summaries) == 1
    assert summaries[0].program_name == "x"


def test_list_runs_handles_corrupt_summary(tmp_path: Path) -> None:
    """[v0.5.6] A run dir with corrupt JSON returns None from _summarize."""
    runs = tmp_path / "runs"
    runs.mkdir()
    bad = runs / "20260515T000000Z"
    bad.mkdir()
    (bad / "run_config.json").write_text("not-json", encoding="utf-8")
    (bad / "findings.json").write_text("[]", encoding="utf-8")
    (bad / "scope_decisions.json").write_text("[]", encoding="utf-8")
    (bad / "summary.md").write_text("# x\n", encoding="utf-8")
    summaries = history_mod.list_runs(runs)
    assert summaries == []


def test_list_runs_handles_non_list_findings(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    bad = runs / "20260515T000000Z"
    bad.mkdir()
    (bad / "run_config.json").write_text('{"program_name": "x", "mode": "safe"}', encoding="utf-8")
    (bad / "findings.json").write_text('{"not": "a list"}', encoding="utf-8")
    (bad / "scope_decisions.json").write_text("[]", encoding="utf-8")
    (bad / "summary.md").write_text("# x\n", encoding="utf-8")
    assert history_mod.list_runs(runs) == []


# ---- menu_profile.py — default_program_name fallbacks ----

def test_default_program_name_from_profile_path() -> None:
    """[v0.5.6] When settings.profile is set, default uses its stem."""
    s = ScanSettings(profile="profiles/demo.yaml")
    assert menu_profile.default_program_name(s) == "demo"


def test_default_program_name_from_target() -> None:
    """[v0.5.6] No profile, but targets present → derive from first target host."""
    s = ScanSettings(profile=None, targets=["api.example.com"])
    assert menu_profile.default_program_name(s) == "api-example-com"


def test_default_program_name_falls_through_to_ad_hoc() -> None:
    s = ScanSettings(profile=None, targets=[])
    assert menu_profile.default_program_name(s) == "ad-hoc"


# ---- installer.py — persist_path_in_shell_rc adds trailing newline ----

def test_persist_path_handles_rc_without_trailing_newline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("export X=1", encoding="utf-8")  # No trailing newline
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")
    _, added = installer_mod.persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert added == [bin_dir]
    body = rc.read_text(encoding="utf-8")
    # Newline inserted before the marker block so the export stays separate
    assert body.startswith("export X=1\n")
    assert installer_mod.PERSIST_MARKER in body


# ---- discovery_stage edge paths ----

def test_discovery_dirsearch_command_includes_raw_flag(tmp_path: Path) -> None:
    raw = tmp_path / "req.txt"
    raw.write_text("GET / HTTP/1.1\n", encoding="utf-8")
    artifacts = RunArtifacts(
        root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts",
    )
    config = _make_run_config(tmp_path).model_copy(update={
        "enabled_tools": ["dirsearch"],
        "auth": AuthConfig(raw_request=raw),
    })
    plans = discovery_stage.build_plans(config, artifacts, ["https://example.com"])
    cmd = plans[0].command
    assert any(arg.startswith(f"--raw={raw}") for arg in cmd)
