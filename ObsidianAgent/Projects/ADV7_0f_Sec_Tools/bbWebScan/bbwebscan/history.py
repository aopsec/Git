import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from bbwebscan.models import RunSummary

_REQUIRED_FILES: tuple[str, ...] = ("run_config.json", "findings.json", "scope_decisions.json")


def list_runs(runs_dir: Path = Path("runs")) -> list[RunSummary]:
    """Walk runs_dir for completed runs (all required artifacts present)."""
    if not runs_dir.is_dir():
        return []
    summaries: list[RunSummary] = []
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        if not all((run_dir / name).is_file() for name in _REQUIRED_FILES):
            continue
        summary = _summarize(run_dir)
        if summary is not None:
            summaries.append(summary)
    return summaries


def _summarize(run_dir: Path) -> RunSummary | None:
    try:
        config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
        findings = json.loads((run_dir / "findings.json").read_text(encoding="utf-8"))
        decisions = json.loads((run_dir / "scope_decisions.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(findings, list) or not isinstance(decisions, list):
        return None
    allowed = sum(1 for d in decisions if isinstance(d, dict) and d.get("allowed") is True)
    rejected = len(decisions) - allowed
    return RunSummary(
        run_dir=run_dir,
        program_name=str(config.get("program_name", "unknown")),
        mode=str(config.get("mode", "unknown")),
        finding_count=len(findings),
        allowed_decisions=allowed,
        rejected_decisions=rejected,
        timestamp=run_dir.name,
    )


def format_history(summaries: list[RunSummary]) -> str:
    if not summaries:
        return "No completed runs found."
    sorted_summaries = sorted(summaries, key=lambda s: s.timestamp, reverse=True)
    header = f"{'TIMESTAMP':<22}{'PROGRAM':<16}{'MODE':<12}{'FINDINGS':<10}SCOPE"
    rows = [header]
    for summary in sorted_summaries:
        total = summary.allowed_decisions + summary.rejected_decisions
        scope = f"{summary.allowed_decisions}/{total}"
        rows.append(
            f"{summary.timestamp:<22}"
            f"{summary.program_name[:14]:<16}"
            f"{summary.mode:<12}"
            f"{summary.finding_count:<10}"
            f"{scope}"
        )
    return "\n".join(rows)


def run_history(args: argparse.Namespace) -> int:
    runs_dir = Path(args.runs_dir).expanduser() if args.runs_dir else Path("runs")
    summaries = list_runs(runs_dir)
    sorted_summaries = sorted(summaries, key=lambda s: s.timestamp, reverse=True)
    limited = sorted_summaries[: args.limit]
    print(format_history(limited))
    return 0


def show_run(run_dir: Path) -> str:
    summary_path = run_dir / "summary.md"
    if not summary_path.is_file():
        raise FileNotFoundError(f"no summary.md at {summary_path}")
    return summary_path.read_text(encoding="utf-8")


def run_show(args: argparse.Namespace) -> int:
    print(show_run(Path(args.run_dir).expanduser()))
    return 0


def compare_runs(run_a: Path, run_b: Path) -> str:
    """[v0.4.3 Item 4] Diff findings.json between two runs.

    Identity is the tuple (stage, kind, target, title). Output sections:
    added (in B but not A), removed (in A but not B), unchanged, severity_delta.
    """
    findings_a = _load_findings(run_a)
    findings_b = _load_findings(run_b)
    keys_a = {_finding_key(f): f for f in findings_a}
    keys_b = {_finding_key(f): f for f in findings_b}
    added = [keys_b[k] for k in keys_b.keys() - keys_a.keys()]
    removed = [keys_a[k] for k in keys_a.keys() - keys_b.keys()]
    unchanged = [keys_a[k] for k in keys_a.keys() & keys_b.keys()]
    sev_a = Counter(str(f.get("severity", "info")) for f in findings_a)
    sev_b = Counter(str(f.get("severity", "info")) for f in findings_b)
    severity_delta = {sev: (sev_a[sev], sev_b[sev]) for sev in sev_a.keys() | sev_b.keys()}
    return _format_compare(run_a, run_b, added, removed, unchanged, severity_delta)


def _load_findings(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "findings.json"
    if not path.is_file():
        raise FileNotFoundError(f"no findings.json at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _finding_key(finding: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(finding.get("stage", "")),
        str(finding.get("kind", "")),
        str(finding.get("target", "")),
        str(finding.get("title", "")),
    )


def _sev_str(counter: Counter[str]) -> str:
    return ", ".join(f"{n} {sev}" for sev, n in counter.items()) or ""


def _format_compare(  # noqa: PLR0913 - format helper takes the materialized diff sections
    run_a: Path, run_b: Path,
    added: list[dict[str, Any]],
    removed: list[dict[str, Any]],
    unchanged: list[dict[str, Any]],
    severity_delta: dict[str, tuple[int, int]],
) -> str:
    lines = [f"bbwebscan compare {run_a.name} → {run_b.name}", ""]
    added_summary = Counter(str(f.get("severity", "info")) for f in added)
    removed_summary = Counter(str(f.get("severity", "info")) for f in removed)
    lines.append(
        f"  +{len(added)} added{(' (' + _sev_str(added_summary) + ')') if added else ''}"
    )
    for finding in added:
        lines.append(
            f"    + {finding.get('severity')} {finding.get('stage')} "
            f"{finding.get('target')}: {finding.get('title')}"
        )
    lines.append("")
    lines.append(
        f"  -{len(removed)} removed"
        f"{(' (' + _sev_str(removed_summary) + ')') if removed else ''}"
    )
    for finding in removed:
        lines.append(
            f"    - {finding.get('severity')} {finding.get('stage')} "
            f"{finding.get('target')}: {finding.get('title')}"
        )
    lines.append(f"   = {len(unchanged)} unchanged")
    lines.append("")
    a_parts = ", ".join(f"{sev}={severity_delta[sev][0]}" for sev in sorted(severity_delta))
    b_parts = ", ".join(f"{sev}={severity_delta[sev][1]}" for sev in sorted(severity_delta))
    lines.append(f"severity counts: A=[{a_parts}] B=[{b_parts}]")
    return "\n".join(lines)


def run_compare(args: argparse.Namespace) -> int:
    print(compare_runs(Path(args.run_a).expanduser(), Path(args.run_b).expanduser()))
    return 0
