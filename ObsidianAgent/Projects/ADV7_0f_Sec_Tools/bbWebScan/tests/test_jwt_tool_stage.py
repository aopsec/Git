"""Tests for jwt_tool_stage module."""

from pathlib import Path

from bbwebscan.models import AuthConfig, RetryPolicy, RunArtifacts, RunConfig
from bbwebscan.stages import jwt_tool_stage


def _config_with_auth(tmp_path: Path, auth: AuthConfig) -> RunConfig:
    return RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=auth,
        mode="safe",
        enabled_tools=["jwt_tool"],
        wordlist=Path("/dev/null"),
        threads=4,
        rate=4,
        tool_timeout_s=1,
        command_wall_clock_s=60,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=[],
        dry_run=True,
        jwt_analysis=True,
    )


def _artifacts(tmp_path: Path) -> RunArtifacts:
    root = tmp_path / "run"
    logs = root / "logs"
    artifacts = root / "artifacts"
    logs.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    return RunArtifacts(root=root, logs=logs, artifacts=artifacts)


def test_build_plan_with_bearer_token(tmp_path: Path) -> None:
    """Test that build_plan creates a CommandPlan when Bearer token exists."""
    auth = AuthConfig(headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"})
    config = _config_with_auth(tmp_path, auth)
    artifacts = _artifacts(tmp_path)

    plan = jwt_tool_stage.build_plan(config, artifacts)
    assert plan is not None
    assert plan.stage == "jwt-analysis"
    assert plan.label == "jwt_tool"
    assert plan.command[0] == "jwt_tool"
    assert "-t" in plan.command
    token_idx = plan.command.index("-t") + 1
    assert plan.command[token_idx] == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    # [v0.5.5 sec-fix] The token slot must be marked for redaction so the
    # dry-run argv echo doesn't leak the bearer JWT to stdout / log files.
    assert plan.redact_indices == [token_idx]


def test_build_plan_with_no_auth(tmp_path: Path) -> None:
    """Test that build_plan returns None when no auth header exists."""
    auth = AuthConfig()
    config = _config_with_auth(tmp_path, auth)
    artifacts = _artifacts(tmp_path)

    plan = jwt_tool_stage.build_plan(config, artifacts)
    assert plan is None


def test_build_plan_with_empty_bearer(tmp_path: Path) -> None:
    """Test that build_plan returns None when Bearer token is empty."""
    auth = AuthConfig(headers={"Authorization": "Bearer "})
    config = _config_with_auth(tmp_path, auth)
    artifacts = _artifacts(tmp_path)

    plan = jwt_tool_stage.build_plan(config, artifacts)
    assert plan is None


def test_parse_results_with_valid_json(tmp_path: Path, fixtures_dir: Path) -> None:
    """Test parsing jwt_tool JSON output."""
    findings = jwt_tool_stage.parse_results(fixtures_dir / "jwt_tool.json")
    assert len(findings) > 0
    # Check that issues were parsed
    assert any(f.kind == "jwt-issue" for f in findings)
    assert any(f.severity == "critical" for f in findings)


def test_parse_results_with_missing_file(tmp_path: Path) -> None:
    """Test parsing when output file doesn't exist."""
    findings = jwt_tool_stage.parse_results(tmp_path / "nonexistent.json")
    assert findings == []


def test_parse_results_with_invalid_json(tmp_path: Path) -> None:
    """Test parsing with invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid json}")
    findings = jwt_tool_stage.parse_results(invalid_file)
    assert findings == []


def test_parse_results_with_no_issues(tmp_path: Path) -> None:
    """Test parsing when no issues are found."""
    report_file = tmp_path / "clean.json"
    report_file.write_text('{"token": "...", "issues": []}')
    findings = jwt_tool_stage.parse_results(report_file)
    assert findings == []
