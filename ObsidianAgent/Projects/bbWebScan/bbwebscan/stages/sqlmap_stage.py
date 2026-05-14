"""sqlmap SQL injection detection stage — active parameter testing.

[v0.5.5] Vault citation: pending (hacking-apis / OWASP integration TBD).

sqlmap (https://sqlmap.org) performs automated SQL injection testing across
application parameters. The tool supports multiple detection techniques:
boolean-based blind, time-based blind, error-based, UNION query-based, etc.

Modes:
- `off` (default): stage is skipped
- `smooth`: conservative testing (--level 1, --risk 1, per-URL timeout)
  suitable for production environments; compatible with standard deployments
- `aggressive`: intensive testing (--level 5, --risk 3, tamper scripts)
  requires `--ack-authorized`; higher noise and target load

Input scope:
- Only parameterized URLs (from arjun params stage)
- URLs are filtered: scheme + netloc + path; params with known values passed
  as `?key=value` query strings

Output: sqlmap JSON report (one per URL) containing vulnerability summaries.
We parse and emit findings with severity per injection type.

Severity mapping:
- boolean-based blind, time-based blind → high
- error-based → critical (data extraction usually possible)
- UNION query-based → critical
- stack queries → high
"""

import json
from pathlib import Path

from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig


def build_plans(
    config: RunConfig, artifacts: RunArtifacts, urls: list[str]
) -> list[CommandPlan]:
    """Build sqlmap command plans for parameterized URLs.

    Skips if sqlmap_mode is 'off'.
    """
    if config.sqlmap_mode == "off" or not urls:
        return []

    plans: list[CommandPlan] = []
    for index, url in enumerate(urls, start=1):
        output_file = artifacts.artifacts / f"sqlmap_{index}.json"
        command = _build_sqlmap_command(url, output_file, config)
        plans.append(
            CommandPlan(
                stage="sqlmap",
                label=f"sqlmap_{index}",
                command=command,
                artifacts=[output_file],
            )
        )
    return plans


def parse_results(artifact_paths: list[Path]) -> tuple[list[Finding], list[str]]:
    """Parse sqlmap JSON reports and emit findings."""
    findings: list[Finding] = []
    for artifact_path in artifact_paths:
        file_findings = _parse_single_report(artifact_path)
        findings.extend(file_findings)
    return findings, []


def _build_sqlmap_command(url: str, output_file: Path, config: RunConfig) -> list[str]:
    """Build sqlmap command line for the given mode."""
    base_command = [
        "sqlmap",
        "-u", url,
        "--batch",
        "--json-file", str(output_file),
    ]

    if config.sqlmap_mode == "smooth":
        base_command.extend([
            "--level", "1",
            "--risk", "1",
            "--random-agent",
            "--timeout", str(config.sqlmap_timeout // 10),  # per-request timeout
        ])
    elif config.sqlmap_mode == "aggressive":
        base_command.extend([
            "--level", "5",
            "--risk", "3",
            "--random-agent",
            "--threads", "4",
            "--tamper", "between,space2comment",
            "--timeout", str(config.sqlmap_timeout // 5),  # per-request timeout (aggressive)
        ])

    return base_command


def _parse_single_report(artifact_path: Path) -> list[Finding]:
    """Parse a single sqlmap JSON report."""
    findings: list[Finding] = []
    if not artifact_path.is_file():
        return findings

    try:
        report = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return findings

    # sqlmap JSON: { "target": "...", "vulnerability": [...] }
    vulnerabilities = report.get("vulnerability", [])
    if not vulnerabilities:
        return findings

    for vuln in vulnerabilities:
        severity = _map_injection_type_to_severity(vuln.get("type", "unknown"))
        title = f"SQL Injection ({vuln.get('type', 'unknown')})"
        target = report.get("target", str(artifact_path))
        evidence = str(artifact_path)

        findings.append(
            Finding(
                stage="sqlmap",
                kind="sql-injection",
                target=target,
                severity=severity,
                title=title,
                evidence=evidence,
            )
        )

    return findings


def _map_injection_type_to_severity(injection_type: str) -> str:
    """Map sqlmap injection type to severity."""
    type_lower = injection_type.lower()

    # Critical: data extraction is possible
    if any(x in type_lower for x in ["union", "error", "stacked"]):
        return "critical"

    # High: blind injection, information leakage
    if any(x in type_lower for x in ["boolean", "time", "blind"]):
        return "high"

    # Medium: default
    return "medium"
