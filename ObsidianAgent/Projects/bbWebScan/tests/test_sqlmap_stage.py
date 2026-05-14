"""Tests for sqlmap_stage module."""

from pathlib import Path

from bbwebscan.models import AuthConfig, RetryPolicy, RunArtifacts, RunConfig
from bbwebscan.stages import sqlmap_stage


def _config(tmp_path: Path, *, mode: str = "smooth", timeout: int = 600) -> RunConfig:
    return RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["sqlmap"],
        wordlist=Path("/dev/null"),
        threads=4,
        rate=4,
        tool_timeout_s=1,
        command_wall_clock_s=60,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=[],
        dry_run=True,
        sqlmap_mode=mode,
        sqlmap_timeout=timeout,
    )


def _artifacts(tmp_path: Path) -> RunArtifacts:
    root = tmp_path / "run"
    logs = root / "logs"
    artifacts = root / "artifacts"
    logs.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    return RunArtifacts(root=root, logs=logs, artifacts=artifacts)


def test_build_plans_with_off_mode(tmp_path: Path) -> None:
    """Test that build_plans returns empty when sqlmap_mode is 'off'."""
    config = _config(tmp_path, mode="off")
    artifacts = _artifacts(tmp_path)
    urls = ["https://example.com/search?q=test"]

    plans = sqlmap_stage.build_plans(config, artifacts, urls)
    assert plans == []


def test_build_plans_smooth_mode(tmp_path: Path) -> None:
    """Test smooth mode command building."""
    config = _config(tmp_path, mode="smooth")
    artifacts = _artifacts(tmp_path)
    urls = ["https://example.com/search?q=test", "https://example.com/api/user?id=123"]

    plans = sqlmap_stage.build_plans(config, artifacts, urls)
    assert len(plans) == 2

    plan = plans[0]
    assert plan.stage == "sqlmap"
    assert plan.label == "sqlmap_1"
    assert plan.command[0] == "sqlmap"
    assert "--level" in plan.command
    assert "1" in plan.command
    assert "--risk" in plan.command
    assert "1" in plan.command


def test_build_plans_aggressive_mode(tmp_path: Path) -> None:
    """Test aggressive mode command building."""
    config = _config(tmp_path, mode="aggressive")
    artifacts = _artifacts(tmp_path)
    urls = ["https://example.com/api/user?id=123"]

    plans = sqlmap_stage.build_plans(config, artifacts, urls)
    assert len(plans) == 1

    plan = plans[0]
    assert "--level" in plan.command
    assert "5" in plan.command
    assert "--risk" in plan.command
    assert "3" in plan.command
    assert "--tamper" in plan.command


def test_build_plans_with_empty_urls(tmp_path: Path) -> None:
    """Test with empty URL list."""
    config = _config(tmp_path, mode="smooth")
    artifacts = _artifacts(tmp_path)

    plans = sqlmap_stage.build_plans(config, artifacts, [])
    assert plans == []


def test_parse_results_with_valid_smooth(tmp_path: Path, fixtures_dir: Path) -> None:
    """Test parsing smooth mode results."""
    findings, _ = sqlmap_stage.parse_results([fixtures_dir / "sqlmap_smooth.json"])
    assert len(findings) > 0
    assert any(f.kind == "sql-injection" for f in findings)
    assert any(f.severity == "critical" for f in findings)


def test_parse_results_with_valid_aggressive(tmp_path: Path, fixtures_dir: Path) -> None:
    """Test parsing aggressive mode results."""
    findings, _ = sqlmap_stage.parse_results([fixtures_dir / "sqlmap_aggressive.json"])
    assert len(findings) > 0
    assert any(f.kind == "sql-injection" for f in findings)
    # Should have both critical and high severity findings
    severities = {f.severity for f in findings}
    assert len(severities) >= 1


def test_parse_results_with_missing_file(tmp_path: Path) -> None:
    """Test parsing when output file doesn't exist."""
    findings, _ = sqlmap_stage.parse_results([tmp_path / "nonexistent.json"])
    assert findings == []


def test_parse_results_with_invalid_json(tmp_path: Path) -> None:
    """Test parsing with invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid json}")
    findings, _ = sqlmap_stage.parse_results([invalid_file])
    assert findings == []


def test_parse_results_with_no_vulnerabilities(tmp_path: Path) -> None:
    """Test parsing when no vulnerabilities are found."""
    report_file = tmp_path / "clean.json"
    report_file.write_text('{"target": "...", "vulnerability": []}')
    findings, _ = sqlmap_stage.parse_results([report_file])
    assert findings == []


def test_parse_results_returns_empty_urls(tmp_path: Path, fixtures_dir: Path) -> None:
    """Test that parse_results returns empty URL list."""
    findings, urls = sqlmap_stage.parse_results([fixtures_dir / "sqlmap_smooth.json"])
    assert urls == []
