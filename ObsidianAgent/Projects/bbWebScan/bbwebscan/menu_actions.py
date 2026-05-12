from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from bbwebscan.config import SUPPORTED_TOOLS
from bbwebscan.doctor import doctor_exit_code, run_doctor
from bbwebscan.history import run_compare, run_history, run_show
from bbwebscan.init_profile import run_init
from bbwebscan.installer import run_installer
from bbwebscan.menu_prompts import confirm, split_csv
from bbwebscan.menu_types import InputFunc, MenuIO
from bbwebscan.models import ToolStatus
from bbwebscan.preflight import inventory_tools

CommandRunner = Callable[[argparse.Namespace], int]


def run_doctor_auto_fix(
    io: MenuIO,
    *,
    input_func: InputFunc,
    doctor_runner: CommandRunner = run_doctor,
    installer_runner: CommandRunner = run_installer,
) -> int:
    statuses = inventory_tools(SUPPORTED_TOOLS)
    show_doctor_table(io, statuses)
    path_fix_needed = any(status.path_gap is not None for status in statuses)
    install_needed = any(not status.found and status.path_gap is None for status in statuses)
    suspect = [status.name for status in statuses if status.identity == "suspect"]
    if not path_fix_needed and not install_needed:
        if suspect:
            io.print(f"Suspect identities need manual review: {', '.join(suspect)}")
        return doctor_exit_code(statuses)
    io.panel("Planned Fixes", "\n".join(planned_doctor_fixes(path_fix_needed, install_needed)))
    if not confirm("Run these fix/install actions", input_func):
        return doctor_exit_code(statuses)
    rc = 0
    if path_fix_needed:
        rc = doctor_runner(argparse.Namespace(profile=None, strict_identity=False, fix_path=True))
    if rc == 0 and install_needed:
        rc = installer_runner(installer_args(dry_run=False))
    return rc


def run_install_menu(
    *,
    input_func: InputFunc,
    installer_runner: CommandRunner = run_installer,
) -> int:
    dry_run = confirm("Preview installer only", input_func, default=True)
    update = confirm("Update nuclei templates", input_func, default=False)
    quiet = confirm("Quiet installer output", input_func, default=True)
    return installer_runner(installer_args(dry_run=dry_run, update=update, quiet=quiet))


def run_init_menu(
    *,
    input_func: InputFunc,
    init_runner: CommandRunner = run_init,
) -> int:
    program = input_func("Program name: ").strip()
    targets = split_csv(input_func("Targets (comma-separated): "))
    out_raw = input_func("Output profile path [profiles/<program>.yaml]: ").strip()
    force = confirm("Overwrite existing profile", input_func, default=False)
    out = out_raw or str(Path("profiles") / f"{program}.yaml")
    args = argparse.Namespace(
        program_name=program,
        target=targets,
        out=out,
        force=force,
        ack_authorized=False,
    )
    return init_runner(args)


def run_history_menu() -> int:
    return run_history(argparse.Namespace(limit=20, runs_dir=None, ack_authorized=False))


def run_show_menu(*, input_func: InputFunc) -> int:
    run_dir = input_func("Run directory: ").strip()
    if not run_dir:
        return 0
    return run_show(argparse.Namespace(run_dir=run_dir, ack_authorized=False))


def run_compare_menu(*, input_func: InputFunc) -> int:
    run_a = input_func("Run A directory: ").strip()
    run_b = input_func("Run B directory: ").strip()
    if not run_a or not run_b:
        return 0
    return run_compare(argparse.Namespace(run_a=run_a, run_b=run_b, ack_authorized=False))


def show_doctor_table(io: MenuIO, statuses: list[ToolStatus]) -> None:
    rows: list[list[str]] = []
    for status in statuses:
        rows.append([
            status.name,
            doctor_state(status),
            status.version or "n/a",
            str(status.path or "not on PATH"),
            status.note or "",
        ])
    io.table("Doctor", ["Tool", "State", "Version", "Path", "Note"], rows)


def doctor_state(status: ToolStatus) -> str:
    if not status.found and status.path_gap is not None:
        return "path-gap"
    if not status.found:
        return "missing"
    if status.shadowed_by is not None:
        return "shadowed"
    if status.identity == "suspect":
        return "suspect"
    return "found"


def planned_doctor_fixes(path_fix_needed: bool, install_needed: bool) -> list[str]:
    planned: list[str] = []
    if path_fix_needed:
        planned.append("bbwebscan doctor --fix-path")
    if install_needed:
        planned.append("bbwebscan install")
    return planned


def installer_args(
    *,
    dry_run: bool,
    update: bool = False,
    quiet: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=dry_run,
        persist_path=True,
        update_nuclei_templates=update,
        installer=None,
        quiet=quiet,
        ack_authorized=False,
    )
