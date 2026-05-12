"""Packaged resource access for ADV7Sec 1.0."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Protocol

from adv7sec_1_0 import resource_files

RESOURCE_RELATIVE_PATHS: tuple[str, ...] = (
    "etc/aide/aide.conf",
    "etc/audit/rules.d/50-persistence.rules",
    "etc/falco/falco.local.yaml",
    "etc/falco/rules.d/workstation.yaml",
    "etc/kunai/rules/workstation.kunai",
    "etc/pacman.d/hooks/90-aide-update.hook",
    "etc/suricata/disable.conf",
    "etc/suricata/eve-minimal.yaml",
    "etc/suricata/ipsids-overrides.yaml",
    "etc/systemd/system/aide-check.service",
    "etc/systemd/system/aide-check.timer",
    "etc/systemd/system/chkrootkit.service",
    "etc/systemd/system/chkrootkit.timer",
    "etc/systemd/system/kunai.service",
    "etc/systemd/system/loki-rs-scan.service",
    "etc/systemd/system/loki-rs-scan.timer",
    "etc/systemd/system/lynis-audit.service",
    "etc/systemd/system/lynis-audit.timer",
    "etc/systemd/system/suricata.service.d/ipsids.conf",
    "etc/unbound/unbound.conf.d/dnstap.conf",
    "usr/local/sbin/ipsids-aide-pacman-hook.sh",
    "usr/local/sbin/ipsids-suricata-run.sh",
)


class ResourceTraversable(Protocol):
    """Minimal traversable interface used by importlib.resources."""

    def joinpath(self, *descendants: str) -> ResourceTraversable: ...
    def is_file(self) -> bool: ...
    def read_bytes(self) -> bytes: ...


def _resource_tree() -> ResourceTraversable:
    """Return the traversable root for packaged resources."""
    return files(resource_files)


def _resource_path(relative_path: str) -> ResourceTraversable:
    """Return a traversable resource path."""
    traversable = _resource_tree()
    for part in Path(relative_path).parts:
        traversable = traversable.joinpath(part)
    return traversable


def list_packaged_resources() -> list[str]:
    """Return packaged resources available in the core runtime."""
    available: list[str] = []
    for relative_path in RESOURCE_RELATIVE_PATHS:
        if _resource_path(relative_path).is_file():
            available.append(relative_path)
    return available


def missing_packaged_resources() -> list[str]:
    """Return packaged resources still missing from the core runtime."""
    available = set(list_packaged_resources())
    return [path for path in RESOURCE_RELATIVE_PATHS if path not in available]


def export_packaged_resources(destination: Path) -> list[Path]:
    """Export packaged runtime resources into a filesystem tree."""
    return export_selected_resources(destination, list_packaged_resources())


def export_selected_resources(destination: Path, relative_paths: list[str]) -> list[Path]:
    """[FIX-UNIFIED-INSTALL] Export a selected subset of packaged runtime resources."""
    exported: list[Path] = []
    available = set(list_packaged_resources())
    for relative_path in relative_paths:
        if relative_path not in available:
            continue
        target_path = destination / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(_resource_path(relative_path).read_bytes())
        exported.append(target_path)
    return exported


def export_resource_map(destination: Path, mappings: list[tuple[str, str]]) -> list[Path]:
    """[FIX-UNIFIED-INSTALL] Export packaged resources to explicit install targets."""
    exported: list[Path] = []
    available = set(list_packaged_resources())
    for source_relative, target_relative in mappings:
        if source_relative not in available:
            continue
        target_path = destination / target_relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(_resource_path(source_relative).read_bytes())
        exported.append(target_path)
    return exported
