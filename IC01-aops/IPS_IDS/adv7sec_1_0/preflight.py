"""Install-time warnings and preflight helpers."""

from __future__ import annotations

import os
from pathlib import Path

from adv7sec_1_0.models import RuntimeTarget


def build_install_warnings(
    target: RuntimeTarget,
    features: list[str],
    root_dir: Path,
    execute: bool,
    confirm: bool,
) -> list[str]:
    """[FIX-UNIFIED-INSTALL] Derive operator warnings before apply."""
    warnings: list[str] = []
    if target.init_system != "systemd":
        warnings.append("Non-systemd target detected; service enable commands are preview-only.")
    if execute and root_dir == Path("/") and os.geteuid() != 0:
        warnings.append("Root privileges are required to apply into '/'.")
    if execute and root_dir == Path("/") and not confirm:
        warnings.append("Live host apply requires --yes to confirm non-interactive execution.")
    if "falco" in features and target.support_tier != "native":
        warnings.append("Falco remains manual outside the native Arch path.")
    if "kunai" in features and target.support_tier == "experimental":
        warnings.append("Kunai packaging remains experimental on this distro tier.")
    if "clamav" in features:
        warnings.append("Review local clamd layout before promoting OnAccess scope on live hosts.")
    return warnings
