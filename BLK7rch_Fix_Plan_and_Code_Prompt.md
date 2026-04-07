# BLK7rch — Project Fix Plan & Code Prompt

**Date:** 2026-04-06 | **Source:** Live screencast + screenshot error analysis

---

## PART 1 — ERROR DIAGNOSIS (from screenshot)

### Exact errors observed (in order):

| # | Command | Location | Error | Root Cause |
|---|---------|----------|-------|------------|
| E1 | `pip install .` | `~/Git/blk7rch/` | `BackendUnavailable: Cannot import 'setuptools.backends.legacy'` | `pyproject.toml` has wrong build-system backend string |
| E2 | `pip install .` | `~/Git/blk7rch/blk7rch/` | `Neither 'setup.py' nor 'pyproject.toml' found` | Wrong directory — `pyproject.toml` is in parent |
| E3 | `pip install .` | `~/Git/blk7rch/blk7rch/installer/` | Same as E2 | Wrong directory |
| E4 | `blk7rch` | `~` | `zsh: command not found: blk7rch` | Package never installed (E1 blocked it) |
| E5 | `python3 __main__.py` | `~/Git/blk7rch/blk7rch/` | `ModuleNotFoundError: No module named 'blk7rch'` | Running script directly; Python's cwd is inside the package, so `from blk7rch.main import main` can't resolve |
| E6 | `python3 main.py` | `~/Git/blk7rch/blk7rch/` | `ModuleNotFoundError: No module named 'blk7rch'` at line 19: `from blk7rch.config.defaults import make_default_config` | Same root cause as E5 |

### Current project tree (confirmed from `ls` output):

```
~/Git/blk7rch/                          ← PROJECT ROOT (has pyproject.toml)
├── CLAUDE.md
├── README.txt
├── pyproject.toml                      ← BROKEN: wrong build backend
├── configs/
├── tests/
└── blk7rch/                            ← PYTHON PACKAGE
    ├── __init__.py
    ├── __main__.py                     ← line 3: from blk7rch.main import main
    ├── main.py                         ← line 19: from blk7rch.config.defaults import ...
    ├── config/
    ├── desktop/
    ├── installer/
    │   ├── __init__.py
    │   ├── chroot_config.py
    │   ├── core.py
    │   ├── disk_setup.py
    │   └── post_install.py
    ├── profiles/
    ├── security/
    ├── tui/
    └── utils/
```

---

## PART 2 — FIX PLAN (7 fixes, execute in order)

### FIX-1: pyproject.toml — wrong build backend

**File:** `~/Git/blk7rch/pyproject.toml`

**Problem:** The `[build-system]` section references `setuptools.backends.legacy` which does not exist in setuptools.

**Fix:** Replace with `setuptools.build_meta`.

```bash
cd ~/Git/blk7rch
sed -i 's/setuptools\.backends\.legacy/setuptools.build_meta/' pyproject.toml
```

**Also verify** the `[build-system]` section looks like:
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

And that `[project.scripts]` or `[project.gui-scripts]` has:
```toml
[project.scripts]
blk7rch = "blk7rch.main:main"
```

---

### FIX-2: Missing `__init__.py` in subpackages

**Problem:** Every subdirectory under `blk7rch/` must have an `__init__.py` to be importable as a Python package. If any are missing, `from blk7rch.config.defaults import ...` will fail with `ModuleNotFoundError`.

**Fix:** Create empty `__init__.py` in every subpackage:

```bash
cd ~/Git/blk7rch
for dir in blk7rch/config blk7rch/desktop blk7rch/installer \
           blk7rch/profiles blk7rch/security blk7rch/tui blk7rch/utils; do
    touch "$dir/__init__.py"
done
```

---

### FIX-3: Missing module files

**Problem:** `main.py` imports `from blk7rch.config.defaults import make_default_config`, but `blk7rch/config/defaults.py` may not exist. Same for other imports.

**Fix:** The code prompt below generates ALL required module files with working implementations.

---

### FIX-4: Install the package in editable mode

**Problem:** Running `python3 main.py` from inside `blk7rch/blk7rch/` fails because Python doesn't know the package root.

**Fix:** After fixing pyproject.toml, install in editable (development) mode:

