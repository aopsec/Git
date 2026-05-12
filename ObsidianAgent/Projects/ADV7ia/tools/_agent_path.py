"""Shared path resolution for the ADV7ia vault wrappers."""
from __future__ import annotations

import os
from pathlib import Path


class AgentResolutionError(RuntimeError):
    """Raised when no valid shared Obsidian agent install can be found."""


def _is_valid_agent_root(path: Path) -> bool:
    """Return whether a candidate path contains the shared CLI and package."""
    return (
        path.is_dir()
        and (path / "obsidian_agent").is_dir()
        and (path / "obsidian_agent" / "cli.py").is_file()
        and (path / "obsidian_agent_cli.py").is_file()
    )


def _candidate_roots(start: Path) -> tuple[Path, ...]:
    """Return unique shared-agent candidate roots in search order."""
    candidates: list[Path] = []
    seen: set[Path] = set()

    env_path = os.environ.get("AOPS_OBSIDIAN_AGENT_HOME")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        candidates.append(candidate)
        seen.add(candidate)

    for base in (start, *start.parents):
        candidate = (base / "plugins" / "aops-agent" / "obsidian-agent").resolve()
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    home_candidate = (Path.home() / "plugins" / "aops-agent" / "obsidian-agent").resolve()
    if home_candidate not in seen:
        candidates.append(home_candidate)

    return tuple(candidates)


# [FIX-ADV7IA-VAULT-01] Validate the shared agent root instead of returning stale paths.
def shared_agent_root() -> Path:
    """Return the absolute path to a valid shared Obsidian agent root."""
    start = Path(__file__).resolve().parent
    checked: list[str] = []

    for candidate in _candidate_roots(start):
        checked.append(str(candidate))
        if _is_valid_agent_root(candidate):
            return candidate

    default_root = Path.home() / "plugins" / "aops-agent" / "obsidian-agent"
    raise AgentResolutionError(
        "No valid shared Obsidian agent install was found. "
        "Expected a directory containing `obsidian_agent/cli.py` and "
        "`obsidian_agent_cli.py`. "
        f"Checked: {', '.join(checked)}. "
        f"Set AOPS_OBSIDIAN_AGENT_HOME to a valid install, for example "
        f"`{default_root}`."
    )
