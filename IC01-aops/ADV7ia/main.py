#!/usr/bin/env python3
"""Minimal runtime entrypoint for ADV7ia."""
from __future__ import annotations

from pathlib import Path


# [FIX-ADV7IA-CM-06] Render the repo-local control-mesh brief when dependencies are present.
def project_status_message() -> str:
    """Return a short runtime status string for the imported project."""
    try:
        from adv7ia_control.render import render_brief
        from adv7ia_control.service import build_mesh_status
        from adv7ia_control.store import discover_root
    except ModuleNotFoundError:
        return "ADV7ia control mesh repo is present. Install project dependencies for live status."
    root = discover_root(Path(__file__).resolve().parent)
    return render_brief(build_mesh_status(root))


def main() -> int:
    """Print the project status string and exit cleanly."""
    print(project_status_message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
