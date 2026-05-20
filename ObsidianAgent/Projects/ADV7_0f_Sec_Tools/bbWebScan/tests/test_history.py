import argparse
import json
from pathlib import Path

import pytest

from bbwebscan.history import (
    compare_runs,
    format_history,
    list_runs,
    run_compare,
    run_history,
    run_show,
    show_run,
)
from bbwebscan.models import RunSummary


def _write_run(  # noqa: PLR0913 - test fixture builder benefits from many kwargs
    runs_dir: Path,
    timestamp: str,
    *,
    program: str = "demo",
    findings: list[dict[str, object]] | None = None,
    decisions: list[dict[str, object]] | None = None,
    summary: str = "# bbWebScan Summary",
    incomplete: bool = False,
) -> Path:
    run_dir = runs_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_config.json").write_text(
        json.dumps({"program_name": program, "mode": "safe"}), encoding="utf-8",
    )
    if not incomplete:
        (run_dir / "findings.json").write_text(
            json.dumps(findings or []), encoding="utf-8",
        )
    (run_dir / "scope_decisions.json").write_text(
        json.dumps(decisions or [{"allowed": True, "reason": "ok", "value": "x"}]),
        encoding="utf-8",
    )
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")
    return run_dir


def test_list_runs_skips_incomplete(tmp_path: Path) -> None:
    """v0.4.3 (Item 3): runs missing required artifacts are excluded."""
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "20260509T010000Z")
    _write_run(runs_dir, "20260509T020000Z", incomplete=True)
    summaries = list_runs(runs_dir)
    assert len(summaries) == 1
    assert summaries[0].timestamp == "20260509T010000Z"


def test_list_runs_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    assert list_runs(tmp_path / "nonexistent") == []


def test_format_history_sorts_newest_first(tmp_path: Path) -> None:
    """v0.4.3 (Item 3): newest run appears first in the table output."""
    runs_dir = tmp_path / "runs"
    _write_run(runs_dir, "20260509T010000Z", program="early")
    _write_run(runs_dir, "20260509T030000Z", program="latest")
    _write_run(runs_dir, "20260509T020000Z", program="middle")
    summaries = list_runs(runs_dir)
    output = format_history(summaries)
    lines = output.splitlines()
    assert "TIMESTAMP" in lines[0]
    # First data row should be the latest timestamp.
    assert "20260509T030000Z" in lines[1]
    assert "latest" in lines[1]


def test_run_history_respects_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.3 (Item 3): --limit caps the number of rows shown."""
    runs_dir = tmp_path / "runs"
    for i in range(5):
        _write_run(runs_dir, f"20260509T0{i}0000Z", program=f"prog{i}")
    args = argparse.Namespace(limit=2, runs_dir=str(runs_dir))
    rc = run_history(args)
    assert rc == 0
    out = capsys.readouterr().out
    # Header + 2 data rows = 3 lines (might be more if formatting wraps).
    data_rows = [line for line in out.splitlines() if line.startswith("20260509")]
    assert len(data_rows) == 2


def test_format_history_empty_says_no_runs() -> None:
    assert format_history([]) == "No completed runs found."


def test_show_run_prints_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.3 (Item 4): show_run returns summary.md content."""
    runs_dir = tmp_path / "runs"
    run_dir = _write_run(runs_dir, "20260509T010000Z", summary="# specific summary text")
    output = show_run(run_dir)
    assert "specific summary text" in output


def test_show_run_raises_on_missing_summary(tmp_path: Path) -> None:
    """v0.4.3 (Item 4): missing summary.md → FileNotFoundError."""
    empty = tmp_path / "no-summary"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="no summary.md"):
        show_run(empty)


def _finding(stage: str, target: str, title: str, severity: str = "info") -> dict[str, object]:
    return {
        "stage": stage, "kind": "test", "target": target, "title": title,
        "severity": severity, "evidence": "fixture",
    }


def test_compare_runs_detects_added_and_removed(tmp_path: Path) -> None:
    """v0.4.3 (Item 4): identity is (stage, kind, target, title) — diff is exact."""
    runs_dir = tmp_path / "runs"
    f1 = _finding("httpx", "https://app.example.com", "shared")
    f2 = _finding("nuclei", "https://app.example.com/old", "removed-finding")
    f3 = _finding("nuclei", "https://app.example.com/new", "added-finding")
    a = _write_run(runs_dir, "20260509T010000Z", findings=[f1, f2])
    b = _write_run(runs_dir, "20260509T020000Z", findings=[f1, f3])
    output = compare_runs(a, b)
    assert "added-finding" in output
    assert "removed-finding" in output
    assert "+1 added" in output
    assert "-1 removed" in output
    assert "= 1 unchanged" in output


def test_compare_runs_severity_delta(tmp_path: Path) -> None:
    """v0.4.3 (Item 4): severity counts reflect both sides."""
    runs_dir = tmp_path / "runs"
    a = _write_run(runs_dir, "20260509T010000Z", findings=[
        _finding("httpx", "https://x", "f1", severity="medium"),
    ])
    b = _write_run(runs_dir, "20260509T020000Z", findings=[
        _finding("httpx", "https://x", "f1", severity="medium"),
        _finding("nuclei", "https://x/admin", "f2", severity="high"),
    ])
    output = compare_runs(a, b)
    assert "medium=1" in output  # in both A and B sections
    assert "high=0" in output  # A had zero high
    assert "high=1" in output  # B has one high


def test_run_show_wires_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    run_dir = _write_run(runs_dir, "20260509T010000Z", summary="### test summary")
    args = argparse.Namespace(run_dir=str(run_dir))
    rc = run_show(args)
    assert rc == 0
    assert "test summary" in capsys.readouterr().out


def test_run_compare_wires_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    a = _write_run(runs_dir, "20260509T010000Z")
    b = _write_run(runs_dir, "20260509T020000Z")
    args = argparse.Namespace(run_a=str(a), run_b=str(b))
    rc = run_compare(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "bbwebscan compare" in out


def test_list_runs_creates_valid_run_summary(tmp_path: Path) -> None:
    """RunSummary fields populate correctly."""
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir, "20260509T010000Z",
        program="acme",
        findings=[_finding("httpx", "https://x", "f1")],
        decisions=[
            {"allowed": True, "reason": "ok", "value": "a"},
            {"allowed": False, "reason": "denied", "value": "b"},
        ],
    )
    [summary] = list_runs(runs_dir)
    assert isinstance(summary, RunSummary)
    assert summary.program_name == "acme"
    assert summary.finding_count == 1
    assert summary.allowed_decisions == 1
    assert summary.rejected_decisions == 1
    assert summary.timestamp == "20260509T010000Z"
