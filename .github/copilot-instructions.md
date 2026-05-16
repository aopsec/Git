# Copilot Instructions for aopsec/Git

This repository is a multi-project monorepo combining educational coursework, security infrastructure projects, and AI-assisted development tools.

## Repository Structure

### Main Projects

- **`blk7rch/`** — Python-based Arch Linux pentest installer (archinstall-based). Full-disk LUKS2 encryption, Hyprland desktop, optional BlackArch/IDS integration.
- **`ObsidianAgent/`** — Meta-vault for AOPS project orchestration. Generates Obsidian notes across multiple nested projects using `.aops-vault.toml` contracts.
- **`IC01-aops/`** — University coursework umbrella containing:
  - `ADV7ia/` — Local AI stack project (Arch Linux + LM Studio + OpenHands/Aider)
  - `AVAL01-IC/` — Course assignment delivery (HTML/PDF/DOCX with Pandoc pipeline)
  - `IPS_IDS/` — Arch-based IPS/IDS installer (Suricata/Snort)
  - `OpenBox0.1v/` — Debian/Raspbian hardened edge-router reference design (systemd, nftables, Wireguard, Tor, monitoring)
- **`KALInit/`** — Kali Linux initialization scripts
- **`FreeCodeCamp/`, `Python_Essentials_I/`, `Revisao_Prova01/`** — Educational Python coursework
- **Nested in ObsidianAgent/Projects:** `bbWebScan/` (v0.5.2+, active bug-bounty recon tool, Python 3.12+, Pydantic v2, coverage gate 85%)

### Shared Elements

- `.aops-vault.toml` — Vault contract files (in projects and meta-repo) that declare how notes are generated
- `CLAUDE.md` files — AI assistant guidelines at project level (e.g., `ObsidianAgent/CLAUDE.md`, `IC01-aops/AVAL01-IC/CLAUDE.md`, `IC01-aops/IPS_IDS/CLAUDE.md`)
- Obsidian vault (`Vault/` in ObsidianAgent) — manually authored notes + auto-generated indexes and catalogs from source patterns

## Build, Test, and Lint Commands

### blk7rch (Python 3.12+, archinstall-based)

**Location:** `/blk7rch/`

```bash
cd blk7rch

# Install dev dependencies (from pyproject.toml)
pip install -e .

# Run all tests (pytest discovers in ./blk7rch/ and ./tests/)
python -m pytest tests/ -v

# Single test file
python -m pytest tests/test_config.py -v

# Single test function
python -m pytest tests/test_config.py::TestConfigValidation::test_hostname_validation -v

# Syntax check all Python files
python -m py_compile blk7rch/**/*.py

# Type checking (mypy configured in pyproject.toml, python_version=3.12)
mypy blk7rch/

# Linting (ruff, line-length=120, target-version=py312)
ruff check blk7rch/

# Dry-run the installer (no disk writes)
python -m blk7rch install --dry-run --profile pentest --disk /dev/sda

# Self-test (full installer dry-run, exit 0)
python -m blk7rch self-test
```

**Entry point:** `blk7rch.main:main` (defined in pyproject.toml)

### ObsidianAgent (Bash + Python + TOML)

**Location:** `/ObsidianAgent/`

**Environment setup:**
```bash
export AOPS_OBSIDIAN_AGENT_CLI="${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}"
export LC_ALL=C.UTF-8 LANG=C.UTF-8   # Deterministic ordering for globs
```

**Core commands:**
```bash
# Check if vault notes are stale (read-only)
python3 "${AOPS_OBSIDIAN_AGENT_CLI}" --check --repo .

# Regenerate vault notes under Vault/Generated/
python3 "${AOPS_OBSIDIAN_AGENT_CLI}" --sync --repo .

# Full collab stack health check (requires Claude CLI skills)
bash tests/validate-collab-stack.sh

# Validate OpenBox fixture (reference canonical implementation)
bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh       # bash -n + shellcheck + nft + python
bash Projects/OpenBox0.1v/tests/validate-obsidian-vault.sh
bash Projects/OpenBox0.1v/tests/validate-stack.sh        # 10 accumulated checks
```

**Standard vault flow:** `--check` → `--sync` → `--check` (second check must show no stale entries)

**Critical constraint:** The external CLI (`obsidian_agent_cli.py`) is NOT vendored. If `$AOPS_OBSIDIAN_AGENT_CLI` is unset and `$HOME/plugins/aops-agent/obsidian-agent/` doesn't exist, all sync/check commands will fail.

### bbWebScan (Python 3.12+, Pydantic v2, active project)

