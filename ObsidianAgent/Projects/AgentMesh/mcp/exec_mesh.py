#!/usr/bin/env python3
"""AgentMesh executor MCP — exposes the local executor agents as callable tools.

This is the MCP-centric control plane: planners (Claude/Copilot/Cline) dispatch a
sub-task to an executor by calling one of these tools over MCP. Each tool shells out to
the executor's own CLI; output is returned to the planner.

Security: localhost stdio server; commands are fixed argv (no shell) with timeouts.
"""
from __future__ import annotations

import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mesh-executors")

REPO_DEFAULT = "/home/aops/OPia/Git"


def _run(cmd: list[str], timeout: int, cwd: str | None = None) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        return f"[timeout after {timeout}s] {' '.join(cmd[:3])}…"
    except FileNotFoundError as e:
        return f"[error] executable not found: {e}"
    except Exception as e:  # noqa: BLE001 - surface anything to the planner
        return f"[error] {e!r}"
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        out += f"\n[exit {r.returncode}] {(r.stderr or '').strip()[:1500]}"
    return out or "(no output)"


@mcp.tool()
def run_hermes(prompt: str) -> str:
    """Dispatch a one-shot task to the local GPU Hermes agent (hermes3:8b) and return its reply."""
    return _run(["docker", "exec", "hermes", "hermes", "-z", prompt], timeout=300)


@mcp.tool()
def run_opencode(prompt: str, cwd: str = REPO_DEFAULT) -> str:
    """Dispatch a coding task to OpenCode (local qwen2.5-coder via the gateway), run in `cwd`."""
    return _run(["opencode", "run", prompt], timeout=600, cwd=cwd)


@mcp.tool()
def run_openhands(prompt: str) -> str:
    """Dispatch a one-shot task to OpenHands (headless, gateway-backed qwen2.5-coder) and
    return the agent's run output. Runs `openhands.core.main` inside the openhands-app
    container, which spawns its own runtime sandbox; iterations are capped so a runaway task
    can't hang the planner."""
    return _run(
        ["docker", "exec", "openhands-app",
         "python", "-m", "openhands.core.main",
         "--config-file", "/app/config.toml",
         "-i", "30",            # cap agent iterations
         "-t", prompt],
        timeout=900,            # OpenHands runs are long; first run pulls the runtime image
    )


if __name__ == "__main__":
    mcp.run()
