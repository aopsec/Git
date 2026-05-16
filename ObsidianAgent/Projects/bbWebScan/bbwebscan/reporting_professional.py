"""Professional security assessment report generator.

Produces a structured .md report with CWE/CVE references after every scan.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from bbwebscan.models import (
    ExecutionResult,
    Finding,
    RunConfig,
    ScopeDecision,
    ToolStatus,
)

# CWE/OWASP/CVE reference table keyed by Finding.kind
FINDING_CWE_MAP: dict[str, tuple[str | None, str | None, str | None]] = {
    "sql-injection": (
        "CWE-89", "A03:2021 - Injection", "CVE-2022-21664, CVE-2022-22965",
    ),
    "exposed-secret": (
        "CWE-312", "A02:2021 - Cryptographic Failures", "CVE-2021-41091",
    ),
    "exposed-document": (
        "CWE-538", "A01:2021 - Broken Access Control", "-",
    ),
    "exposed-path": (
        "CWE-538", "A01:2021 - Broken Access Control", "-",
    ),
    "info-disclosure-email": (
        "CWE-359", "A02:2021 - Cryptographic Failures", "-",
    ),
    "xss": (
        "CWE-79", "A03:2021 - Injection", "CVE-2021-40438",
    ),
    "open-redirect": (
        "CWE-601", "A01:2021 - Broken Access Control", "-",
    ),
    "api-route": (
        "CWE-285", "A01:2021 - Broken Access Control", "-",
    ),
    "jwt-finding": (
        "CWE-347", "A02:2021 - Cryptographic Failures", "CVE-2022-21449",
    ),
    "nuclei-finding": (
        "CWE-200", "A05:2021 - Security Misconfiguration", "-",
    ),
    "amass-finding": (
        "CWE-200", "A05:2021 - Security Misconfiguration", "-",
    ),
    "port-open": (
        "CWE-200", "A05:2021 - Security Misconfiguration", "-",
    ),
    "crawl":     (None, None, None),
    "inventory": (None, None, None),
}

_PHP_VERSION_CVES: list[tuple[str, list[str]]] = [
    ("PHP/7.", ["CVE-2021-21707", "CVE-2021-21709", "CVE-2022-31625", "CVE-2022-31626"]),
    ("PHP/8.", ["CVE-2022-31625", "CVE-2022-31626"]),
]


def generate_professional_report(  # noqa: PLR0913 - report assembly requires all scan artifacts
    run_dir: Path,
    config: RunConfig,
    findings: list[Finding],
    statuses: list[ToolStatus],
    results: list[ExecutionResult],
    scope_decisions: list[ScopeDecision],
) -> Path:
    """Generate professional .md report and write to run_dir/report_professional.md."""
    out_path = run_dir / "report_professional.md"
    lines: list[str] = []
    lines.extend(_format_header(config, findings, scope_decisions))
    lines.extend(_format_findings_section(findings))
    php_lines = _detect_php_findings(run_dir)
    if php_lines:
        lines.extend(php_lines)
    lines.extend(_format_stage_summary(results, statuses))
    lines.extend(_format_scope_section(scope_decisions))
    lines.extend(_format_appendix())
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _risk_rating(findings: list[Finding]) -> str:
    """Return overall risk level from highest severity finding."""
    if not findings:
        return "Informational"
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    max_sev = max(findings, key=lambda f: severity_rank.get(f.severity, 0)).severity
    return {
        "critical": "Critical",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "info": "Informational",
    }.get(max_sev, "Informational")


def _severity_breakdown(findings: list[Finding]) -> dict[str, int]:
    """Count findings per severity."""
    counts: Counter[str] = Counter(f.severity for f in findings)
    return dict(counts)


def _format_header(
    config: RunConfig,
    findings: list[Finding],
    scope_decisions: list[ScopeDecision],
) -> list[str]:
    allowed = sum(1 for d in scope_decisions if d.allowed)
    total = len(scope_decisions)
    breakdown = _severity_breakdown(findings)
    sev_parts = [
        f"{sev}: {breakdown[sev]}"
        for sev in ("critical", "high", "medium", "low", "info")
        if breakdown.get(sev, 0) > 0
    ]
    sev_str = ", ".join(sev_parts) if sev_parts else "none"
    target_str = (
        ", ".join(config.target_inputs)
        if config.target_inputs
        else ", ".join(config.seed_urls)
    )
    return [
        "# Security Assessment Report",
        "",
        "## Executive Summary",
        "",
        f"- **Target**: {target_str}",
        f"- **Program**: {config.program_name}",
        f"- **Scan Mode**: {config.mode}",
        f"- **Overall Risk Rating**: {_risk_rating(findings)}",
        f"- **Total Findings**: {len(findings)} ({sev_str})",
        f"- **Scope**: {allowed}/{total} decisions allowed",
        f"- **Tools Used**: {', '.join(config.enabled_tools)}",
        "",
    ]


def _format_findings_section(findings: list[Finding]) -> list[str]:
    """Format each finding with CWE/CVE references."""
    lines: list[str] = ["## Findings", ""]
    if not findings:
        lines.append("No findings collected.")
        lines.append("")
        return lines
    for i, finding in enumerate(findings, 1):
        cwe, owasp, cves = FINDING_CWE_MAP.get(finding.kind, (None, None, None))
        lines.append(f"### {i}. [{finding.severity.upper()}] {finding.title}")
        lines.append("")
        lines.append(f"- **Stage**: {finding.stage}")
        lines.append(f"- **Kind**: {finding.kind}")
        lines.append(f"- **Target**: `{finding.target}`")
        lines.append(f"- **Severity**: {finding.severity}")
        if cwe:
            lines.append(f"- **CWE**: {cwe}")
        if owasp:
            lines.append(f"- **OWASP**: {owasp}")
        if cves:
            lines.append(f"- **Reference CVEs**: {cves}")
        lines.append(f"- **Evidence**: `{finding.evidence}`")
        lines.append("")
    return lines


def _detect_php_findings(run_dir: Path) -> list[str]:  # noqa: PLR0912
    """Read httpx.jsonl and detect PHP version from X-Powered-By headers."""
    httpx_file = run_dir / "artifacts" / "httpx.jsonl"
    if not httpx_file.is_file():
        return []
    php_hits: list[tuple[str, str]] = []
    try:
        for raw_line in httpx_file.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            url = record.get("url", "")
            headers = record.get("response_headers", record.get("headers", {}))
            if not isinstance(headers, dict):
                continue
            powered_by = headers.get("x-powered-by") or headers.get("X-Powered-By", "")
            if not isinstance(powered_by, str):
                continue
            for php_prefix, _cves in _PHP_VERSION_CVES:
                if php_prefix.lower() in powered_by.lower():
                    php_hits.append((url, powered_by))
                    break
    except OSError:  # pragma: no cover — IsADirectoryError path; tested but coverage misses it
        return []
    if not php_hits:
        return []
    lines: list[str] = [
        "## PHP Version Disclosure",
        "",
        "Outdated PHP version detected via `X-Powered-By` header (CWE-1104).",
        "",
    ]
    for url, version in php_hits:
        relevant_cves: list[str] = []
        for php_prefix, cves in _PHP_VERSION_CVES:  # pragma: no branch
            if php_prefix.lower() in version.lower():
                relevant_cves = cves
                break
        lines.append(f"- **Target**: `{url}` — `{version}`")
        lines.append("  - **CWE**: CWE-1104 (Use of Unmaintained Third-Party Components)")
        lines.append(f"  - **CVEs**: {', '.join(relevant_cves)}")
        lines.append("")
    return lines


def _format_stage_summary(
    results: list[ExecutionResult],
    statuses: list[ToolStatus],
) -> list[str]:
    lines: list[str] = ["## Stage Execution Summary", ""]
    if results:
        for result in results:
            icon = "OK" if result.status in {"ok", "dry-run"} else "FAIL"
            lines.append(
                f"- [{icon}] `{result.label}`: status=`{result.status}` "
                f"attempts={result.attempts} exit={result.exit_code}"
            )
    else:
        lines.append("No stages executed.")
    lines.append("")
    lines.append("### Tool Inventory")
    lines.append("")
    for status in statuses:
        found_str = "found" if status.found else "missing"
        lines.append(f"- `{status.name}`: {found_str} ({status.path or 'n/a'})")
    lines.append("")
    return lines


def _format_scope_section(scope_decisions: list[ScopeDecision]) -> list[str]:
    lines: list[str] = ["## Scope Decisions", ""]
    allowed = [d for d in scope_decisions if d.allowed]
    rejected = [d for d in scope_decisions if not d.allowed]
    lines.append(f"- Allowed: {len(allowed)}")
    lines.append(f"- Rejected: {len(rejected)}")
    if rejected:
        lines.append("")
        lines.append("### Out-of-Scope Rejections")
        lines.append("")
        for d in rejected[:20]:
            lines.append(f"- `{d.value}` — {d.reason}")
    lines.append("")
    return lines


def _format_appendix() -> list[str]:
    """Static CWE/CVE reference table."""
    lines: list[str] = [
        "## Appendix",
        "",
        "### CWE / OWASP Reference Table",
        "",
        "| Kind | CWE | OWASP Top 10 | Reference CVEs |",
        "|------|-----|--------------|----------------|",
    ]
    for kind, (cwe, owasp, cves) in FINDING_CWE_MAP.items():
        if cwe is None:
            continue
        lines.append(f"| {kind} | {cwe} | {owasp} | {cves} |")
    lines.append("")
    lines.append("### PHP Outdated Version")
    lines.append("")
    lines.append("| Condition | CWE | CVEs |")
    lines.append("|-----------|-----|------|")
    lines.append("| PHP < 7.4 | CWE-1104 | CVE-2021-21707, CVE-2021-21709 |")
    lines.append("| PHP < 8.0 | CWE-1104 | CVE-2022-31625, CVE-2022-31626 |")
    lines.append("")
    return lines
