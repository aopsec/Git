import argparse
import os
import re
import subprocess
from pathlib import Path

DEFAULT_INSTALLER_PATH: Path = Path("~/bbScan_Installer.sh").expanduser()
WELL_KNOWN_BIN_DIRS: tuple[Path, ...] = (
    Path.home() / "go" / "bin",
    Path.home() / ".cargo" / "bin",
    Path.home() / ".local" / "bin",
)
PERSIST_MARKER: str = "# [bbwebscan] PATH for recon tools"
# [FIX-BBW-J] Lines kept by `bbwebscan install --quiet`. Status prefixes from the
# bash installer ([*]/[!]/[+]) plus error/warning surfaces from cargo and pip.
QUIET_KEEP_RE: re.Pattern[str] = re.compile(
    r"^(\s*\[(?:[*!+]|dry-run)\]|warning:|error:|Error|"
    r"Successfully|Already|Installed tools:|Active PATH)",
)
# [FIX-BBW-E] The bash installer (~/bbScan_Installer.sh) writes its own marker.
# Recognise either so a user running both `bbwebscan install` and `bbwebscan
# doctor --fix-path` doesn't end up with duplicate PATH-export blocks.
KNOWN_PERSIST_MARKERS: tuple[str, ...] = (
    PERSIST_MARKER,
    "# [FIX-BBR-02] bug bounty web recon tool PATH",
)


def build_install_command(
    installer: Path,
    *,
    dry_run: bool,
    persist_path: bool = True,
    update_nuclei_templates: bool = False,
) -> list[str]:
    cmd = [str(installer)]
    if dry_run:
        cmd.append("--dry-run")
    if persist_path:
        cmd.append("--persist-path")
    if update_nuclei_templates:
        cmd.append("--update-nuclei-templates")
    return cmd


def run_installer(args: argparse.Namespace) -> int:
    installer = Path(args.installer).expanduser() if args.installer else DEFAULT_INSTALLER_PATH
    if not installer.is_file():
        raise FileNotFoundError(
            f"installer not found: {installer}. Provide --installer PATH or place the "
            "script at ~/bbScan_Installer.sh."
        )
    cmd = build_install_command(
        installer,
        dry_run=args.dry_run,
        persist_path=args.persist_path,
        update_nuclei_templates=args.update_nuclei_templates,
    )
    print(f"[bbwebscan install] {' '.join(cmd)}", flush=True)
    if getattr(args, "quiet", False):
        return _stream_filtered(cmd)
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def _stream_filtered(cmd: list[str]) -> int:
    """Run ``cmd`` while suppressing compile spam (Compiling X v1.0 etc.).

    Status lines ([*]/[!]/[+]), warnings, errors, and the installer's final
    "Installed tools" / "Active PATH" lines pass through. Everything else
    is dropped. Exit code is the underlying process's returncode.
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    if proc.stdout is not None:
        for line in proc.stdout:
            if QUIET_KEEP_RE.match(line):
                print(line, end="", flush=True)
    return proc.wait()


def _resolve_rc_path(shell: str | None) -> Path:
    """Pick the user's shell rc file. Honors $ZDOTDIR for zsh."""
    shell_name = shell or os.environ.get("SHELL", "")
    if shell_name.endswith("bash") or shell_name == "bash":
        return Path.home() / ".bashrc"
    zdotdir = os.environ.get("ZDOTDIR")
    return (Path(zdotdir) if zdotdir else Path.home()) / ".zshrc"


def _current_path_dirs() -> set[Path]:
    """Resolved directories present on the current `$PATH`."""
    raw = os.environ.get("PATH", "")
    out: set[Path] = set()
    for entry in raw.split(os.pathsep):
        if not entry:
            continue
        try:
            out.add(Path(entry).resolve())
        except OSError:
            continue
    return out


def persist_path_in_shell_rc(
    *,
    rc_path: Path | None = None,
    shell: str | None = None,
    candidate_dirs: tuple[Path, ...] = WELL_KNOWN_BIN_DIRS,
) -> tuple[Path, list[Path]]:
    """Idempotently prepend missing recon bin dirs to the user's shell rc.

    Returns ``(rc_file, dirs_added)``. ``dirs_added`` is empty when no change
    was needed (marker already present, or no missing dirs).
    """
    target = rc_path if rc_path is not None else _resolve_rc_path(shell)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    if any(marker in existing for marker in KNOWN_PERSIST_MARKERS):
        return (target, [])

    on_path = _current_path_dirs()
    needed = [
        d for d in candidate_dirs
        if d.is_dir() and d.resolve() not in on_path
    ]
    if not needed:
        return (target, [])

    target.parent.mkdir(parents=True, exist_ok=True)
    joined = ":".join(str(d) for d in needed)
    block = "\n".join(["", PERSIST_MARKER, f'export PATH="{joined}:$PATH"', ""])
    suffix = "" if existing.endswith("\n") or not existing else "\n"
    target.write_text(existing + suffix + block, encoding="utf-8")
    return (target, needed)
