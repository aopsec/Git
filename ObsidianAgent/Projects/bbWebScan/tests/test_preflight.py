import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import bbwebscan.preflight as preflight_module
from bbwebscan.models import AuthConfig, RetryPolicy, RunConfig, ToolStatus
from bbwebscan.preflight import (
    _compile_profile_fingerprints,
    _resolve_tool_path,
    collect_tool_inventory,
    detect_identity,
    inventory_tools,
    validate_environment,
)


def _config(tmp_path: Path, *, dry_run: bool, check_tools: bool = False) -> RunConfig:
    return RunConfig(
        program_name="t",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx"],
        wordlist=tmp_path / "missing-wordlist.txt",
        threads=1,
        rate=1,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(),
        output_dir=tmp_path / "run",
        target_inputs=["example.com"],
        check_tools=check_tools,
        dry_run=dry_run,
    )


def test_validate_environment_allows_missing_tools_in_dry_run(tmp_path: Path) -> None:
    statuses = [ToolStatus(name="httpx", required=True, found=False)]

    assert validate_environment(_config(tmp_path, dry_run=True), statuses) == []


def test_validate_environment_check_tools_reports_missing_in_dry_run(tmp_path: Path) -> None:
    statuses = [ToolStatus(name="httpx", required=True, found=False)]

    errors = validate_environment(
        _config(tmp_path, dry_run=True, check_tools=True), statuses
    )

    assert "Missing required tool: httpx" in errors


def _patch_probe(
    monkeypatch: pytest.MonkeyPatch, outputs: list[tuple[int, str]]
) -> list[list[str]]:
    """Replace subprocess.run so each call returns the next (rc, output) tuple.

    Returns a list that captures the argv of every invocation so callers can
    assert which probes were attempted.
    """
    captured_argvs: list[list[str]] = []
    seq: Iterator[tuple[int, str]] = iter(outputs)

    def fake_run(*args: Any, **kwargs: Any) -> MagicMock:
        argv = args[0] if args else kwargs.get("args", [])
        captured_argvs.append(list(argv))
        rc, payload = next(seq)
        result = MagicMock()
        result.returncode = rc
        result.stdout = payload
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    return captured_argvs


def test_detect_identity_verified_for_matching_version_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_probe(monkeypatch, [(0, "Current Version: v1.6.7 by ProjectDiscovery")])
    assert detect_identity("httpx", Path("/usr/bin/httpx")) == "verified"


def test_detect_identity_falls_back_to_help_when_version_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_probe(
        monkeypatch,
        [
            (1, "Error: No such option"),  # httpx -version (Python shim)
            (0, "ProjectDiscovery httpx help text\n--target ..."),  # httpx --help
        ],
    )
    assert detect_identity("httpx", Path("/usr/bin/httpx")) == "verified"
    assert captured[0][1] == "-version"
    assert captured[1][1] == "--help"


def test_detect_identity_suspect_when_python_shim_lacks_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_probe(
        monkeypatch,
        [
            (2, "Error: No such option: -version"),  # version probe fails
            (0, "Usage: httpx [OPTIONS] URL\n\n  HTTPX command-line client."),  # --help
        ],
    )
    assert detect_identity("httpx", Path("/usr/bin/httpx")) == "suspect"


def test_detect_identity_returns_none_when_no_fingerprint() -> None:
    assert detect_identity("arjun", Path("/usr/bin/arjun")) is None


def test_detect_identity_returns_none_when_path_missing() -> None:
    assert detect_identity("httpx", None) is None