**Location:** `/ObsidianAgent/Projects/bbWebScan/`

```bash
cd bbWebScan

# Activate venv
source .venv/bin/activate

# Install dev extras (includes pytest, coverage, mypy, ruff)
pip install -e '.[dev,cov]'    # Add ',psl' for publicsuffix2

# Lint (ruff, line-length=120, target-version=py312)
ruff check .

# Type check (mypy --strict)
mypy

# Test suite with coverage enforcement (fail_under=85%)
pytest -q --cov

# Single test
pytest tests/test_stages.py::TestHttpxStage -v

# Version (reads from pyproject.toml via importlib.metadata)
bbwebscan --version

# Health check (readiness of httpx, katana, nuclei, ffuf, katana, amass, kiterunner)
bbwebscan doctor

# History of past runs
bbwebscan history --limit 10

# Scan a target (exit code: 0=ok, 2=tool/wordlist error, 3=findings ≥ severity)
bbwebscan example.com
bbwebscan scan example.com --severity medium

# Dry-run before execution
bbwebscan scan example.com --dry-run
```

**Important:** DNS preflight (`--check-dns`) is non-fatal — failures appear in `summary.md` but don't cause exit code error. Aggressive mode (`--api-discovery`, `--enumerate-subdomains` in intel mode) requires `--ack-authorized`.

**Version tracking:** Single source of truth is `pyproject.toml`. Bump version there, and `tests/test_changelog.py` will fail if CHANGELOG.md isn't updated — this catches version-bump oversights.

### IC01-aops Subprojects

#### AVAL01-IC (HTML → PDF/DOCX pipeline)

**Location:** `/IC01-aops/AVAL01-IC/`

```bash
# Regenerate PDF + DOCX from HTML source
bash build.sh

# Validate HTML syntax
xmllint --noout --html AVAL01-IC.html

# Check file hashes (source of truth)
sha256sum AVAL01-IC.{html,pdf,docx}

# Audit external link status
grep -oE 'https?://[^"<> ]+' AVAL01-IC.html | sort -u | \
  while read u; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 10 "$u")
    printf '%s  %s\n' "$code" "$u"
  done
```

**Note:** Pandoc is optional (not on Arch by default). `build.sh` continues even if pandoc is absent, skipping DOCX with a warning.

#### OpenBox0.1v (Debian/Raspbian edge router)

**Location:** `/IC01-aops/OpenBox0.1v/`

```bash
# Validate installation phases (00–09)
bash tests/ci-syntax-check.sh         # bash -n + shellcheck + nft validation + python checks
bash tests/validate-obsidian-vault.sh # Vault contract check
bash tests/phase-b-vault-tool.sh      # Proof that vault repo is neutral
bash tests/validate-stack.sh          # 10 combined checks (intentional: set -uo pipefail, doesn't abort on first failure)

# Sync vault
python3 tools/sync_obsidian_vault.py --check
python3 tools/sync_obsidian_vault.py --sync
```

**Critical note:** `validate-stack.sh` intentionally uses `set -uo pipefail` (no `-e`), so it accumulates PASS/FAIL instead of aborting. Don't confuse with the root-level `tests/validate-collab-stack.sh`, which uses `set -euo pipefail`.

**Target platform:** Debian/Raspbian only (uses `apt`, not `pacman`). Scripts will not run on Arch without adaptation.

## Key Conventions

### Commit Messages

Use semantic prefixes scoped to the affected subsystem:

```
vault: Update generated indexes
tests: Add validation for OpenBox vault contract
projects/bbwebscan: Bump version to 0.5.2
projects/openbox: Add nftables rule validation
projects/ips_ids: Fix Suricata HOME_NET interpolation
```

For new nested projects, follow `projects/<slug>:` where slug is snake_case (e.g., `projects/adv7ia:`, `projects/ips_ids:`).

### Code Style

- **Python:** ruff (line-length=120) + mypy strict mode where configured
- **Bash:** shellcheck-clean, `set -euo pipefail` (intentional deviations documented)
- **No shell expansion obfuscation:** All subprocess calls use list args, no `shell=True`, no `${var@P}` or dynamic command construction

### Vault and Generated Content

- **`Vault/Generated/` is machine-managed.** Never edit files here by hand. The agent CLI regenerates these.
- **Manual vault notes:** Short names, title-case, link-friendly (e.g., `Vault Home.md`)
- **`.aops-vault.toml` changes:** Declare new catalogs or source patterns carefully. Determinism is enforced — the same repo state must produce byte-identical output.
- **Secrets redaction:** Session logs redacted via `~/plugins/aops-agent/cpr/redact.py`

