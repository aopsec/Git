"""Unified install planning and apply helpers."""

from __future__ import annotations

import os
from pathlib import Path

from adv7sec_1_0.backends import build_backend_plan
from adv7sec_1_0.executor import execute_host_operations, filter_applied_operations
from adv7sec_1_0.feature_catalog import FeatureSpec, selected_feature_specs
from adv7sec_1_0.generated import build_generated_artifacts, write_generated_artifacts
from adv7sec_1_0.models import InstallOperation, InstallReport, RuntimeTarget
from adv7sec_1_0.preflight import build_install_warnings
from adv7sec_1_0.resources import export_resource_map
from adv7sec_1_0.runtime import build_runtime_operations, create_runtime_directories


def _feature_names(specs: list[FeatureSpec]) -> list[str]:
    return [spec.name for spec in specs]


def _resource_pairs(specs: list[FeatureSpec]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for spec in specs:
        pairs.extend(spec.resources)
    return pairs


def _package_operations(
    target: RuntimeTarget,
    features: list[str],
) -> tuple[list[InstallOperation], list[str]]:
    operations: list[InstallOperation] = []
    warnings: list[str] = []
    backend = build_backend_plan(target)
    for action in backend.package_actions:
        if action.feature not in features:
            continue
        package_summary = ", ".join(action.packages) or action.status
        operations.append(
            InstallOperation(
                kind="package",
                feature=action.feature,
                summary=f"Install packages for {action.feature}: {package_summary}",
                command=action.command,
                environment=action.environment,
            )
        )
        if not action.command:
            warnings.append(f"{action.feature}: {action.status}")
    return operations, warnings


def build_install_report(
    target: RuntimeTarget,
    feature: str,
    root_dir: Path,
    execute: bool,
    confirm: bool = False,
) -> InstallReport:
    """[FIX-UNIFIED-INSTALL] Build the unified install/apply plan for one feature set."""

    specs = selected_feature_specs(feature)
    features = _feature_names(specs)
    operations, warnings = _package_operations(target, features)
    warnings = build_install_warnings(target, features, root_dir, execute, confirm) + warnings
    for spec in specs:
        for source_relative, target_relative in spec.resources:
            operations.append(
                InstallOperation(
                    kind="resource",
                    feature=spec.name,
                    summary=f"Export packaged resource {source_relative}",
                    path=str(root_dir / target_relative),
                )
            )
    for relative_path in build_generated_artifacts(features):
        feature_name = "suricata" if "suricata" in relative_path else "clamav"
        operations.append(
            InstallOperation(
                kind="generated",
                feature=feature_name,
                summary=f"Generate derived config {relative_path}",
                path=str(root_dir / relative_path),
            )
        )
    operations.extend(build_runtime_operations(root_dir, specs))
    for binding in build_backend_plan(target).service_bindings:
        if binding.feature not in features:
            continue
        operations.append(
            InstallOperation(
                kind="service",
                feature=binding.feature,
                summary=f"Enable service {binding.unit}",
                command=binding.enable_command,
            )
        )
    return InstallReport(
        root_dir=str(root_dir),
        execute=execute,
        confirm=confirm,
        features=features,
        operations=operations,
        warnings=warnings,
    )


def apply_install_report(report: InstallReport) -> InstallReport:
    """[FIX-BLOCKING-VALIDATION] Export resources and execute host ops with failure propagation."""

    root_dir = Path(report.root_dir)
    if report.execute and root_dir == Path("/") and os.geteuid() != 0:
        raise RuntimeError("apply install into '/' requires sudo/root")
    if report.execute and root_dir == Path("/") and not report.confirm:
        raise RuntimeError("live apply into '/' requires --yes")
    specs = selected_feature_specs("all")
    selected = [spec for spec in specs if spec.name in report.features]
    exported = set(export_resource_map(root_dir, _resource_pairs(selected)))
    generated = set(write_generated_artifacts(root_dir, report.features))
    directories = set(create_runtime_directories(root_dir, selected))
    filtered = filter_applied_operations(report.operations, exported, generated, directories)
    results = execute_host_operations(report)
    exit_code = 1 if any(result.status == "failed" for result in results) else 0
    return report.model_copy(
        update={"operations": filtered, "results": results, "exit_code": exit_code}
    )
