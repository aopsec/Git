import json
from pathlib import Path

import pytest

from bbwebscan import pipeline
from bbwebscan.models import (
    AuthConfig,
    CommandPlan,
    ExecutionResult,
    Finding,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
)
from bbwebscan.stages import (
    amass_stage,
    httpx_stage,
    katana_stage,
    kiterunner_stage,
    params_stage,
)


def _scan_config(tmp_path: Path, *, verbose: bool = True) -> RunConfig:
    return RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx"],
        wordlist=Path("/usr/share/dirb/wordlists/common.txt"),
        threads=5,
        rate=5,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["https://example.com"],
        dry_run=True,
        verbose=verbose,
    )


def test_execute_scan_writes_summary_for_missing_tools(tmp_path: Path) -> None:
    config = _scan_config(tmp_path)
    exit_code = pipeline.execute_scan(config)
    summary_path = config.output_dir / "summary.md"
    assert summary_path.is_file()
    summary = summary_path.read_text()
    assert "bbWebScan Summary" in summary
    # Either 0 (tools all present, dry-run) or 2 (missing tool errors).
    assert exit_code in {0, 2}
    if exit_code == 2:
        assert "Errors" in summary


def test_execute_scan_prints_closing_summary_when_verbose(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.2 (FIX-BBW-G): close the loop so operators don't `cd runs/` to find output."""
    pipeline.execute_scan(_scan_config(tmp_path, verbose=True))
    out = capsys.readouterr().out
    assert "[bbwebscan] scan complete" in out
    assert "scope decisions allowed" in out
    assert "[bbwebscan] artifacts:" in out
    assert str(tmp_path / "run") in out


def test_execute_scan_omits_closing_summary_when_quiet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    pipeline.execute_scan(_scan_config(tmp_path, verbose=False))
    out = capsys.readouterr().out
    assert "[bbwebscan] scan complete" not in out
    assert "[bbwebscan] artifacts:" not in out


def test_execute_scan_filters_crawled_urls_before_arjun(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_dir = tmp_path / "run"
    captured: dict[str, list[CommandPlan]] = {}

    def fake_run_plan(
        plan: CommandPlan, config: RunConfig, artifacts: RunArtifacts
    ) -> ExecutionResult:
        captured.setdefault(plan.stage, []).append(plan)
        return ExecutionResult(
            stage=plan.stage,
            label=plan.label,
            command=plan.command,
            status="dry-run",
            artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda config: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda config, statuses: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(
        httpx_stage,
        "parse_results",
        lambda output_file: ([], ["https://app.example.com"]),
    )
    monkeypatch.setattr(
        katana_stage,
        "parse_results",
        lambda output_file: (
            [],
            ["https://app.example.com/login", "https://accounts.google.com/o/oauth2"],
        ),
    )
    monkeypatch.setattr(params_stage, "parse_results", lambda artifact_paths: ([], []))

    config = RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx", "katana", "arjun"],
        wordlist=Path("/usr/share/dirb/wordlists/common.txt"),
        threads=5,
        rate=5,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(),
        output_dir=output_dir,
        target_inputs=["https://app.example.com"],
        dry_run=True,
    )

    assert pipeline.execute_scan(config) == 0
    arjun_urls = [
        plan.command[plan.command.index("-u") + 1]
        for plan in captured["params"]
    ]
    assert arjun_urls == ["https://app.example.com", "https://app.example.com/login"]

    decisions = json.loads((output_dir / "scope_decisions.json").read_text(encoding="utf-8"))
    assert {
        "allowed": False,
        "reason": "not-allowed",
        "value": "https://accounts.google.com/o/oauth2",
    } in decisions


def _patch_for_findings_test(
    monkeypatch: pytest.MonkeyPatch, severities: list[str],
) -> None:
    """Wire pipeline so it produces a synthetic finding per severity in the list."""
    def fake_run_plan(plan, config, artifacts):  # type: ignore[no-untyped-def]
        return ExecutionResult(
            stage=plan.stage,
            label=plan.label,
            command=plan.command,
            status="dry-run",
            artifacts=plan.artifacts,
        )

    fakes = [
        Finding(
            stage="test", kind="synthetic", target=f"https://example.com/{i}",
            severity=sev, title=f"synthetic {sev}", evidence="test",
        )
        for i, sev in enumerate(severities)
    ]
    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda config: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda config, statuses: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _p: (fakes, []))
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(params_stage, "parse_results", lambda _p: ([], []))


def _severity_config(tmp_path: Path, min_severity: str) -> RunConfig:
    config = _scan_config(tmp_path)
    return config.model_copy(update={"min_severity": min_severity})


def test_findings_filtered_by_min_severity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 5): findings.json only contains items at or above threshold."""
    _patch_for_findings_test(monkeypatch, ["info", "low", "medium", "high"])
    config = _severity_config(tmp_path, "medium")
    pipeline.execute_scan(config)
    findings = json.loads((config.output_dir / "findings.json").read_text())
    severities = [f["severity"] for f in findings]
    assert "info" not in severities
    assert "low" not in severities
    assert "medium" in severities
    assert "high" in severities


def test_exit_code_3_when_threshold_findings_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 5): exit 3 when findings ≥ min_severity exist (CI gating)."""
    _patch_for_findings_test(monkeypatch, ["high"])
    config = _severity_config(tmp_path, "high")
    assert pipeline.execute_scan(config) == 3


