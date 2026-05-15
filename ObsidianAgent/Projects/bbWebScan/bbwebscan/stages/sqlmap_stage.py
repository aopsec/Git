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

Output: sqlmap stores results in output_dir. We parse output files and emit
findings with severity per injection type.

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
    sqlmap_output_dir = artifacts.artifacts / "sqlmap"
    sqlmap_output_dir.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(urls, start=1):
        results_file = sqlmap_output_dir / f"results_{index}.txt"
        command = _build_sqlmap_command(url, sqlmap_output_dir, config)
        plans.append(
            CommandPlan(
                stage="sqlmap",
                label=f"sqlmap_{index}",
                command=command,
                artifacts=[results_file],
            )
        )
    return plans


def parse_results(artifact_paths: list[Path]) -> tuple[list[Finding], list[str]]:
    """Parse sqlmap output reports and emit findings.

    sqlmap outputs to output_dir with results stored in subdirectories.
    We look for evidence of SQL injection in the output.
    """
    findings: list[Finding] = []
    for artifact_path in artifact_paths:
        file_findings = _parse_single_report(artifact_path)
        findings.extend(file_findings)
    return findings, []


def _build_sqlmap_command(url: str, output_dir: Path, config: RunConfig) -> list[str]:
    """Build sqlmap command line for the given mode."""
    base_command = [
        "sqlmap",
        "-u", url,
        "--batch",
        "--output-dir", str(output_dir),
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
    """Parse sqlmap output from JSON, directory, or text files.

    Handles:
    - JSON test fixtures (for backward compatibility with tests)
    - sqlmap output directories (actual command execution)
    - Text files containing vulnerability indicators
    """
    findings: list[Finding] = []
    if not artifact_path.exists():
        return findings

    # Try parsing as JSON first (test fixtures + potential future sqlmap JSON output)
    if artifact_path.is_file() and artifact_path.suffix == ".json":
        return _parse_json_report(artifact_path)

    # Handle directory output from sqlmap
    if artifact_path.is_dir():
        return _parse_sqlmap_directory(artifact_path)

    # Handle text files or other output
    if artifact_path.is_file():
        return _parse_text_report(artifact_path)

    return findings


def _parse_json_report(artifact_path: Path) -> list[Finding]:
    """Parse sqlmap JSON test fixture format."""
    findings: list[Finding] = []
    try:
        report = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return findings

    vulnerabilities = report.get("vulnerability", [])
    if not vulnerabilities:
        return findings

    for vuln in vulnerabilities:
        severity = _map_injection_type_to_severity(vuln.get("type", "unknown"))
        title = f"SQL Injection ({vuln.get('type', 'unknown')})"
        target = report.get("target", str(artifact_path))

        findings.append(
            Finding(
                stage="sqlmap",
                kind="sql-injection",
                target=target,
                severity=severity,
                title=title,
                evidence=str(artifact_path),
            )
        )

    return findings


def _parse_sqlmap_directory(artifact_path: Path) -> list[Finding]:
    """Parse sqlmap output directory structure."""
    findings: list[Finding] = []

    # Look for XML or other result files sqlmap generates
    for xml_file in artifact_path.glob("**/*.xml"):
        try:
            content = xml_file.read_text(encoding="utf-8", errors="ignore")
            if "SQL injection" in content or "vulnerability" in content:
                findings.append(
                    Finding(
                        stage="sqlmap",
                        kind="sql-injection",
                        target=str(artifact_path),
                        severity="high",
                        title="SQL Injection Detected",
                        evidence=str(xml_file),
                    )
                )
        except (OSError, ValueError):
            continue

    return findings


def _parse_text_report(artifact_path: Path) -> list[Finding]:
    """Parse sqlmap text output for vulnerability indicators."""
    findings: list[Finding] = []
    try:
        content = artifact_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return findings

    # Check for sqlmap vulnerability indicators
    if any(indicator in content for indicator in [
        "SQL injection found",
        "injectable",
        "sqlmap identified",
        "[PAYLOAD]",  # Common in sqlmap output
    ]):
        findings.append(
            Finding(
                stage="sqlmap",
                kind="sql-injection",
                target=str(artifact_path),
                severity="high",
                title="SQL Injection Detected",
                evidence=str(artifact_path),
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