def test_detect_identity_rejects_fake_binary_sharing_tool_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-PD binary that just calls itself 'katana' / 'nuclei' must NOT pass
    fingerprinting — discrimination requires PD-specific tagline or org string."""
    _patch_probe(
        monkeypatch,
        [
            (1, "Usage: katana [options]\n  --target URL"),  # version probe
            (0, "Usage: katana [options]\n  --target URL"),  # --help fallback
        ],
    )
    assert detect_identity("katana", Path("/usr/local/bin/katana")) == "suspect"

    _patch_probe(
        monkeypatch,
        [
            (1, "Usage: nuclei OPTIONS"),
            (0, "Usage: nuclei OPTIONS\n  Run nuclei templates against URL"),
        ],
    )
    assert detect_identity("nuclei", Path("/usr/local/bin/nuclei")) == "suspect"


def test_collect_tool_inventory_marks_suspect_in_note(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "bbwebscan.preflight.shutil.which", lambda name: "/usr/bin/httpx"
    )
    _patch_probe(
        monkeypatch,
        [
            (1, "Usage: httpx [OPTIONS] URL"),  # detect_version probe
            (1, "Usage: httpx [OPTIONS] URL"),  # detect_identity version probe
            (0, "Usage: httpx [OPTIONS] URL"),  # detect_identity --help fallback
        ],
    )
    config = _config(tmp_path, dry_run=True)
    statuses = collect_tool_inventory(config)
    assert len(statuses) == 1
    httpx_status = statuses[0]
    assert httpx_status.identity == "suspect"
    assert httpx_status.note is not None
    assert "/usr/bin/httpx" in httpx_status.note


def test_compile_profile_fingerprints_rejects_bad_regex() -> None:
    with pytest.raises(ValueError, match="Invalid tool_identity regex"):
        _compile_profile_fingerprints({"httpx": "(unbalanced"})


def test_profile_fingerprint_overrides_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Residual A: a profile-supplied regex takes precedence over TOOL_IDENTITY."""
    extra = _compile_profile_fingerprints({"httpx": r"^FAKE-OK"})
    # Output that misses both the built-in PD signature AND the profile signature → suspect
    _patch_probe(monkeypatch, [(0, "Usage: httpx ..."), (0, "Usage: httpx ...")])
    assert detect_identity(
        "httpx", Path("/usr/bin/httpx"), extra_fingerprints=extra
    ) == "suspect"
    # Output that matches the profile regex → verified, even though built-in would fail
    _patch_probe(monkeypatch, [(0, "FAKE-OK 1.0")])
    assert detect_identity(
        "httpx", Path("/usr/bin/httpx"), extra_fingerprints=extra
    ) == "verified"


def test_validate_environment_strict_identity_promotes_suspect(tmp_path: Path) -> None:
    """Residual B: --strict-identity makes any 'suspect' a hard error."""
    statuses = [
        ToolStatus(
            name="httpx", required=True, found=True, path=Path("/usr/bin/httpx"),
            identity="suspect", note="binary at /usr/bin/httpx looks wrong",
        )
    ]
    config = _config(tmp_path, dry_run=False)
    config = config.model_copy(update={"strict_identity": True})
    errors = validate_environment(config, statuses)
    assert any("Suspect tool identity: httpx" in e for e in errors)


def test_validate_environment_no_strict_keeps_suspect_advisory(tmp_path: Path) -> None:
    statuses = [
        ToolStatus(
            name="httpx", required=True, found=True, path=Path("/usr/bin/httpx"),
            identity="suspect",
        )
    ]
    config = _config(tmp_path, dry_run=False)
    errors = validate_environment(config, statuses)
    assert not any("Suspect tool identity" in e for e in errors)


def test_inventory_tools_accepts_explicit_list() -> None:
    """The new inventory_tools entrypoint can be called without a RunConfig."""
    statuses = inventory_tools(["httpx", "katana"])
    assert {s.name for s in statuses} == {"httpx", "katana"}