def test_exit_code_0_when_no_findings_meet_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 5): exit 0 when all findings filtered out."""
    _patch_for_findings_test(monkeypatch, ["info", "low"])
    config = _severity_config(tmp_path, "high")
    assert pipeline.execute_scan(config) == 0


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [("failed", 1), ("timeout", 124), ("missing-binary", None)],
)
def test_runtime_stage_failure_returns_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    exit_code: int | None,
) -> None:
    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        return ExecutionResult(
            stage=plan.stage,
            label=plan.label,
            command=plan.command,
            status=status,
            exit_code=exit_code,
            error=f"{status} during test",
            artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _config: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _config, _statuses: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _path: ([], []))

    config = _scan_config(tmp_path).model_copy(update={"dry_run": False})

    assert pipeline.execute_scan(config) == 2
    summary = (config.output_dir / "summary.md").read_text(encoding="utf-8")
    assert f"Execution failed: httpx/httpx status={status}" in summary


def test_disabled_core_stages_are_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    captured_stages: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        captured_stages.append(plan.stage)
        return ExecutionResult(
            stage=plan.stage,
            label=plan.label,
            command=plan.command,
            status="dry-run",
            artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _config: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _config, _statuses: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)

    config = _scan_config(tmp_path).model_copy(update={"enabled_tools": []})

    assert pipeline.execute_scan(config) == 0
    assert captured_stages == []


def test_closing_summary_includes_severity_breakdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_for_findings_test(monkeypatch, ["medium", "high", "high"])
    config = _severity_config(tmp_path, "info")
    pipeline.execute_scan(config)
    out = capsys.readouterr().out
    assert "[bbwebscan] scan complete — 3 findings" in out
    assert "medium=1" in out
    assert "high=2" in out


def test_dns_preflight_appends_note_for_unresolvable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 8): when --check-dns is set, unresolvable hosts get a non-fatal
    note in summary.md and the run continues (exit code unchanged)."""
    monkeypatch.setattr(pipeline, "resolve_host", lambda _h: None)
    config = _scan_config(tmp_path).model_copy(update={"preflight_dns": True})
    rc = pipeline.execute_scan(config)
    summary = (config.output_dir / "summary.md").read_text(encoding="utf-8")
    assert "did not resolve via DNS" in summary
    # Exit code is decided by errors/findings, NOT by DNS notes.
    assert rc in {0, 2}  # 2 only if a missing tool blocked the run


def test_dns_preflight_silent_when_resolves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(pipeline, "resolve_host", lambda _h: "93.184.216.34")
    config = _scan_config(tmp_path).model_copy(update={"preflight_dns": True})
    pipeline.execute_scan(config)
    summary = (config.output_dir / "summary.md").read_text(encoding="utf-8")
    assert "did not resolve via DNS" not in summary


# ---- v0.5.0 amass + kiterunner pipeline integration ----

