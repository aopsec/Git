"""Tests for bbwebscan.reporting_professional."""
from __future__ import annotations

import json
from pathlib import Path

from bbwebscan.models import (
    AuthConfig,
    ExecutionResult,
    Finding,
    RetryPolicy,
    RunConfig,
    ScopeDecision,
    ToolStatus,
)
from bbwebscan.reporting_professional import (
    _detect_php_findings,
    _risk_rating,
    _severity_breakdown,
    generate_professional_report,
)


def _make_finding(
    severity: str = "info",
    kind: str = "crawl",
    stage: str = "scrapy",
    target: str = "https://example.com",
    title: str = "Test finding",
) -> Finding:
    return Finding(
        stage=stage,
        kind=kind,
        target=target,
        severity=severity,
        title=title,
        evidence="n/a",
    )


def _make_config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        program_name="test-prog",
        seed_urls=["https://example.com"],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx", "scrapy"],
        wordlist=Path("/dev/null"),
        threads=4,
        rate=10,
        tool_timeout_s=10,
        command_wall_clock_s=60,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["example.com"],
    )


def _make_status(name: str = "httpx", found: bool = True) -> ToolStatus:
    return ToolStatus(name=name, required=True, found=found)


def _make_result(
    stage: str = "httpx",
    label: str = "httpx",
    status: str = "ok",
    exit_code: int = 0,
) -> ExecutionResult:
    return ExecutionResult(
        stage=stage,
        label=label,
        command=["httpx"],
        status=status,
        exit_code=exit_code,
    )


# ── _risk_rating ──────────────────────────────────────────────────────────────

class TestRiskRating:
    def test_empty_returns_informational(self) -> None:
        assert _risk_rating([]) == "Informational"

    def test_info_only_returns_informational(self) -> None:
        findings = [_make_finding("info"), _make_finding("info")]
        assert _risk_rating(findings) == "Informational"

    def test_mixed_returns_highest(self) -> None:
        findings = [
            _make_finding("info"),
            _make_finding("medium"),
            _make_finding("low"),
        ]
        assert _risk_rating(findings) == "Medium"

    def test_critical_dominates(self) -> None:
        findings = [
            _make_finding("low"),
            _make_finding("critical"),
            _make_finding("high"),
        ]
        assert _risk_rating(findings) == "Critical"

    def test_high_single(self) -> None:
        assert _risk_rating([_make_finding("high")]) == "High"


# ── _severity_breakdown ───────────────────────────────────────────────────────

class TestSeverityBreakdown:
    def test_empty(self) -> None:
        assert _severity_breakdown([]) == {}

    def test_correct_counts(self) -> None:
        findings = [
            _make_finding("high"),
            _make_finding("high"),
            _make_finding("medium"),
            _make_finding("info"),
        ]
        result = _severity_breakdown(findings)
        assert result["high"] == 2
        assert result["medium"] == 1
        assert result["info"] == 1
        assert result.get("low", 0) == 0


# ── generate_professional_report ──────────────────────────────────────────────