```bash
cd ~/Git/blk7rch
pip install -e . --break-system-packages
```

This:
- Creates the `blk7rch` CLI command (FIX for E4)
- Makes `from blk7rch.xxx import yyy` work everywhere (FIX for E5, E6)
- Editable mode means code changes take effect immediately

---

### FIX-5: Run correctly

**After installation**, run using either:

```bash
# As CLI command:
blk7rch install --dry-run

# As Python module:
python -m blk7rch install --dry-run

# Or from project root WITHOUT installing:
cd ~/Git/blk7rch
PYTHONPATH=. python -m blk7rch install --dry-run
```

**NEVER** run by doing `cd blk7rch/blk7rch && python3 main.py` — this breaks Python's module resolution.

---

### FIX-6: Verify archinstall is available

**Problem:** The code imports from `archinstall.lib.*` which must be installed.

**Fix:** On Arch ISO, archinstall is pre-installed. On VirtualBox test:

```bash
pacman -Sy archinstall
```

If archinstall is NOT available (testing outside ISO), all archinstall imports must have try/except fallbacks for dry-run mode.

---

### FIX-7: Test complete chain

```bash
cd ~/Git/blk7rch

# 1. Fix pyproject.toml
sed -i 's/setuptools\.backends\.legacy/setuptools.build_meta/' pyproject.toml

# 2. Ensure __init__.py files
for d in blk7rch/{config,desktop,installer,profiles,security,tui,utils}; do
    touch "$d/__init__.py"
done

# 3. Install
pip install -e . --break-system-packages

# 4. Test
blk7rch --help
blk7rch install --dry-run
python -m blk7rch self-test
```

---

## PART 3 — CODE PROMPT

### Prompt for Python — Fix & Complete blk7rch package

**Language:** Python 3.12+ (Arch Linux ISO, Python 3.14 detected from error traceback)  
**Constraint:** Must work on Arch ISO with `archinstall` pre-installed  
**Constraint:** Must also work WITHOUT archinstall in dry-run/self-test mode (graceful fallback)

---

**ROLE:** You are fixing and completing an existing Python project called `blk7rch` at `~/Git/blk7rch/`. The project structure exists but has broken build config and untested module files. You must produce every file needed to make the project installable and runnable.

---

#### CRITICAL RULES

1. **pyproject.toml `build-backend` must be `"setuptools.build_meta"`** — not `setuptools.backends.legacy` (which does not exist)
2. **Every subdirectory under `blk7rch/` must have `__init__.py`** — config, desktop, installer, profiles, security, tui, utils
3. **All imports must use absolute package paths** — `from blk7rch.config.schema import BLK7Config`, never relative
4. **archinstall imports must be wrapped in try/except** — so dry-run and self-test work even without archinstall installed:
   ```python
   try:
       from archinstall.lib.installer import Installer
       HAS_ARCHINSTALL = True
   except ImportError:
       HAS_ARCHINSTALL = False
       Installer = None  # type: ignore
   ```
5. **Entry point must work 3 ways:**
   - `blk7rch` CLI command (via pyproject.toml `[project.scripts]`)
   - `python -m blk7rch` (via `__main__.py`)
   - `PYTHONPATH=. python -m blk7rch` (without install)
6. **No file may exceed 200 lines** — keep modules focused and small
7. **Every function must have a docstring and type hints**

---

#### FILES TO PRODUCE (complete, working, no stubs)

**File 1: `pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "blk7rch"
version = "1.0.3"
description = "Encrypted Arch Linux Pentest Installer built on archinstall"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
archinstall = ["archinstall"]

[project.scripts]
blk7rch = "blk7rch.main:main"

[tool.setuptools.packages.find]
include = ["blk7rch*"]
```

**File 2: `blk7rch/__init__.py`**
```python
"""BLK7rch — Encrypted Arch Linux Pentest Installer."""
__version__ = "1.0.3"
```

**File 3: `blk7rch/__main__.py`**
```python
"""Allow running as: python -m blk7rch"""
from blk7rch.main import main
main()
```

