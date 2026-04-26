"""Shared path resolution for aops vault tooling."""
# [FIX-V8] Extracted from aops_vault_cli.py and sync_obsidian_vault.py — implementations
# were byte-identical. Single source of truth prevents drift.
from __future__ import annotations

import os
from pathlib import Path


def shared_agent_root() -> Path:
    """Return the absolute path to the ObsidianAgent shared agent root.

    Resolution order:
    1. $AOPS_OBSIDIAN_AGENT_HOME env var (explicit override).
    2. Walk up from __file__ looking for plugins/aops-agent/obsidian-agent/.
    3. Fall back to ~/plugins/aops-agent/obsidian-agent/.
    """
    env_path = os.environ.get("AOPS_OBSIDIAN_AGENT_HOME")
    if env_path:
        return Path(env_path).expanduser().resolve()
    start = Path(__file__).resolve().parent
    for base in (start, *start.parents):
        candidate = base / "plugins" / "aops-agent" / "obsidian-agent"
        if candidate.is_dir():
            return candidate.resolve()
    return (Path.home() / "plugins" / "aops-agent" / "obsidian-agent").resolve()