def test_amass_runs_before_httpx_when_enabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.5.0 Item 5: amass plans build before httpx plans when --enumerate-subdomains.
    Verified by ordering of stages in the captured plan list."""

    captured_stages: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        captured_stages.append(plan.stage)
        return ExecutionResult(
            stage=plan.stage, label=plan.label, command=plan.command,
            status="dry-run", artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _c: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _c, _s: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(amass_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))

    config = _scan_config(tmp_path).model_copy(
        update={"enumerate_subdomains": True, "enabled_tools": ["httpx", "amass"]}
    )
    pipeline.execute_scan(config)
    # First stage seen must be amass; httpx must follow.
    assert captured_stages[0] == "amass"
    assert "httpx" in captured_stages
    assert captured_stages.index("amass") < captured_stages.index("httpx")


def test_amass_subdomains_filtered_by_scope_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.5.0 Item 5: amass-discovered FQDNs must pass enforce_scope_gate.
    An out-of-scope FQDN gets a Rejected scope decision and never reaches httpx."""

    httpx_targets: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        return ExecutionResult(
            stage=plan.stage, label=plan.label, command=plan.command,
            status="dry-run", artifacts=plan.artifacts,
        )

    def fake_httpx_build_plan(_config, _arts, targets):  # type: ignore[no-untyped-def]
        httpx_targets.extend(t.host for t in targets)
        return []

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _c: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _c, _s: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    # amass returns one in-scope FQDN + one out-of-scope FQDN
    monkeypatch.setattr(
        amass_stage, "parse_results",
        lambda _p: ([], ["api.example.com", "evil.attacker.test"]),
    )
    monkeypatch.setattr(httpx_stage, "build_plan", fake_httpx_build_plan)
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))

    config = _scan_config(tmp_path).model_copy(
        update={"enumerate_subdomains": True, "enabled_tools": ["httpx", "amass"]}
    )
    pipeline.execute_scan(config)
    # In-scope target reaches httpx; out-of-scope is filtered.
    assert "api.example.com" in httpx_targets
    assert "evil.attacker.test" not in httpx_targets
    # Out-of-scope FQDN recorded in scope_decisions.json as rejected
    decisions = json.loads(
        (config.output_dir / "scope_decisions.json").read_text(encoding="utf-8")
    )
    rejected_values = {d["value"] for d in decisions if not d["allowed"]}
    assert "evil.attacker.test" in rejected_values


def test_kiterunner_runs_in_discovery_when_api_flag_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.5.0 Item 5: kiterunner builds plans inside the discovery phase
    when --api-discovery is set; absent when not."""
    captured_labels: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        captured_labels.append(plan.label)
        return ExecutionResult(
            stage=plan.stage, label=plan.label, command=plan.command,
            status="dry-run", artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _c: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _c, _s: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(
        httpx_stage, "parse_results",
        lambda _p: ([], ["https://app.example.com"]),
    )
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))
    monkeypatch.setattr(kiterunner_stage, "parse_results", lambda _p: ([], []))

    config = _scan_config(tmp_path).model_copy(
        update={"api_discovery": True, "enabled_tools": ["httpx", "kiterunner"]}
    )
    pipeline.execute_scan(config)
    assert any(label.startswith("kiterunner_") for label in captured_labels)


def test_kiterunner_skipped_when_api_flag_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:

    captured_labels: list[str] = []

    def fake_run_plan(
        plan: CommandPlan, _config: RunConfig, _arts: RunArtifacts,
    ) -> ExecutionResult:
        captured_labels.append(plan.label)
        return ExecutionResult(
            stage=plan.stage, label=plan.label, command=plan.command,
            status="dry-run", artifacts=plan.artifacts,
        )

    monkeypatch.setattr(pipeline, "collect_tool_inventory", lambda _c: [])
    monkeypatch.setattr(pipeline, "validate_environment", lambda _c, _s: [])
    monkeypatch.setattr(pipeline, "run_plan", fake_run_plan)
    monkeypatch.setattr(httpx_stage, "parse_results", lambda _p: ([], ["https://x"]))
    monkeypatch.setattr(katana_stage, "parse_results", lambda _p: ([], []))

    config = _scan_config(tmp_path)  # api_discovery=False default
    pipeline.execute_scan(config)
    assert not any(label.startswith("kiterunner_") for label in captured_labels)
