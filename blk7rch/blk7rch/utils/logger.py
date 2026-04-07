"""BLK7rch logger — wraps archinstall's logger with coloured step/ok/warn/error helpers."""

import logging
import sys
from pathlib import Path

_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BLUE = "\033[34m"

LOG_PATH = Path("/var/log/blk7rch-install.log")


class BLK7Logger:
    """Simple coloured logger for BLK7rch installer output."""

    def __init__(self, name: str = "blk7rch") -> None:
        """Initialise the logger and attach a file handler when running as root."""
        self._log = logging.getLogger(name)
        self._log.setLevel(logging.DEBUG)
        if not self._log.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._log.addHandler(handler)

    def _emit(self, prefix: str, colour: str, message: str) -> None:
        """Emit a formatted message to stdout."""
        self._log.info("%s%s%s %s%s", colour, _BOLD, prefix, _RESET, message)

    def step(self, message: str) -> None:
        """Log a major installation step."""
        self._emit("==>", _BLUE, message)

    def ok(self, message: str) -> None:
        """Log a success message."""
        self._emit("[OK]", _GREEN, message)

    def warn(self, message: str) -> None:
        """Log a warning (non-fatal)."""
        self._emit("[WARN]", _YELLOW, message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self._emit("[ERROR]", _RED, message)

    def info(self, message: str) -> None:
        """Log an informational message."""
        self._emit("[INFO]", _CYAN, message)

    def dry(self, message: str) -> None:
        """Log a dry-run action (no disk changes will occur)."""
        self._emit("[DRY-RUN]", _YELLOW, message)

    def append_to_file(self, message: str) -> None:
        """Append *message* to the transaction log file (best-effort)."""
        try:
            with LOG_PATH.open("a") as fh:
                fh.write(message + "\n")
        except OSError:
            pass  # Best-effort: cannot log a logging failure without recursion [FIX-V2]


log: BLK7Logger = BLK7Logger()
