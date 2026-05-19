from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from bbwebscan import __version__
from bbwebscan.menu_actions import run_doctor_auto_fix, run_history_menu
from bbwebscan.menu_custom import run_custom_scan
from bbwebscan.menu_form import run_form_scan
from bbwebscan.menu_profiles import run_profiles_menu
from bbwebscan.menu_quick import run_quick_scan
from bbwebscan.menu_types import InputFunc, MenuIO, default_input
from bbwebscan.pipeline import execute_scan

MenuHandler = Callable[[MenuIO, bool, InputFunc], int]


class RichMenuIO:
    """[MENU-051] Rich renderer with a plain fallback for unbootstrapped venvs."""

    def __init__(self) -> None:
        self._console: Any | None = None
        self._panel: Any | None = None
        self._table: Any | None = None
        try:
            console_mod = importlib.import_module("rich.console")
            panel_mod = importlib.import_module("rich.panel")
            table_mod = importlib.import_module("rich.table")
        except ImportError:
            return
        self._console = console_mod.Console()
        self._panel = panel_mod.Panel
        self._table = table_mod.Table

    def print(self, message: str = "") -> None:
        if self._console is None:
            print(message)
            return
        self._console.print(message)

    def panel(self, title: str, body: str) -> None:
        if self._console is None or self._panel is None:
            print(f"\n== {title} ==\n{body}")
            return
        self._console.print(self._panel(body, title=title, border_style="cyan"))

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        if self._console is None or self._table is None:
            _print_plain_table(title, columns, rows)
            return
        table = self._table(title=title)
        for column in columns:
            table.add_column(column)
        for row in rows:
            table.add_row(*row)
        self._console.print(table)


def run_menu(
    *,
    input_func: InputFunc = default_input,
    io: MenuIO | None = None,
) -> int:
    """Interactive menu with session-wide authorization ack caching."""
    menu_io = io or RichMenuIO()
    handlers = _menu_handlers()
    session_ack = False

    while True:
        menu_io.panel(f"bbWebScan v{__version__}", _main_menu_body())
        choice = input_func("Choose [1-7]: ").strip()

        if choice == "7":
            return 0

        handler = handlers.get(choice)
        if handler is None:
            menu_io.print("Choose a number from 1 to 7.")
            continue

        try:
            rc = handler(menu_io, session_ack, input_func)
            if rc is not None and rc != 0:
                return rc
            # Update session ack if custom scan was run (it may have changed)
            # For now, assume custom scan updates it; in practice users re-ack if needed
        except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
            menu_io.print(f"[bbwebscan menu] {exc}")


def _menu_handlers() -> dict[str, MenuHandler]:
    return {
        "1": lambda io, ack, fn: run_quick_scan(io, input_func=fn),
        "2": lambda io, ack, fn: run_custom_scan(io, session_ack=ack, input_func=fn),
        "3": lambda io, _ack, fn: _run_form_scan_entry(io, fn),
        "4": lambda io, _ack, fn: run_profiles_menu(io, input_func=fn),
        "5": lambda io, _ack, fn: run_doctor_auto_fix(io, input_func=fn),
        "6": lambda io, _ack, _fn: run_history_menu(),
    }


def _run_form_scan_entry(io: MenuIO, input_func: InputFunc) -> int:
    """[v0.5.9] Adapter from ``run_form_scan`` (returns RunConfig|None) to the
    menu handler contract (returns int). Executes the scan via
    :func:`bbwebscan.pipeline.execute_scan` when the wizard yields a config.
    """
    try:
        config = run_form_scan(input_func=input_func)
    except (FileNotFoundError, ValueError) as exc:
        io.print(f"[bbwebscan menu] {exc}")
        return 2
    if config is None:
        return 0
    return execute_scan(config)


def _main_menu_body() -> str:
    return "\n".join((
        "1. Quick Scan",
        "2. Custom Scan",
        "3. Form Scan",
        "4. Manage Profiles",
        "5. Doctor / Auto Fix",
        "6. History",
        "7. Exit",
    ))


def _print_plain_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    print(f"\n== {title} ==")
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(row))