def test_amass_fingerprint_matches_observed_v420_banner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v0.5.0 Item 6: regex derived from real `amass --help` output (v4.2.0
    contains 'OWASP Amass Project'). `-version` alone returns just 'v4.2.0',
    so detect_identity falls back to --help — assert the full path."""
    captured = _patch_probe(
        monkeypatch,
        [
            (0, "v4.2.0"),  # amass -version output
            # amass --help banner contains OWASP (real-output sample):
            (0, "                                  v4.2.0\n  OWASP Amass Project - @owaspamass\n"),
        ],
    )
    assert detect_identity("amass", Path("/home/aops/go/bin/amass")) == "verified"
    assert captured[0][1] == "-version"
    assert captured[1][1] == "--help"


def test_amass_fingerprint_rejects_fake_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake binary just printing 'amass' must NOT pass."""
    _patch_probe(monkeypatch, [(0, "amass\n"), (0, "amass: usage\n")])
    assert detect_identity("amass", Path("/usr/local/bin/amass")) == "suspect"


def test_kiterunner_fingerprint_matches_observed_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v0.5.0 Item 6: kiterunner help references kitebuilder + assetnote."""
    banner = (
        "kite is a context based webscanner\n"
        "use the wordlists from wordlist.assetnote.io\n"
    )
    _patch_probe(monkeypatch, [(0, banner)])
    assert detect_identity("kiterunner", Path("/home/aops/go/bin/kiterunner")) == "verified"


def test_kiterunner_fingerprint_rejects_fake_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_probe(monkeypatch, [(0, "kiterunner: usage\n"), (0, "kiterunner: usage\n")])
    assert detect_identity("kiterunner", Path("/usr/local/bin/kiterunner")) == "suspect"


def test_resolve_tool_path_detects_on_disk_when_not_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.1: a binary in a well-known dir but absent from PATH is path-gap."""
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    binary = bin_dir / "katana"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    monkeypatch.setattr(preflight_module, "_WELL_KNOWN_BIN_DIRS", (bin_dir,))
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    which, gap, shadow = _resolve_tool_path("katana")
    assert which is None
    assert gap == binary.resolve()
    assert shadow is None


def test_resolve_tool_path_detects_shadow_when_path_resolves_elsewhere(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The /usr/bin/httpx (Python shim) shadowing ~/go/bin/httpx scenario."""
    well_known = tmp_path / "go" / "bin"
    well_known.mkdir(parents=True)
    deeper = well_known / "httpx"
    deeper.write_text("real")

    shallow_dir = tmp_path / "usr" / "bin"
    shallow_dir.mkdir(parents=True)
    shallow = shallow_dir / "httpx"
    shallow.write_text("shim")

    monkeypatch.setattr(preflight_module, "_WELL_KNOWN_BIN_DIRS", (well_known,))
    monkeypatch.setattr(shutil, "which", lambda _name: str(shallow))

    which, gap, shadow = _resolve_tool_path("httpx")
    assert which == shallow.resolve()
    assert gap == deeper.resolve()
    assert shadow == shallow.resolve()


def test_resolve_tool_path_no_match_anywhere(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "empty"
    bin_dir.mkdir()
    monkeypatch.setattr(preflight_module, "_WELL_KNOWN_BIN_DIRS", (bin_dir,))
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    which, gap, shadow = _resolve_tool_path("ghost-tool")
    assert which is None
    assert gap is None
    assert shadow is None


def test_inventory_tools_populates_path_gap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "cargo" / "bin"
    bin_dir.mkdir(parents=True)
    binary = bin_dir / "feroxbuster"
    binary.write_text("placeholder")
    binary.chmod(0o755)
    monkeypatch.setattr(preflight_module, "_WELL_KNOWN_BIN_DIRS", (bin_dir,))
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    # Skip subprocess probes — version/identity not under test here.
    monkeypatch.setattr(preflight_module, "detect_version", lambda *_a, **_k: None)
    monkeypatch.setattr(preflight_module, "detect_identity", lambda *_a, **_k: None)

    [status] = inventory_tools(["feroxbuster"])
    assert status.found is False
    assert status.path_gap == binary.resolve()
    assert status.path == binary.resolve()
    assert status.note is not None
    assert "not on PATH" in status.note
    assert "--fix-path" in status.note
