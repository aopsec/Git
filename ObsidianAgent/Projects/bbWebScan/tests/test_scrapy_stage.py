from __future__ import annotations

from pathlib import Path

from bbwebscan.models import (
    AuthConfig,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
)
from bbwebscan.stages import scrapy_stage


def _config(tmp_path: Path, *, deep: bool = False, depth: int = 2, js: bool = False) -> RunConfig:
    return RunConfig(
        program_name="t",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["scrapy"],
        wordlist=Path("/dev/null"),
        threads=4,
        rate=4,
        tool_timeout_s=1,
        command_wall_clock_s=60,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["https://app.example.com"],
        dry_run=True,
        scrapy_deep=deep,
        scrapy_max_depth=depth,
        scrapy_js_render=js,
    )


def _artifacts(tmp_path: Path) -> RunArtifacts:
    root = tmp_path / "run"
    logs = root / "logs"
    artifacts = root / "artifacts"
    logs.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    return RunArtifacts(root=root, logs=logs, artifacts=artifacts)


def test_build_plan_emits_scrapy_runspider_invocation(tmp_path: Path) -> None:
    config = _config(tmp_path, deep=True, depth=3, js=True)
    artifacts = _artifacts(tmp_path)
    plans = scrapy_stage.build_plan(config, artifacts, ["https://app.example.com"])

    assert len(plans) == 1
    plan = plans[0]
    assert plan.stage == "scrapy"
    assert plan.label == "scrapy"
    # [FIX-V2] command[0] is now the venv-relative scrapy binary path, not "scrapy"
    assert plan.command[0].endswith("scrapy")
    assert plan.command[1] == "runspider"
    # spider file path passed positionally
    assert plan.command[2].endswith("bbspider.py")
    assert "-O" in plan.command
    output_idx = plan.command.index("-O") + 1
    assert plan.command[output_idx].endswith("scrapy.jsonl")
    # all -a kwargs present
    a_values = [
        plan.command[i + 1] for i, value in enumerate(plan.command)
        if value == "-a"
    ]
    assert any(arg.startswith("urls_file=") for arg in a_values)
    assert "max_depth=3" in a_values
    assert "deep_mode=1" in a_values
    assert "js_render=1" in a_values
    # targets file written
    targets_file = artifacts.artifacts / "scrapy_targets.txt"
    assert targets_file.is_file()
    assert targets_file.read_text().strip() == "https://app.example.com"


def test_build_plan_defaults_when_flags_off(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifacts = _artifacts(tmp_path)
    plans = scrapy_stage.build_plan(config, artifacts, ["https://example.com"])
    a_values = [
        plans[0].command[i + 1] for i, value in enumerate(plans[0].command)
        if value == "-a"
    ]
    assert "deep_mode=0" in a_values
    assert "js_render=0" in a_values
    assert "max_depth=2" in a_values


def test_parse_results_summary_and_severity_tiers(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "scrapy.jsonl"
    findings, urls = scrapy_stage.parse_results(fixture)

    # URLs include both .url and .links from every record
    assert "https://app.example.com/" in urls
    assert "https://app.example.com/team" in urls
    assert "https://app.example.com/cv.pdf" in urls

    severities = {f.severity for f in findings}
    kinds = {f.kind for f in findings}
    assert "crawl" in kinds
    assert "info-disclosure-email" in kinds
    assert "exposed-document" in kinds
    assert "exposed-path" in kinds
    assert "exposed-secret" in kinds
    # severity ladder enforced
    assert "info" in severities
    assert "low" in severities  # documents
    assert "medium" in severities  # exposed paths
    assert "high" in severities  # AWS key (confidence=high)


def test_parse_results_never_persists_raw_secret_value(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "scrapy.jsonl"
    findings, _ = scrapy_stage.parse_results(fixture)
    # The fixture's hashed digest:
    digest_prefix = "0123456789abcdef"
    # Evidence field MUST be sha256: prefix form, never an AKIA value.
    for finding in findings:
        assert "AKIA" not in finding.evidence
        assert "AKIA" not in finding.title
        assert "AKIA" not in finding.target
    secret_findings = [f for f in findings if f.kind == "exposed-secret"]
    assert secret_findings
    assert all(digest_prefix in f.evidence for f in secret_findings)
    assert all(f.evidence.startswith("sha256:") for f in secret_findings)


def test_parse_results_dedups_secret_hits(tmp_path: Path) -> None:
    """Same (name, sha256) pair should only emit one Finding."""
    duplicate_fixture = tmp_path / "scrapy.jsonl"
    duplicate_fixture.write_text(
        '{"url":"https://app.example.com/a","status":200,"title":"","links":[],'
        '"scripts":[],"documents":[],"emails":[],"exposed_paths":[],'
        '"secrets":[{"name":"x","confidence":"high","evidence_sha256":"abc",'
        '"source_url":"https://app.example.com/a"}]}\n'
        '{"url":"https://app.example.com/b","status":200,"title":"","links":[],'
        '"scripts":[],"documents":[],"emails":[],"exposed_paths":[],'
        '"secrets":[{"name":"x","confidence":"high","evidence_sha256":"abc",'
        '"source_url":"https://app.example.com/b"}]}\n',
        encoding="utf-8",
    )
    findings, _ = scrapy_stage.parse_results(duplicate_fixture)
    secret_findings = [f for f in findings if f.kind == "exposed-secret"]
    assert len(secret_findings) == 1