**File 4: `blk7rch/main.py`**
- Must import `argparse`, NOT archinstall at top level
- Subcommands: `install`, `config-init`, `self-test`, `help`
- `install` args: `--config PATH`, `--dry-run`, `--unattended`, `--profile {minimal,core,workstation,pentest}`, `--disk PATH`, `--advanced`
- `config-init` args: `output` (positional, default `blk7rch.json`)
- `self-test`: runs install with `--dry-run` + preset values
- On `install`: load config → if interactive launch TUI menu → validate → run `BLK7Installer.run()`
- Archinstall import must be LAZY (inside function, not at module top), wrapped in try/except

**File 5: `blk7rch/config/__init__.py`** — empty

**File 6: `blk7rch/config/schema.py`**
- `@dataclass` class `BLK7Config` with ALL fields:
  - `disk: str = ""`
  - `hostname: str = "blk7arch"`
  - `username: str = "user"`
  - `timezone: str = "America/Sao_Paulo"`
  - `locale: str = "en_US.UTF-8"`
  - `keymap: str = "us"`
  - `profile: str = "workstation"` (minimal|core|workstation|pentest)
  - `enable_blackarch: bool = False`
  - `enable_ids: bool = False`
  - `ids_home_net: str = "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"`
  - `allow_ssh_inbound: bool = False`
  - `enable_gdm: bool = True`
  - `auto_reboot: bool = True`
  - `root_lv_size: str = "50G"`
  - `swap_lv_size: str = "8G"`
  - `wifi_backend: str = "nm"`
  - `dry_run: bool = False`
  - `unattended: bool = False`
- Validation method `validate()` that checks:
  - hostname matches RFC 952 regex
  - username matches POSIX regex
  - LV sizes match `^[1-9][0-9]*(G|M|T)$`
  - timezone file exists in `/usr/share/zoneinfo/` (skip if dry-run)

**File 7: `blk7rch/config/defaults.py`**
- Function `make_default_config() -> BLK7Config` that returns config with all defaults
- Function `make_pentest_config() -> BLK7Config` that returns pentest preset (enable_blackarch=True, enable_ids=True, profile="pentest")

**File 8: `blk7rch/config/loader.py`**
- Function `load_config(path: Path) -> BLK7Config` — reads JSON, maps to BLK7Config fields
- Function `save_config(config: BLK7Config, path: Path)` — writes JSON
- Function `merge_cli_args(config: BLK7Config, args: argparse.Namespace) -> BLK7Config` — CLI args override config fields

**File 9: `blk7rch/utils/__init__.py`** — empty

**File 10: `blk7rch/utils/logger.py`**
- Class `Logger` with methods: `step()`, `info()`, `ok()`, `warn()`, `error()`
- Each prints colored timestamped output: `[STEP]`, `[INFO]`, `[ OK ]`, `[WARN]`, `[ERR ]`
- Global instance `log = Logger()`

**File 11: `blk7rch/utils/run.py`**
- Function `run_cmd(cmd: list[str], dry_run: bool = False) -> subprocess.CompletedProcess`
- If `dry_run=True`: log `[DRY-RUN] would execute: <cmd>` and return a mock CompletedProcess
- If `dry_run=False`: run `subprocess.run(cmd, check=True, capture_output=True, text=True)`

**File 12: `blk7rch/utils/rollback.py`**
- Class `RollbackStack` with methods:
  - `push(description: str, undo_cmd: list[str])` — record an undo action
  - `execute_rollback(dry_run: bool)` — run all undo actions in reverse order
  - `clear()` — clear the stack (on success)

**File 13: `blk7rch/installer/__init__.py`** — empty

**File 14: `blk7rch/installer/core.py`**
- Class `BLK7Installer`:
  - `__init__(self, config: BLK7Config)`
  - `run(self)` — main method that executes all phases:
    1. Validate config
    2. If not dry_run: check root, check UEFI, check dependencies
    3. Disk setup (call `disk_setup.setup_disk()`)
    4. Base install (call `pacstrap` via `run_cmd`)
    5. Chroot config (call `chroot_config.configure()`)
    6. Apply profiles
    7. Post-install
  - Each phase must be wrapped in try/except with rollback on failure
  - archinstall imports inside methods, not at class level

