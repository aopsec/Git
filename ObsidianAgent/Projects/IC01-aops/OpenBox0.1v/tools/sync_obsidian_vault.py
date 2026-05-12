#!/usr/bin/env python3
"""OpenBox compatibility wrapper for the shared Obsidian agent."""

from __future__ import annotations

import sys
from pathlib import Path

# [FIX-V8] Deduplication: shared resolution logic lives in _agent_path.py.
from _agent_path import shared_agent_root


SHARED_ROOT = shared_agent_root()
if str(SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_ROOT))

from obsidian_agent.cli import main


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".aops-vault.toml"


if __name__ == "__main__":
    # [VAULT-C] Preserve the existing OpenBox entrypoint and default behavior.
    sys.exit(main(default_repo=ROOT, default_config=CONFIG))