### Locale Determinism

Always set locale before vault sync to ensure consistent glob ordering:
```bash
export LC_ALL=C.UTF-8 LANG=C.UTF-8
```
Divergence between machines with different locales can reorder catalogs without source changes — this is a known gotcha.

## Architecture Highlights

### ObsidianAgent Meta-Vault

The root `.aops-vault.toml` declares:
- **Project Manifests** (from projects with `.aops-vault.toml`)
- **Project Overviews** (from projects with `README.md`)
- **Session Logs** (from `/compress` skill output)
- **Daily Notes** (manual entries in `Vault/Journal/Daily/`)

Nested projects (ADV7ia, OpenBox0.1v, bbWebScan) can also declare their own catalogs that feed into their respective Obsidian vaults without affecting the meta-vault.

### blk7rch Architecture

```
blk7rch/
├── config/         BLK7Config dataclass, validation, JSON loader
├── installer/      Orchestrator, disk setup, chroot config, post-install
├── profiles/       base, workstation, pentest, ids
├── security/       blackarch, ufw, ids_snort, ids_suricata, validation
├── desktop/        hyprland, waybar, gdm
├── tui/            BLK7Menu (extends archinstall GlobalMenu)
├── utils/          logger, rollback stack, subprocess wrapper
├── main.py         CLI entry point
└── tests/          Disk config validation, dry-run orchestration
```

**Key pattern:** Extensible archinstall-based design. Profiles inherit from a base class; security/desktop modules are pluggable.

### bbWebScan Architecture

```
bbwebscan/
├── stages/         httpx, katana, discovery, params, nuclei (per-stage retry/backoff)
├── __init__.py     Main CLI orchestrator (Rich menus, profile management)
└── tests/fixtures/ JSONL test data
```

**Exit codes:** 0=ok, 2=tool/wordlist error (preflight), 3=findings ≥ severity (CI gate).

## Important Gotchas

1. **ObsidianAgent CLI is external:** `obsidian_agent_cli.py` must be installed separately (typically at `$HOME/plugins/aops-agent/obsidian-agent/`). All vault commands fail if missing.

2. **Claude skills required for full stack validation:** `validate-collab-stack.sh` requires `preserve`, `compress`, `resume`, `collab` skills in `~/.claude/commands/`.

3. **OpenBox is Debian-only:** Installer scripts (bash + pacman) are not portable to Arch. Use `apt`-based systems.

4. **Determinism depends on locale:** Set `LC_ALL=C.UTF-8` before vault operations to ensure consistent ordering.

5. **bbWebScan version gate:** `test_changelog.py` enforces CHANGELOG.md updates when `pyproject.toml` version changes. Forgotten bumps in the changelog will fail CI.

6. **Placeholders in OpenBox configs:** `etc/wireguard/wg0.conf.example` and `etc/monit/monitrc.d/openbox.conf` contain `REPLACE_WITH_*` placeholders. Replace before deployment.

7. **Coverage gate in bbWebScan:** Minimum 85% enforced via `pytest --cov` with `fail_under=85%`.

8. **Secrets in dry-run mode:** bbWebScan masks `Authorization:` and `Cookie:` headers in dry-run output and config snapshots.

## Vault Skills (Claude Commands)

When working with the collab stack, these skills should be available in `~/.claude/commands/`:
- `preserve.md` — Save session state
- `compress.md` — Compact session into session logs (populates `SessionLogs/<project>/`)
- `resume.md` — Restore from checkpoint
- `collab.md` — Multi-agent orchestration
- Optional: `cyberref.md` (Codex-Claude dual-ecosystem for cyber/offensive-security work)

## Testing Notes

- **blk7rch:** Full test suite runs in dry-run mode (zero disk writes). `pytest` is the primary runner.
- **ObsidianAgent:** Vault contracts validated by shell scripts. Test discovery is per-project.
- **OpenBox0.1v:** Tests accumulate PASS/FAIL without aborting (by design). Each `.sh` in `tests/` is independently executable.
- **bbWebScan:** pytest with coverage gate (85%). Single-test execution uses standard pytest filter syntax.

## MCP Server Integration

This repository benefits from Model Context Protocol servers for enhanced capabilities. Configure these in your AI assistant settings:

### Recommended MCP Servers

#### 1. **Filesystem MCP** (Essential)
Best for: Browsing configs, templates, editing installation phases, vault structure

