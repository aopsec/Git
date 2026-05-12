import argparse
import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bbwebscan.installer import (
    PERSIST_MARKER,
    QUIET_KEEP_RE,
    build_install_command,
    persist_path_in_shell_rc,
    run_installer,
)


def _args(installer: str | None = None, **flags: bool) -> argparse.Namespace:
    return argparse.Namespace(
        installer=installer,
        dry_run=flags.get("dry_run", False),
        persist_path=flags.get("persist_path", True),
        update_nuclei_templates=flags.get("update_nuclei_templates", False),
        quiet=flags.get("quiet", False),
    )


def test_build_install_command_default_includes_persist_path(tmp_path: Path) -> None:
    """v0.4.1: persist-path is the new default so PATH gets fixed automatically."""
    installer = tmp_path / "fake-installer.sh"
    installer.touch()
    cmd = build_install_command(installer, dry_run=False)
    assert cmd == [str(installer), "--persist-path"]


def test_build_install_command_omits_persist_path_when_opted_out(tmp_path: Path) -> None:
    installer = tmp_path / "fake-installer.sh"
    installer.touch()
    cmd = build_install_command(installer, dry_run=False, persist_path=False)
    assert cmd == [str(installer)]


def test_build_install_command_passes_each_flag(tmp_path: Path) -> None:
    installer = tmp_path / "fake-installer.sh"
    installer.touch()
    cmd = build_install_command(
        installer, dry_run=True, persist_path=True, update_nuclei_templates=True
    )
    assert cmd[0] == str(installer)
    assert cmd[1:] == ["--dry-run", "--persist-path", "--update-nuclei-templates"]


