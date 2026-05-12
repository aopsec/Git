#!/usr/bin/env python3
"""ADV7ia control-mesh CLI wrapper."""
from __future__ import annotations

import sys
from pathlib import Path

# [FIX-ADV7IA-CM-08] Add the repo root so the sibling control package resolves for direct runs.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if __name__ == "__main__":
    try:
        from adv7ia_control.cli import main
    except ModuleNotFoundError as error:
        print(
            "[ERROR] Missing controller dependency: "
            f"{error}. Run `bash tools/control-mesh ...` so the repo-local virtualenv is used."
        )
        raise SystemExit(2) from error
    raise SystemExit(main())
