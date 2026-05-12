"""ADV7Sec 1.0 package."""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "1.0.0"

_VENDOR_DIR = Path(__file__).resolve().parents[1] / ".vendor"
if _VENDOR_DIR.is_dir():
    sys.path.insert(0, str(_VENDOR_DIR))
