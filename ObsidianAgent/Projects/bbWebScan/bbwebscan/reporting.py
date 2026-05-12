from pathlib import Path

from bbwebscan.models import ExecutionResult, Finding, RunConfig, ScopeDecision, ToolStatus

_FINDINGS_PREVIEW_LIMIT: int = 25


def build_summary_markdown(  # noqa: PLR0913 - report assembly is naturally wide
    config: RunConfig,
    findings: list[Finding],
    statuses: list[ToolStatus],
    results: list[ExecutionResult],
    decisions: list[ScopeDecision],
    errors: list[str],
) -> str:
    timeouts = (
        f"- Tool timeout: `{config.tool_timeout_s}s` | "
        f"Wall clock: `{config.command_wall_clock_s}s`"
    )
    lines = [
        f"# bbWebScan Summary: {config.program_name}",
        "",
        f"- Mode: `{config.mode}`",
        f"- Dry run: `{config.dry_run}`",
        f"- Selected tools: `{', '.join(config.enabled_tools)}`",
        f"- Findings: `{len(findings)}`",
        f"- Allowed scope decisions: `{sum(1 for item in decisions if item.allowed)}`",
        f"- Rejected scope decisions: `{sum(1 for item in decisions if not item.allowed)}`",
        timeouts,
        f"- Retry: `attempts={config.retry.max_attempts} backoff={config.retry.backoff_s}s`",
        "",
        "## Tool Inventory",
    ]
    lines.extend(_tool_inventory_line(status) for status in statuses)
    lines.extend(["", "## Execution"])
    lines.extend(
        f"- `{result.label}`: `{result.status}` (attempts={result.attempts}, "
        f"exit={result.exit_code})"
        for result in results
    )
    lines.extend(["", "## Findings"])
    if findings:
        lines.extend(
            f"- `{finding.severity}` `{finding.stage}` `{finding.target}`: {finding.title}"
            for finding in findings[:_FINDINGS_PREVIEW_LIMIT]
        )
    else:
        lines.append("- No findings collected.")
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines) + "\n"


def write_summary(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _tool_inventory_line(status: ToolStatus) -> str:
    state = "found" if status.found else "missing"
    suffix = " [SUSPECT]" if status.identity == "suspect" else ""
    return (
        f"- `{status.name}`: `{state}` ({status.path or 'n/a'}) "
        f"v=`{status.version or 'n/a'}`{suffix}"
    )