def test_run_installer_raises_when_script_missing(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-installer.sh"
    args = _args(installer=str(missing))
    with pytest.raises(FileNotFoundError, match="installer not found"):
        run_installer(args)


def test_run_installer_invokes_subprocess_and_returns_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = tmp_path / "fake-installer.sh"
    installer.write_text("#!/bin/sh\nexit 0\n")
    captured: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        captured["cmd"] = cmd
        result = MagicMock()
        result.returncode = 7
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    args = _args(installer=str(installer), dry_run=True, persist_path=True)
    rc = run_installer(args)
    assert rc == 7
    assert captured["cmd"] == [str(installer), "--dry-run", "--persist-path"]
    out = capsys.readouterr().out
    assert "[bbwebscan install]" in out
    assert "--dry-run" in out


def test_persist_path_creates_rc_block_when_marker_absent(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    rc.write_text("# user shell setup\nexport EDITOR=vim\n", encoding="utf-8")
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    written, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert written == rc
    assert added == [bin_dir]
    body = rc.read_text(encoding="utf-8")
    assert PERSIST_MARKER in body
    assert f'"{bin_dir}:$PATH"' in body
    assert body.startswith("# user shell setup")  # original content preserved


def test_persist_path_idempotent_when_bash_installer_marker_present(tmp_path: Path) -> None:
    """v0.4.2 (FIX-BBW-E): the bash installer's own marker also counts as 'already
    configured', so running `bbwebscan doctor --fix-path` after `bbwebscan install`
    doesn't double-write a second PATH-export block."""
    rc = tmp_path / ".zshrc"
    bin_dir = tmp_path / "go" / "bin"
    bin_dir.mkdir(parents=True)
    rc.write_text(
        "# user setup\n"
        "# [FIX-BBR-02] bug bounty web recon tool PATH\n"
        f'export PATH="{bin_dir}:$PATH"\n',
        encoding="utf-8",
    )
    pre = rc.read_text(encoding="utf-8")
    written, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert written == rc
    assert added == []
    assert rc.read_text(encoding="utf-8") == pre


def test_persist_path_idempotent_when_marker_present(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    bin_dir = tmp_path / "cargo" / "bin"
    bin_dir.mkdir(parents=True)
    rc.write_text(
        f"# user setup\n{PERSIST_MARKER}\nexport PATH=\"{bin_dir}:$PATH\"\n",
        encoding="utf-8",
    )
    pre = rc.read_text(encoding="utf-8")
    written, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert written == rc
    assert added == []
    assert rc.read_text(encoding="utf-8") == pre  # untouched


def test_persist_path_skips_dirs_already_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rc = tmp_path / ".zshrc"
    on_path_dir = tmp_path / "already-here"
    on_path_dir.mkdir()
    elsewhere_dir = tmp_path / "missing-from-path"
    elsewhere_dir.mkdir()
    monkeypatch.setenv("PATH", str(on_path_dir))
    _, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(on_path_dir, elsewhere_dir),
    )
    assert added == [elsewhere_dir]


def test_persist_path_skips_nonexistent_dirs(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    real = tmp_path / "real-bin"
    real.mkdir()
    fake = tmp_path / "does-not-exist"
    _, added = persist_path_in_shell_rc(rc_path=rc, candidate_dirs=(real, fake))
    assert added == [real]


def test_persist_path_creates_missing_rc_file(tmp_path: Path) -> None:
    rc = tmp_path / "newhome" / ".zshrc"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    written, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert written.is_file()
    assert added == [bin_dir]


def test_persist_path_returns_noop_when_no_dirs_needed(tmp_path: Path) -> None:
    rc = tmp_path / ".zshrc"
    bin_dir = tmp_path / "bin"  # not created on disk
    written, added = persist_path_in_shell_rc(
        rc_path=rc, candidate_dirs=(bin_dir,),
    )
    assert written == rc
    assert added == []
    assert not rc.exists()


@pytest.mark.parametrize("line,expected", [
    ("[*] Installing Go-based tools\n", True),
    ("[!] Missing required tool\n", True),
    ("[+] Persisted PATH\n", True),
    ("[dry-run] sudo pacman -S --needed base-devel\n", True),
    ("warning: package slab is yanked\n", True),
    ("error: failed to compile\n", True),
    ("Successfully built dirsearch\n", True),
    ("Already up to date.\n", True),
    ("Installed tools: ffuf, gobuster\n", True),
    ("Active PATH for this run: /home/aops/go/bin:$PATH\n", True),
    ("   Compiling proc-macro2 v1.0.95\n", False),
    ("   Updating crates.io index\n", False),
    ("Requirement already satisfied: pip\n", False),
    ("Building wheels for collected packages: dirsearch\n", False),
    ("\n", False),
])
def test_quiet_keep_regex(line: str, expected: bool) -> None:
    """v0.4.2 (FIX-BBW-J): the --quiet line filter keeps installer status lines
    and error/warning surfaces but drops cargo/pip compile spam."""
    assert bool(QUIET_KEEP_RE.match(line)) is expected


def test_run_installer_uses_streaming_when_quiet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    installer = tmp_path / "fake-installer.sh"
    installer.write_text("#!/bin/sh\nexit 0\n")
    streamed = (
        "[*] Installing base packages with pacman\n"
        "   Compiling proc-macro2 v1.0.95\n"
        "   Compiling libc v0.2.174\n"
        "warning: slab v0.4.10 is yanked\n"
        "[*] Persisting local tool PATH in /home/aops/.zshrc\n"
        "Installed tools: ffuf, gobuster, katana\n"
    )

    class FakePopen:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.stdout = io.StringIO(streamed)

        def wait(self) -> int:
            return 0

    monkeypatch.setattr("bbwebscan.installer.subprocess.Popen", FakePopen)
    args = _args(installer=str(installer), dry_run=True, quiet=True)
    rc = run_installer(args)
    assert rc == 0
    out = capsys.readouterr().out
    # Status, warnings, terminal lines kept:
    assert "Installing base packages" in out
    assert "warning: slab" in out
    assert "Persisting local tool PATH" in out
    assert "Installed tools:" in out
    # Compile spam dropped:
    assert "Compiling proc-macro2" not in out
    assert "Compiling libc" not in out
