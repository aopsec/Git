from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from bbwebscan import __version__
from bbwebscan.menu_actions import (
    run_compare_menu,
    run_doctor_auto_fix,
    run_history_menu,
    run_init_menu,
    run_install_menu,
    run_show_menu,
)
from bbwebscan.menu_scan import collect_scan_settings, run_scan_action_menu
from bbwebscan.menu_types import InputFunc, MenuIO, default_input

MenuHandler = Callable[[MenuIO, InputFunc], int]


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
    menu_io = io or RichMenuIO()
    handlers = _menu_handlers()
    while True:
        menu_io.panel(f"bbWebScan v{__version__}", _main_menu_body())
        choice = input_func("Choose [1-8]: ").strip()
        if choice == "8":
            return 0
        handler = handlers.get(choice)
        if handler is None:
            menu_io.print("Choose a number from 1 to 8.")
            continue
        rc = _run_menu_handler(handler, menu_io, input_func)
        if rc is None:
            continue
        if rc != 0:
            return rc


def _menu_handlers() -> dict[str, MenuHandler]:
    return {
        "1": _handle_scan,
        "2": lambda io, input_func: run_doctor_auto_fix(io, input_func=input_func),
        "3": lambda _io, input_func: run_install_menu(input_func=input_func),
        "4": lambda _io, input_func: run_init_menu(input_func=input_func),
        "5": lambda _io, _input_func: run_history_menu(),
        "6": lambda _io, input_func: run_show_menu(input_func=input_func),
        "7": lambda _io, input_func: run_compare_menu(input_func=input_func),
    }


def _handle_scan(io: MenuIO, input_func: InputFunc) -> int:
    settings = collect_scan_settings(input_func=input_func)
    return run_scan_action_menu(settings, io, input_func=input_func)


def _run_menu_handler(handler: MenuHandler, io: MenuIO, input_func: InputFunc) -> int | None:
    try:
        return handler(io, input_func)
    except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
        io.print(f"[bbwebscan menu] {exc}")
        return None


def _main_menu_body() -> str:
    return "\n".join((
        "1. Scan Wizard",
        "2. Doctor / Auto Fix Tools",
        "3. Install Tools",
        "4. Init / Save Profile",
        "5. History",
        "6. Show Run",
        "7. Compare Runs",
        "8. Exit",
    ))


def _print_plain_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    print(f"\n== {title} ==")
    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(row))
