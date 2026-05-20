import argparse
from pathlib import Path

import pytest

from bbwebscan.doctor import (
    INSTALL_HINTS,
    _classify,
    doctor_exit_code,
    format_report,
    run_doctor,
)
from bbwebscan.models import ToolStatus


def _found(name: str) -> ToolStatus:
    return ToolStatus(
        name=name, required=True, found=True, path=Path(f"/usr/bin/{name}"),
        version=f"{name} v1.0", identity="verified",
    )


def _missing(name: str) -> ToolStatus:
    return ToolStatus(name=name, required=True, found=False)


def _suspect(name: str) -> ToolStatus:
    return ToolStatus(
        name=name, required=True, found=True, path=Path(f"/usr/bin/{name}"),
        version="Usage: ...", identity="suspect", note=f"binary at /usr/bin/{name} is suspect",
    )


def test_format_report_marks_each_state() -> None:
    statuses = [_found("arjun"), _missing("katana"), _suspect("httpx")]
    report = format_report(statuses)
    assert "✓ arjun" in report
    assert "✗ katana" in report
    assert "? httpx" in report


def test_format_report_includes_install_hint_for_missing_tool() -> None:
    statuses = [_missing("katana")]
    report = format_report(statuses)
    assert INSTALL_HINTS["katana"] in report
    assert "→ install:" in report


def test_format_report_summary_lists_missing_and_suspect() -> None:
    statuses = [_missing("katana"), _missing("nuclei"), _suspect("httpx")]
    report = format_report(statuses)
    assert "2 missing (katana, nuclei)" in report
    assert "1 suspect (httpx)" in report


def test_format_report_all_clean_says_ready() -> None:
    statuses = [_found("arjun"), _found("dirsearch")]
    report = format_report(statuses)
    assert "All tools ready" in report


def test_doctor_exit_code_zero_when_all_found_and_no_strict_suspects() -> None:
    statuses = [_found("arjun"), _suspect("httpx")]
    assert doctor_exit_code(statuses) == 0
    assert doctor_exit_code(statuses, strict_identity=True) == 2


def test_doctor_exit_code_two_when_any_missing() -> None:
    statuses = [_found("arjun"), _missing("katana")]
    assert doctor_exit_code(statuses) == 2


def test_install_hints_cover_supported_tools() -> None:
    """Every tool that bbWebScan can drive should have an install hint, so doctor's
    advice is never blank."""
    expected = {
        "httpx", "katana", "scrapy", "nuclei", "ffuf",
        "feroxbuster", "arjun", "dirsearch",
    }
    assert expected.issubset(INSTALL_HINTS.keys())


def _path_gap(name: str, gap: Path) -> ToolStatus:
    return ToolStatus(
        name=name, required=True, found=False, path=gap, path_gap=gap,
        note=f"binary present at {gap} but not on PATH; run `bbwebscan doctor --fix-path`...",
    )


def _shadowed(name: str, shallow: Path, deep: Path) -> ToolStatus:
    return ToolStatus(
        name=name, required=True, found=True, path=shallow,
        version="Usage: ...", identity=None,
        path_gap=deep, shadowed_by=shallow,
    )


def test_classify_marks_path_gap_as_warning(tmp_path: Path) -> None:
    status = _path_gap("feroxbuster", tmp_path / "feroxbuster")
    symbol, label = _classify(status)
    assert symbol == "⚠"
    assert label == "on-disk"


def test_classify_marks_shadowed_as_warning(tmp_path: Path) -> None:
    status = _shadowed(
        "httpx", Path("/usr/bin/httpx"), tmp_path / "go" / "bin" / "httpx"
    )
    symbol, label = _classify(status)
    assert symbol == "⚠"
    assert label == "shadowed"


def test_format_report_includes_fix_path_remediation(tmp_path: Path) -> None:
    binary = tmp_path / "feroxbuster"
    statuses = [_path_gap("feroxbuster", binary)]
    report = format_report(statuses)
    assert "⚠ feroxbuster" in report
    assert f"on disk at {binary} (not on PATH)" in report
    assert "bbwebscan doctor --fix-path" in report


def test_format_report_includes_shadow_remediation(tmp_path: Path) -> None:
    deep = tmp_path / "go" / "bin" / "httpx"
    statuses = [_shadowed("httpx", Path("/usr/bin/httpx"), deep)]
    report = format_report(statuses)
    assert "/usr/bin/httpx is on PATH first" in report
    assert "shadowing" in report


def test_summary_separates_missing_and_path_gap(tmp_path: Path) -> None:
    statuses = [
        ToolStatus(name="katana", required=True, found=False),
        _path_gap("feroxbuster", tmp_path / "feroxbuster"),
    ]
    report = format_report(statuses)
    assert "1 missing (katana)" in report
    assert "1 path-gap (feroxbuster)" in report
    assert "bbwebscan doctor --fix-path" in report
    assert "bbwebscan install" in report


def test_doctor_exit_code_two_for_path_gap(tmp_path: Path) -> None:
    statuses = [_path_gap("feroxbuster", tmp_path / "feroxbuster")]
    assert doctor_exit_code(statuses) == 2


def test_run_doctor_fix_path_invokes_persist_helper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target_rc = tmp_path / ".zshrc"
    added_dir = tmp_path / "go" / "bin"

    def fake_persist(**_kwargs: object) -> tuple[Path, list[Path]]:
        return (target_rc, [added_dir])

    monkeypatch.setattr("bbwebscan.doctor.persist_path_in_shell_rc", fake_persist)
    rc = run_doctor(argparse.Namespace(profile=None, strict_identity=False, fix_path=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert "updated" in out
    assert str(target_rc) in out
    assert str(added_dir) in out


def test_run_doctor_fix_path_idempotent_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target_rc = tmp_path / ".zshrc"
    monkeypatch.setattr(
        "bbwebscan.doctor.persist_path_in_shell_rc",
        lambda **_kwargs: (target_rc, []),
    )
    rc = run_doctor(argparse.Namespace(profile=None, strict_identity=False, fix_path=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert "already configured" in out
