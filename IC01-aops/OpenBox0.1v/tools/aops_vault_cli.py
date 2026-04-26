#!/usr/bin/env python3
# [VAULT-C] OpenBox wrapper to the shared aops-agent Obsidian agent CLI.
from __future__ import annotations

import sys
from pathlib import Path

# [FIX-V8] Deduplication: shared resolution logic lives in _agent_path.py.
from _agent_path import shared_agent_root


SHARED_ROOT = shared_agent_root()
if str(SHARED_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_ROOT))

from obsidian_agent.cli import main


if __name__ == "__main__":
    sys.exit(main())