class TestGenerateProfessionalReport:
    def _run(
        self,
        tmp_path: Path,
        findings: list[Finding] | None = None,
        statuses: list[ToolStatus] | None = None,
        results: list[ExecutionResult] | None = None,
        scope_decisions: list[ScopeDecision] | None = None,
    ) -> Path:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        config = _make_config(tmp_path)
        return generate_professional_report(
            run_dir,
            config,
            findings or [],
            statuses or [_make_status()],
            results or [_make_result()],
            scope_decisions or [],
        )

    def test_file_created(self, tmp_path: Path) -> None:
        path = self._run(tmp_path)
        assert path.exists()
        assert path.name == "report_professional.md"

    def test_contains_executive_summary(self, tmp_path: Path) -> None:
        path = self._run(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "## Executive Summary" in content

    def test_contains_findings_section(self, tmp_path: Path) -> None:
        path = self._run(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "## Findings" in content

    def test_contains_appendix(self, tmp_path: Path) -> None:
        path = self._run(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "## Appendix" in content

    def test_cwe89_for_sql_injection(self, tmp_path: Path) -> None:
        finding = _make_finding(
            severity="high",
            kind="sql-injection",
            title="SQL injection detected",
        )
        path = self._run(tmp_path, findings=[finding])
        content = path.read_text(encoding="utf-8")
        assert "CWE-89" in content

    def test_no_findings_message(self, tmp_path: Path) -> None:
        path = self._run(tmp_path, findings=[])
        content = path.read_text(encoding="utf-8")
        assert "No findings collected." in content

    def test_scope_rejected_appears(self, tmp_path: Path) -> None:
        decisions = [
            ScopeDecision(value="https://evil.com", allowed=False, reason="out-of-scope"),
        ]
        path = self._run(tmp_path, scope_decisions=decisions)
        content = path.read_text(encoding="utf-8")
        assert "evil.com" in content

    def test_stage_summary_ok(self, tmp_path: Path) -> None:
        path = self._run(tmp_path, results=[_make_result(status="ok")])
        content = path.read_text(encoding="utf-8")
        assert "Stage Execution Summary" in content
        assert "[OK]" in content

    def test_failed_stage_shows_fail(self, tmp_path: Path) -> None:
        path = self._run(tmp_path, results=[_make_result(status="error", exit_code=1)])
        content = path.read_text(encoding="utf-8")
        assert "[FAIL]" in content


# ── PHP version detection ─────────────────────────────────────────────────────

class TestPhpDetection:
    def _write_httpx(
        self, artifacts: Path, powered_by: str, url: str = "https://example.com",
    ) -> None:
        artifacts.mkdir(parents=True, exist_ok=True)
        record = {"url": url, "response_headers": {"x-powered-by": powered_by}}
        (artifacts / "httpx.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")

    def test_php7_detection(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_httpx(run_dir / "artifacts", "PHP/7.4.3")
        config = _make_config(tmp_path)
        path = generate_professional_report(
            run_dir, config, [], [_make_status()], [], [],
        )
        content = path.read_text(encoding="utf-8")
        assert "CWE-1104" in content
        assert "CVE-2021-21707" in content
        assert "PHP/7.4.3" in content

    def test_php8_detection(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_httpx(run_dir / "artifacts", "PHP/8.1.0")
        config = _make_config(tmp_path)
        path = generate_professional_report(
            run_dir, config, [], [_make_status()], [], [],
        )
        content = path.read_text(encoding="utf-8")
        assert "CWE-1104" in content
        assert "CVE-2022-31625" in content

    def test_no_httpx_file(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        config = _make_config(tmp_path)
        path = generate_professional_report(
            run_dir, config, [], [_make_status()], [], [],
        )
        content = path.read_text(encoding="utf-8")
        # No PHP section when no httpx.jsonl
        assert "PHP Version Disclosure" not in content

    def test_no_php_header(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        self._write_httpx(run_dir / "artifacts", "Express")
        config = _make_config(tmp_path)
        path = generate_professional_report(
            run_dir, config, [], [_make_status()], [], [],
        )
        content = path.read_text(encoding="utf-8")
        assert "PHP Version Disclosure" not in content

    def test_invalid_json_line_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        # Mix bad JSON with valid PHP record
        (artifacts / "httpx.jsonl").write_text(
            "not-json\n"
            + json.dumps({"url": "https://x.com", "response_headers": {"x-powered-by": "PHP/7.4"}})
            + "\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        assert "CWE-1104" in content

    def test_blank_lines_in_httpx_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        record = {"url": "https://x.com", "response_headers": {"x-powered-by": "PHP/7.2"}}
        (artifacts / "httpx.jsonl").write_text(
            "\n\n" + json.dumps(record) + "\n\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        assert "CWE-1104" in content

    def test_non_dict_headers_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "httpx.jsonl").write_text(
            json.dumps({"url": "https://x.com", "response_headers": "not-a-dict"}) + "\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        assert "PHP Version Disclosure" not in content

    def test_oserror_on_httpx_read_returns_no_php_section(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        # Make httpx.jsonl a directory so read_text raises IsADirectoryError (subclass of OSError)
        (artifacts / "httpx.jsonl").mkdir()
        result = _detect_php_findings(run_dir)
        assert result == []

    def test_non_str_powered_by_skipped(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "httpx.jsonl").write_text(
            json.dumps({"url": "https://x.com", "response_headers": {"x-powered-by": 42}}) + "\n",
            encoding="utf-8",
        )
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        assert "PHP Version Disclosure" not in content


# ── findings with no CWE (crawl/inventory kinds) ─────────────────────────────

class TestFindingsNoCwe:
    def test_crawl_kind_no_cwe_in_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        finding = _make_finding(severity="info", kind="crawl", title="Scrapy crawled 5 URLs")
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [finding], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        # crawl kind has no CWE — must not inject a None CWE line
        assert "**CWE**: None" not in content
        # but the finding title should appear
        assert "Scrapy crawled 5 URLs" in content

    def test_unknown_kind_no_cwe(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        finding = _make_finding(severity="info", kind="unknown-kind", title="Mystery")
        config = _make_config(tmp_path)
        path = generate_professional_report(run_dir, config, [finding], [_make_status()], [], [])
        content = path.read_text(encoding="utf-8")
        assert "**CWE**: None" not in content
