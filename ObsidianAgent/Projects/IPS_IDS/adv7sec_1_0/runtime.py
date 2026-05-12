"""Runtime directories and validation commands for install/apply."""

from __future__ import annotations

from pathlib import Path

from adv7sec_1_0.feature_catalog import FeatureSpec
from adv7sec_1_0.models import InstallOperation


def build_runtime_operations(root_dir: Path, specs: list[FeatureSpec]) -> list[InstallOperation]:
    """[FIX-FEATURE-CATALOG] Add directory and validation operations from the catalog."""

    operations: list[InstallOperation] = []
    for spec in specs:
        for relative_path, _mode in spec.directories:
            operations.append(
                InstallOperation(
                    kind="directory",
                    feature=spec.name,
                    summary=f"Create runtime directory {relative_path}",
                    path=str(root_dir / relative_path),
                )
            )
        for command in spec.validations:
            operations.append(
                InstallOperation(
                    kind="validate",
                    feature=spec.name,
                    summary=f"Validate {spec.name} runtime",
                    command=command,
                )
            )
    return operations


def create_runtime_directories(root_dir: Path, specs: list[FeatureSpec]) -> list[Path]:
    """[FIX-FEATURE-CATALOG] Materialize runtime directories from the catalog."""

    created: list[Path] = []
    for spec in specs:
        for relative_path, mode in spec.directories:
            target_path = root_dir / relative_path
            target_path.mkdir(parents=True, exist_ok=True)
            target_path.chmod(mode)
            created.append(target_path)
    return created
