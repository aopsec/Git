"""jwt_tool analysis stage — JWT token inspection after auth discovery.

[v0.5.5] Vault citation: PENDING — Scrapy CyberPDF attestation required.

jwt_tool (https://github.com/ticarpi/jwt_tool) analyzes JWT tokens for
vulnerabilities: alg=none bypass, weak secrets, header injection (kid),
signature issues, etc.

Token input source (Phase 5a):
- Bearer token from Authorization header (config.auth.headers['Authorization'])
- Extracts the token value (strip "Bearer " prefix if present)

Output shape: jwt_tool writes a JSON report (via `-o` flag) with per-token
findings. We parse the JSON and emit findings with severity based on the
detected issue type.

Severity mapping:
- alg=none, alg=RS/HS confusion, header injection → high
- weak secret (cracked) → critical
- signature validation bypass → critical
- other issues → medium
"""

import json
from pathlib import Path

from bbwebscan.models import CommandPlan, Finding, RunArtifacts, RunConfig


def build_plan(config: RunConfig, artifacts: RunArtifacts) -> CommandPlan | None:
    """Build jwt_tool command plan if Bearer token is available.

    Returns None if no Authorization header with Bearer token found.
    """
    auth_header = config.auth.headers.get("Authorization", "")
    if not auth_header:
        return None

    # Extract token: "Bearer <token>" → <token>
    token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()
    if not token:
        return None

    output_file = artifacts.artifacts / "jwt_tool.json"
    command = [
        "jwt_tool",
        "-t", token,
        "-o", str(output_file),
    ]

    # [v0.5.5 sec-fix] Mark the token slot so the dry-run argv echo and any
    # log writes (runner.run_plan + redact_command_for_log) mask the JWT.
    # Without this the bearer token leaked verbatim to stdout and to
    # ``runs/<UTC>/logs/jwt_tool.stdout.log``.
    return CommandPlan(
        stage="jwt-analysis",
        label="jwt_tool",
        command=command,
        artifacts=[output_file],
        redact_indices=[2],
    )


def parse_results(output_file: Path) -> list[Finding]:
    """Parse jwt_tool JSON output and emit findings."""
    findings: list[Finding] = []
    if not output_file.is_file():
        return findings

    try:
        report = json.loads(output_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return findings

    # jwt_tool JSON structure: { "token": "...", "issues": [...] }
    issues = report.get("issues", [])
    if not issues:
        return findings

    for issue in issues:
        severity = _map_severity(issue.get("type", "unknown"))
        title = issue.get("description", issue.get("type", "JWT issue"))
        evidence = str(output_file)

        findings.append(
            Finding(
                stage="jwt-analysis",
                kind="jwt-issue",
                target=evidence,  # No specific URL for token analysis
                severity=severity,
                title=title,
                evidence=evidence,
            )
        )

    return findings


def _map_severity(issue_type: str) -> str:
    """Map jwt_tool issue type to severity level."""
    issue_lower = issue_type.lower()

    # Critical severity
    if any(x in issue_lower for x in ["weak_secret", "cracked", "signature_bypass"]):
        return "critical"

    # High severity
    if any(
        x in issue_lower for x in [
            "alg_none", "algorithm_confusion", "kid_injection", "header_injection"
        ]
    ):
        return "high"

    # Medium severity (default)
    return "medium"
