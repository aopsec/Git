"""RollbackStack — registers undo callables executed in LIFO order on failure."""

from __future__ import annotations

import traceback
from collections.abc import Callable

from blk7rch.utils.logger import log


class RollbackStack:
    """Collects rollback actions and executes them in reverse order on demand."""

    def __init__(self) -> None:
        """Initialise an empty rollback stack."""
        self._stack: list[tuple[str, Callable[[], None]]] = []

    def push(self, description: str, action: Callable[[], None]) -> None:
        """Register *action* with a human-readable *description*.

        Actions are executed LIFO (last registered = first to run).
        """
        self._stack.append((description, action))

    def execute(self) -> None:
        """Execute all registered rollback actions in reverse order.

        Exceptions in individual actions are logged but do not stop the
        remaining rollbacks from running.
        """
        if not self._stack:
            return
        log.warn("Running rollback actions …")
        for description, action in reversed(self._stack):
            log.warn(f"  rollback: {description}")
            try:
                action()
            except Exception as exc:  # noqa: BLE001 — rollback actions must not abort remaining actions
                log.error(f"  rollback failed: {description} — {exc}")  # [FIX-V2]
                traceback.print_exc()
        self._stack.clear()

    def clear(self) -> None:
        """Discard all registered rollback actions without executing them."""
        self._stack.clear()

    def __len__(self) -> int:
        """Return the number of pending rollback actions."""
        return len(self._stack)
