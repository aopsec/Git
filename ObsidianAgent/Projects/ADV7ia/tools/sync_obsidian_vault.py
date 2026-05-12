#!/usr/bin/env python3
"""ADV7ia compatibility wrapper for the shared Obsidian agent."""
from __future__ import annotations

import sys
from pathlib import Path

from _agent_path import AgentResolutionError
from _agent_path import shared_agent_root


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".aops-vault.toml"


def main() -> int:
    """Run the shared Obsidian agent CLI with repo-local defaults."""
    try:
        shared_root = shared_agent_root()
    except AgentResolutionError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2

    if str(shared_root) not in sys.path:
        sys.path.insert(0, str(shared_root))

    try:
        from obsidian_agent.cli import main as shared_main
    except ModuleNotFoundError as error:
        print(
            "[ERROR] Failed to import the shared Obsidian agent from "
            f"`{shared_root}`: {error}. Verify that the install contains "
            "`obsidian_agent/cli.py` and `obsidian_agent_cli.py`.",
            file=sys.stderr,
        )
        return 2

    result = shared_main(default_repo=ROOT, default_config=CONFIG)
    return 0 if result is None else int(result)


if __name__ == "__main__":
    raise SystemExit(main())
