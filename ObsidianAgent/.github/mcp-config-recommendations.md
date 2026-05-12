# MCP Server Configuration for ObsidianAgent

This guide documents recommended MCP server configurations for enhanced Copilot capabilities in this repository. MCP servers extend Claude's abilities to interact with tools, code, and external systems.

## Quick Setup

Add these MCP servers to your Claude configuration (typically in `~/.claude/mcp-config.json` or your IDE's Copilot settings):

### 1. Python MCP

**Purpose**: Direct Python code execution, package inspection, and REPL support for bbWebScan development.

**Configuration** (example for Claude desktop or IDE):
```json
{
  "mcpServers": {
    "python": {
      "command": "python",
      "args": ["-m", "mcp.server.python"],
      "env": {
        "PYTHONPATH": "/home/aops/openhands-workspace/ObsidianAgent/Projects/bbWebScan:$PYTHONPATH"
      }
    }
  }
}
```

**Use cases**:
- Execute Python snippets in the context of bbWebScan package structure
- Inspect Pydantic models, CLI modules, and test fixtures
- Debug import issues and package dependencies
- Run individual pytest tests interactively

### 2. Bash/Shell MCP

**Purpose**: Execute and understand shell scripts, especially test harness and OpenBox validation scripts.

**Configuration**:
```json
{
  "mcpServers": {
    "bash": {
      "command": "bash",
      "args": ["-i", "-l"]
    }
  }
}
```

**Use cases**:
- Run vault validation scripts (`--check`, `--sync`)
- Execute OpenBox test suite (`phase-b-vault-tool.sh`, `validate-stack.sh`)
- Debug shell script behavior and locale issues (e.g., `LC_ALL=C.UTF-8`)
- Run single bbWebScan tests with pytest

### 3. GitHub MCP

**Purpose**: Access GitHub API for PR/issue context, workflow status, and repository metadata.

**Configuration** (requires GitHub token):
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "<your-github-token>"
      }
    }
  }
}
```

**Use cases**:
- View pull request diffs and review comments
- Check CI workflow status and test results
- Access issue descriptions and linked resources
- Verify commit messages and history (if repo is public or you have access)

## Integration Points

### bbWebScan Python Development

When working in `Projects/bbWebScan/`, the Python MCP server can:
- Execute `from bbwebscan import cli, stages` and inspect modules
- Run `pytest tests/test_<module>.py` directly
- Test configuration via Pydantic models
- Verify coverage reports

**Typical workflow**:
```python
# With Python MCP, you can interactively test:
import sys
sys.path.insert(0, '/home/aops/openhands-workspace/ObsidianAgent/Projects/bbWebScan')
from bbwebscan.cli import main
from bbwebscan.stages import httpx_stage
```

### Vault Synchronization

The Bash MCP server streamlines vault operations:
```bash
export LC_ALL=C.UTF-8 LANG=C.UTF-8
export AOPS_OBSIDIAN_AGENT_CLI="$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py"
python3 "$AOPS_OBSIDIAN_AGENT_CLI" --check --repo .
```

### Test Execution

Run test suites with immediate feedback:
```bash
# OpenBox fixture validation
bash Projects/OpenBox0.1v/tests/phase-b-vault-tool.sh

# bbWebScan linting + typing + tests
cd Projects/bbWebScan && ruff check . && mypy && pytest -q --cov
```

## Important Notes

- **Python MCP paths**: Ensure `PYTHONPATH` is set correctly to include `Projects/bbWebScan` for proper package imports.
- **Locale consistency**: Always set `LC_ALL=C.UTF-8` in bash sessions to ensure deterministic vault generation.
- **GitHub token security**: Use environment variables or secure credential storage; never commit tokens.
- **Shell environment**: Use `-i -l` flags for Bash MCP to load your shell profile and environment setup.

## Verification

After configuring MCP servers, verify they're working:

**Python**:
```python
import bbwebscan
print(bbwebscan.__version__)
```

**Bash**:
```bash
echo $LC_ALL && python3 --version && bash --version
```

**GitHub** (if configured):
- Use the MCP to query your own repository or a public repo

## Disabling MCP Servers

If you need to work without MCP servers (e.g., in a restricted environment):
1. Remove or comment out the server entries in your MCP config
2. Copilot will fall back to file-based analysis
3. You can still manually run commands using the CLI directly

Refer to `.github/copilot-instructions.md` for the full repository guide.
