"""Validation checks for the active ADV7Sec 1.0 runtime."""

from __future__ import annotations

from pathlib import Path

from adv7sec_1_0.resources import RESOURCE_RELATIVE_PATHS


def validate_configs(root: Path) -> list[str]:
    """[FIX-ACTIVE-VALIDATE] Validate active packaged resources and basic formats."""
    errors: list[str] = []
    resource_root = root / "adv7sec_1_0/resource_files"
    for rel in RESOURCE_RELATIVE_PATHS:
        path = resource_root / rel
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"required active resource missing or empty: {path.relative_to(root)}")
    for path in list(root.rglob("*.yaml")) + list(root.rglob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "\t" in text:
            errors.append(f"tabs are not allowed in YAML: {path.relative_to(root)}")
        if not text.strip():
            errors.append(f"empty YAML file: {path.relative_to(root)}")
    systemd_root = resource_root / "etc/systemd/system"
    for path in list(systemd_root.glob("*.service")) + list(systemd_root.glob("*.timer")):
        text = path.read_text(encoding="utf-8")
        if "[Unit]" not in text or ("[Service]" not in text and "[Timer]" not in text):
            errors.append(f"invalid active systemd headers: {path.relative_to(root)}")
    return errors
