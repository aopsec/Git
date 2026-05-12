"""run_cmd() — dry-run-aware subprocess wrapper with mandatory return-code checking."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from blk7rch.utils.logger import log


class CommandError(RuntimeError):
    """Raised when a subprocess exits with a non-zero return code."""


def run_cmd(
    cmd: str | Sequence[str],
    *,
    dry_run: bool = False,
    check: bool = True,
    capture: bool = False,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute *cmd* as a subprocess.

    Parameters
    ----------
    cmd:
        Command string (passed through ``shlex.split``) or list of tokens.
    dry_run:
        When *True* the command is logged but never executed; a synthetic
        ``CompletedProcess(returncode=0)`` is returned.
    check:
        When *True* (default) a :class:`CommandError` is raised if the
        process exits with a non-zero return code.
    capture:
        When *True* stdout and stderr are captured and returned in the
        ``CompletedProcess`` object.
    cwd:
        Working directory for the subprocess.
    env:
        Optional environment mapping passed to the subprocess.
    """
    if isinstance(cmd, str):
        tokens: list[str] = shlex.split(cmd)
    else:
        tokens = list(cmd)

    display = shlex.join(tokens)

    if dry_run:
        log.dry(display)
        return subprocess.CompletedProcess(args=tokens, returncode=0, stdout="", stderr="")

    log.info(f"$ {display}")

    kwargs: dict = {
        "text": True,
        "cwd": str(cwd) if cwd else None,
        "env": env,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    result = subprocess.run(tokens, **kwargs)  # noqa: S603 — safe: list argv, no shell=True, no user-supplied shell metacharacters

    if check and result.returncode != 0:
        raise CommandError(
            f"Command exited with code {result.returncode}: {display}"
        )

    return result


def chroot_run(
    target: Path,
    cmd: str | Sequence[str],
    *,
    dry_run: bool = False,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run *cmd* inside *target* via ``arch-chroot``.

    Parameters
    ----------
    target:
        Mount point of the installed system (e.g. ``/mnt``).
    cmd:
        Command to execute inside the chroot.
    dry_run:
        Passed through to :func:`run_cmd`.
    check:
        Passed through to :func:`run_cmd`.
    capture:
        Passed through to :func:`run_cmd`.
    """
    if isinstance(cmd, str):
        inner = shlex.split(cmd)
    else:
        inner = list(cmd)

    full_cmd = ["arch-chroot", str(target), *inner]
    return run_cmd(full_cmd, dry_run=dry_run, check=check, capture=capture)
