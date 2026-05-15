from __future__ import annotations

from dataclasses import replace

from bbwebscan.config import build_run_config
from bbwebscan.menu_collect import collect_dry_run, collect_targets
from bbwebscan.menu_command import scan_settings_to_args
from bbwebscan.menu_types import (
    InputFunc,
    MenuIO,
    ScanExecutor,
    ScanSettings,
    default_input,
)
from bbwebscan.pipeline import execute_scan


def run_quick_scan(
    io: MenuIO,
    *,
    input_func: InputFunc = default_input,
    scan_executor: ScanExecutor = execute_scan,
) -> int:
    """Quick scan: start with defaults → prompt targets + dry-run → execute.

    Returns 0 on success, non-zero on error.
    """
    settings = ScanSettings()
    targets = collect_targets(settings, input_func)
    dry_run = collect_dry_run(settings, input_func)

    if not targets:
        io.print("[bbwebscan menu] No targets specified")
        return 1

    settings = replace(settings, targets=targets, dry_run=dry_run)

    try:
        config = build_run_config(scan_settings_to_args(settings, dry_run_override=dry_run))
        return scan_executor(config)
    except (FileNotFoundError, ValueError) as exc:
        io.print(f"[bbwebscan menu] {exc}")
        return 2