**Use in:**
- `blk7rch/` — explore config/ and profiles/ directories, edit installer stages
- `ObsidianAgent/` — navigate vault structure, update `.aops-vault.toml`
- `OpenBox0.1v/` — manage etc/ configs (nftables, wireguard, systemd units)

**Typical workflow:**
```
filesystem list /blk7rch/configs/
filesystem read /ObsidianAgent/.aops-vault.toml
filesystem write /OpenBox0.1v/etc/wireguard/wg0.conf.example
```

#### 2. **Git MCP** (Essential)
Best for: Understanding repo history, tracing project changes, validating commits

**Use in:**
- `ADV7ia/` — understanding imported state and control-mesh evolution
- Cross-project changes — see which commits touch which domains
- Validating commit message conventions (vault:, tests:, projects/<slug>:)

**Typical workflow:**
```
git log --oneline --all -- ObsidianAgent/Projects/bbWebScan/
git show <commit>  # inspect vault or config changes
git diff HEAD~1    # validate semantic prefix usage
```

**Key pattern:** Many commits in this repo are generated (vault sync) or cross-project. Git MCP helps distinguish machine-generated from human-authored changes.

#### 3. **Bash/Shell MCP** (Conditional—Highly useful)
Best for: Running vault sync/check, tests, and build commands without leaving the context

**Use in:**
- ObsidianAgent vault operations: `bash tests/validate-collab-stack.sh`
- blk7rch dry-run: `python -m blk7rch self-test`
- OpenBox0.1v tests: `bash Projects/OpenBox0.1v/tests/ci-syntax-check.sh`
- bbWebScan single tests: `pytest -q --cov`

**Important safeguards:**
- Shell MCP is read-safe but write-destructive. Use `--dry-run` for all disk operations.
- All blk7rch commands in this repo are safe (they use archinstall's built-in dry-run protection).
- Never run `--sync` without first running `--check` to validate stale entries.
- Test commands are isolated (no persistent side effects).

**Typical workflow:**
```
bash /home/aops/OPia/Git/ObsidianAgent/tests/validate-collab-stack.sh
cd /home/aops/OPia/Git/blk7rch && python -m pytest tests/ -v
export LC_ALL=C.UTF-8 && python3 $AOPS_OBSIDIAN_AGENT_CLI --check --repo /home/aops/OPia/Git/ObsidianAgent
```

#### 4. **Python REPL MCP** (Optional)
Best for: Quick validation of config schemas, testing parsers

**Use in:**
- `blk7rch/config/` — validate BLK7Config dataclass with sample JSON
- `bbWebScan/` — test profile YAML parsing and scope gate logic
- ADV7ia — validate control-mesh JSON policy files

**Typical workflow:**
```python
from blk7rch.config import BLK7Config
import json
cfg = BLK7Config.from_json(open('/path/to/config.json').read())
print(cfg.model_dump_json(indent=2))
```

### When NOT to Use MCP Servers

- **Machine-generated content:** Don't edit `Vault/Generated/` files via MCP. Let the vault CLI regenerate them.
- **Secrets in git:** Never use filesystem MCP to inspect `--creds` JSON files or credential placeholders. Work with `${ENV_VAR}` references only.
- **Interactive installers:** Don't use Bash MCP to interact with prompts (e.g., running `blk7rch install` interactively). Use `--unattended` + config file instead.

### Integration with Existing Workflows

**ObsidianAgent ADV7ia project:** Already declares MCP defaults in `ADV7ia/` tools:
```bash
tools/mcp-filesystem-aider-test      # Defaults to ADV7ia project root
tools/mcp-git-aider-test             # Defaults to ~/openhands-workspace/aider-test
```
If using Copilot with these, follow the tool conventions rather than raw MCP calls.

**bbWebScan profile management:** When modifying profiles YAML:
1. Use filesystem MCP to read/write `~/.bbwebscan/profiles/*.yml`
2. Use Python REPL to validate parsing: `from bbwebscan.profiles import load_profile`
3. Use Bash MCP to test: `bbwebscan scan --profile my-profile --dry-run`

## When to Use Existing Instructions

Some projects have their own detailed guidance:
- **`ObsidianAgent/CLAUDE.md`** — Vault generation, schema, ceremonies
- **`IC01-aops/AVAL01-IC/CLAUDE.md`** — HTML/PDF/DOCX pipeline, rubric mapping
- **`IC01-aops/IPS_IDS/CLAUDE.md`** — Arch-based IPS/IDS installer details
- **`ObsidianAgent/Projects/bbWebScan/README.md`** — Bug-bounty scoping, scope gate enforcement, tool integration

These take precedence over this file for their respective domains.
