"""Host-real execution helpers for unified install/apply."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from adv7sec_1_0.models import InstallOperation, InstallReport, OperationResult

CommandPresence = Callable[[list[str]], bool]
CommandRunner = Callable[[list[str], dict[str, str]], int]
_EXECUTABLE_KINDS = {"package", "service", "validate"}


def _command_present(command: list[str]) -> bool:
    binary = command[0]
    if binary.startswith("/"):
        return Path(binary).exists()
    return shutil.which(binary) is not None


def _run_returncode(command: list[str], environment: dict[str, str]) -> int:
    merged_env = os.environ.copy()
    merged_env.update(environment)
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        env=merged_env,
    )
    return completed.returncode


def _result(
    operation: InstallOperation,
    status: Literal["ok", "failed", "skipped"],
    detail: str,
    returncode: int | None,
    command: list[str] | None = None,
) -> OperationResult:
    return OperationResult(
        kind=operation.kind,
        feature=operation.feature,
        command=operation.command if command is None else command,
        status=status,
        returncode=returncode,
        detail=detail,
    )


def execute_operation_plan(
    operations: list[InstallOperation],
    present: CommandPresence | None = None,
    runner: CommandRunner | None = None,
) -> list[OperationResult]:
    """[FIX-BLOCKING-VALIDATION] Execute planned ops with per-feature failure gating."""

    is_present = _command_present if present is None else present
    run = _run_returncode if runner is None else runner
    blocked_features: set[str] = set()
    daemon_reloaded = False
    results: list[OperationResult] = []
    for operation in operations:
        if operation.kind not in _EXECUTABLE_KINDS or not operation.command:
            continue
        if operation.feature in blocked_features and operation.kind != "package":
            results.append(
                _result(operation, "skipped", "blocked by previous failure for this feature", None)
            )
            continue
        if not is_present(operation.command):
            blocked_features.add(operation.feature)
            results.append(_result(operation, "failed", "required command is missing", 127))
            continue
        if operation.kind == "service" and not daemon_reloaded:
            reload_op = InstallOperation(
                kind="service",
                feature=operation.feature,
                summary="Reload systemd units",
                command=["systemctl", "daemon-reload"],
            )
            if not is_present(reload_op.command):
                blocked_features.add(operation.feature)
                results.append(_result(reload_op, "failed", "required command is missing", 127))
                continue
            reload_code = run(reload_op.command, reload_op.environment)
            results.append(
                _result(
                    reload_op,
                    "ok" if reload_code == 0 else "failed",
                    "daemon reload completed" if reload_code == 0 else "daemon reload failed",
                    reload_code,
                )
            )
            if reload_code != 0:
                blocked_features.add(operation.feature)
                continue
            daemon_reloaded = True
        returncode = run(operation.command, operation.environment)
        if returncode == 0:
            status: Literal["ok", "failed", "skipped"] = "ok"
            detail = f"{' '.join(operation.command)} completed"
        else:
            status = "failed"
            detail = f"{' '.join(operation.command)} failed"
        results.append(_result(operation, status, detail, returncode))
        if returncode != 0:
            blocked_features.add(operation.feature)
    return results


def execute_host_operations(report: InstallReport) -> list[OperationResult]:
    """[FIX-REAL-APPLY] Execute package, service, and validation ops on the live host."""

    if not report.execute or Path(report.root_dir) != Path("/"):
        return []
    if os.geteuid() != 0:
        raise RuntimeError("real apply into '/' requires sudo/root")
    return execute_operation_plan(report.operations)


def filter_applied_operations(
    operations: list[InstallOperation],
    exported: set[Path],
    generated: set[Path],
    directories: set[Path],
) -> list[InstallOperation]:
    """[FIX-REAL-APPLY] Keep only operations that were materialized or intentionally retained."""

    filtered: list[InstallOperation] = []
    for operation in operations:
        if operation.kind not in {"resource", "generated", "directory"} or operation.path is None:
            filtered.append(operation)
            continue
        if operation.kind == "resource":
            selected = exported
        elif operation.kind == "generated":
            selected = generated
        else:
            selected = directories
        if Path(operation.path) in selected:
            filtered.append(operation)
    return filtered