**File 15: `blk7rch/installer/disk_setup.py`**
- Function `setup_disk(config: BLK7Config, rollback: RollbackStack)`:
  - Partition: `sgdisk --zap-all`, create EFI + LUKS partitions
  - Encrypt: `cryptsetup luksFormat --type luks2`
  - LVM: `pvcreate`, `vgcreate`, `lvcreate` (root, swap, home)
  - Format: `mkfs.fat`, `mkfs.ext4`, `mkswap`
  - Mount: mount all to `/mnt`
  - Each step pushes undo to rollback stack
  - All commands go through `run_cmd(dry_run=config.dry_run)`

**File 16: `blk7rch/installer/chroot_config.py`**
- Function `configure(config: BLK7Config)`:
  - Write locale, hostname, vconsole.conf (using config.keymap)
  - Configure mkinitcpio hooks (encrypt + lvm2)
  - Install and configure GRUB with cryptdevice
  - Enable NetworkManager
  - Create user with wheel group
  - Set passwords via chpasswd
  - Setup UFW

**File 17: `blk7rch/installer/post_install.py`**
- Function `post_install(config: BLK7Config)`:
  - Write transaction log
  - Install post-boot validation systemd service
  - Unmount all (`umount -R /mnt`)
  - Auto-reboot prompt or auto-reboot in unattended mode

**File 18-19: `blk7rch/profiles/__init__.py`** — empty, **`blk7rch/profiles/base.py`**
- Function `install_base_packages(config, dry_run)` — pacstrap base, linux, linux-firmware, lvm2, etc.

**File 20: `blk7rch/profiles/workstation.py`**
- Function `install_workstation(config, dry_run)`:
  - Install: hyprland, waybar, foot, wofi, mako, gdm, xdg-desktop-portal-hyprland, etc.
  - Write Hyprland config (call `desktop.hyprland`)
  - Write Waybar config (call `desktop.waybar`)
  - Setup GDM (call `desktop.gdm`)

**File 21: `blk7rch/profiles/pentest.py`**
- Function `install_pentest(config, dry_run)`:
  - Call `install_workstation()` first
  - Add pentest packages: firefox, nmap, wireshark-qt, htop, tmux, etc.
  - Write pentest Hyprland config (red borders, SUPER+SHIFT launchers)
  - Write pentest Waybar config (IDS alert counter)
  - Install IDS if enabled

**File 22: `blk7rch/profiles/ids.py`**
- Function `install_ids(config, dry_run)`:
  - Install snort + suricata
  - Write snort.conf, threshold.conf, suppress.conf, local.rules
  - Write suricata.yaml, threshold.config, local.rules
  - Enable services

**File 23-24: `blk7rch/security/__init__.py`** — empty, **`blk7rch/security/blackarch.py`**
- Function `install_blackarch(target: str, dry_run: bool)`:
  - curl strap.sh with --max-time 60 --retry 3
  - curl strap.sh.sha256
  - Verify SHA256
  - chmod 0o700
  - arch-chroot execute

**File 25: `blk7rch/security/ufw.py`**
- Function `setup_ufw(config, dry_run)`:
  - ufw default deny incoming / allow outgoing
  - Optional: ufw allow ssh
  - ufw --force enable
  - systemctl enable ufw

**File 26-27: `blk7rch/security/ids_snort.py`**, **`blk7rch/security/ids_suricata.py`**
- Snort: Generate snort.conf with HOME_NET, threshold, suppress, local.rules (SIDs 1000001-1000003)
- Suricata: Generate suricata.yaml, threshold.config, local.rules (SIDs 2100001-2100002)

**File 28: `blk7rch/security/validation.py`**
- Function `install_postboot_service(target, dry_run)` — writes systemd unit + validation script

**File 29-30: `blk7rch/desktop/__init__.py`** — empty, **`blk7rch/desktop/hyprland.py`**
- Function `write_hyprland_config(target, username, keymap, pentest=False)`
- Two variants: base (simple) and pentest (red borders, 10 workspace binds, pentest launchers)

**File 31: `blk7rch/desktop/waybar.py`**
- Function `write_waybar_config(target, username, pentest=False)`
- Pentest variant: IDS alert counter module

