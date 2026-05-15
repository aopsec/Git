from __future__ import annotations

from dataclasses import replace
from typing import Literal, cast

from bbwebscan.config import build_run_config
from bbwebscan.menu_collect import (
    collect_authorization_ack,
    collect_disable_tools,
    collect_dry_run,
    collect_output_dir,
    collect_rate,
    collect_severity,
    collect_targets,
    collect_threads,
    collect_wordlist,
)
from bbwebscan.menu_command import scan_settings_to_args
from bbwebscan.menu_profile import save_profile_interactive
from bbwebscan.menu_prompts import choice, prompt_bool
from bbwebscan.menu_templates import select_template
from bbwebscan.menu_types import (
    InputFunc,
    MenuIO,
    ScanExecutor,
    ScanSettings,
    default_input,
)
from bbwebscan.pipeline import execute_scan


def run_custom_scan(
    io: MenuIO,
    *,
    session_ack: bool,
    input_func: InputFunc = default_input,
    scan_executor: ScanExecutor = execute_scan,
) -> int:
    """Custom scan: select template → collect settings → action menu.

    Returns 0 on back/success, 2 on error.
    """
    settings = select_template(input_func)
    ack = session_ack

    targets = collect_targets(settings, input_func)
    mode_str = choice(
        "Scan mode", ("safe", "aggressive"), settings.mode, input_func
    )
    mode = cast(Literal["safe", "aggressive"], mode_str)
    ack = collect_authorization_ack(mode, ack, input_func)
    output_dir = collect_output_dir(settings, input_func)
    wordlist = collect_wordlist(settings, input_func)
    disable_tool = collect_disable_tools(settings, input_func)
    severity = collect_severity(settings, input_func)
    threads = collect_threads(settings, input_func)
    rate = collect_rate(settings, input_func)
    dry_run = collect_dry_run(settings, input_func)

    settings = replace(
        settings,
        targets=targets,
        mode=mode,
        ack_authorized=ack,
        output_dir=output_dir,
        wordlist=wordlist,
        disable_tool=disable_tool,
        severity=severity,
        threads=threads,
        rate=rate,
        dry_run=dry_run,
    )

    while True:
        io.panel("Scan Action", _action_menu_body())
        choice_val = input_func("Choose [1-5]: ").strip()

        if choice_val == "1":
            args = scan_settings_to_args(settings, dry_run_override=dry_run)
            io.print(" ".join(args) if isinstance(args, list) else str(args))
        elif choice_val == "2":
            return _run_configured_scan(settings, False, io, scan_executor)
        elif choice_val == "3":
            return _run_configured_scan(settings, True, io, scan_executor)
        elif choice_val == "4":
            if prompt_bool("Save settings as profile", False, input_func):
                try:
                    path = save_profile_interactive(settings, io, input_func=input_func)
                    io.print(f"Saved to {path}")
                except (FileExistsError, ValueError) as exc:
                    io.print(f"[bbwebscan menu] {exc}")
                    return 2
            return 0
        elif choice_val == "5":
            return 0
        else:
            io.print("Choose a number from 1 to 5.")


def _run_configured_scan(
    settings: ScanSettings,
    dry_run: bool,
    io: MenuIO,
    scan_executor: ScanExecutor,
) -> int:
    """Execute the configured scan."""
    try:
        config = build_run_config(scan_settings_to_args(settings, dry_run_override=dry_run))
        return scan_executor(config)
    except (FileNotFoundError, ValueError) as exc:
        io.print(f"[bbwebscan menu] {exc}")
        return 2


def _action_menu_body() -> str:
    """Return the action submenu text."""
    return "\n".join((
        "1. Preview command",
        "2. Run scan",
        "3. Dry-run",
        "4. Save and exit",
        "5. Back to main menu",
    ))