**File 32: `blk7rch/desktop/gdm.py`**
- Function `setup_gdm(target, username, dry_run)`
- Enable gdm.service, create hyprland.desktop session, set AccountsService default

**File 33-34: `blk7rch/tui/__init__.py`** — empty, **`blk7rch/tui/menu.py`**
- Function `run_interactive_menu(config: BLK7Config) -> BLK7Config`:
  - Try to import archinstall TUI; if unavailable, use simple input() prompts
  - Menu items: disk, hostname, username, keymap, timezone, locale, profile, blackarch, IDS, security
  - Returns updated config

**File 35: `configs/blk7rch_default.json`**
```json
{
  "profile": "workstation",
  "hostname": "blk7arch",
  "username": "user",
  "timezone": "America/Sao_Paulo",
  "locale": "en_US.UTF-8",
  "keymap": "us",
  "enable_blackarch": false,
  "enable_ids": false,
  "enable_gdm": true,
  "auto_reboot": true,
  "root_lv_size": "50G",
  "swap_lv_size": "8G",
  "allow_ssh_inbound": false,
  "wifi_backend": "nm"
}
```

**File 36: `configs/blk7rch_pentest.json`**
```json
{
  "profile": "pentest",
  "hostname": "blk7arch",
  "username": "user",
  "timezone": "America/Sao_Paulo",
  "locale": "en_US.UTF-8",
  "keymap": "us",
  "enable_blackarch": true,
  "enable_ids": true,
  "enable_gdm": true,
  "auto_reboot": true,
  "root_lv_size": "80G",
  "swap_lv_size": "8G",
  "allow_ssh_inbound": false,
  "wifi_backend": "nm"
}
```

---

#### TESTING PROTOCOL (run these IN ORDER after generating all files)

```bash
# Step 0: Navigate to project root
cd ~/Git/blk7rch

# Step 1: Verify pyproject.toml
grep 'build-backend' pyproject.toml
# MUST show: build-backend = "setuptools.build_meta"

# Step 2: Verify all __init__.py exist
for d in blk7rch/{config,desktop,installer,profiles,security,tui,utils}; do
    test -f "$d/__init__.py" && echo "OK: $d" || echo "MISSING: $d"
done

# Step 3: Syntax check ALL .py files
find blk7rch -name '*.py' -exec python3 -m py_compile {} \;
echo "Syntax check: $?"

# Step 4: Install in editable mode
pip install -e . --break-system-packages
echo "Install: $?"

# Step 5: CLI command works
blk7rch --help
echo "CLI help: $?"

# Step 6: Module mode works
python -m blk7rch --help
echo "Module help: $?"

# Step 7: Self-test (dry-run with preset config)
blk7rch self-test
echo "Self-test: $?"

# Step 8: Dry-run install
blk7rch install --dry-run --profile pentest
echo "Dry-run: $?"

# Step 9: Config init
blk7rch config-init /tmp/test_blk7rch.json
python3 -c "import json; c=json.load(open('/tmp/test_blk7rch.json')); print('Keys:', len(c))"
echo "Config-init: $?"

# Step 10: Import chain verification
python3 -c "
from blk7rch.config.schema import BLK7Config
from blk7rch.config.defaults import make_default_config
from blk7rch.config.loader import load_config, save_config
from blk7rch.utils.logger import log
from blk7rch.utils.run import run_cmd
from blk7rch.utils.rollback import RollbackStack
from blk7rch.installer.core import BLK7Installer
from blk7rch.desktop.hyprland import write_hyprland_config
from blk7rch.security.blackarch import install_blackarch
from blk7rch.profiles.pentest import install_pentest
print('ALL IMPORTS OK')
"
echo "Imports: $?"
```

**ALL 10 steps must return exit code 0. If any fails, fix the specific file and re-run from that step.**

---

#### ITERATION PROTOCOL

1. Generate all files
2. Run syntax check (Step 3) — fix any SyntaxError
3. Run install (Step 4) — fix any packaging error
4. Run import chain (Step 10) — fix any ModuleNotFoundError or ImportError
5. Run self-test (Step 7) — fix any runtime error
6. Run dry-run (Step 8) — fix any logic error
7. Repeat until all 10 steps pass
