# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_config.py::TestBLK7ConfigValidation::test_invalid_hostname_raises -v

# Self-test (full dry-run of the pentest profile — zero disk ops)
python -m blk7rch self-test

# Dry-run a specific profile without disk writes
python -m blk7rch install --dry-run --profile pentest --disk /dev/sda --unattended

# Generate a config file
python -m blk7rch config-init output.json --profile pentest

# Syntax-check all source files
python -m py_compile blk7rch/**/*.py

# Type-check (archinstall imports are excluded via ignore_missing_imports)
mypy blk7rch/ --ignore-missing-imports

# Lint
ruff check blk7rch/

# Install for development (from the Arch ISO or a venv)
pip install -e .
```

---

## Architecture

BLK7rch is an **Arch Linux installer** — a Python package that wraps the official `archinstall` library to add LUKS2+LVM full-disk encryption, a Hyprland desktop, and pentest/IDS tooling. It is designed to run live on the Arch ISO.

### Three-layer design

```
CLI (main.py)
    └── BLK7Installer (installer/core.py)   ← orchestrator
            ├── archinstall APIs             ← disk/pacstrap/chroot
            │     FilesystemHandler, Installer, DeviceHandler, Luks2
            ├── BLK7-specific code           ← this package
            │     profiles/, security/, desktop/
            └── post_install.py             ← UFW, validation svc, log, reboot
```

### Execution phases (BLK7Installer.run)

| Phase | What happens |
|-------|-------------|
| 0 | Config validation — disk exists, passwords set, hostname/username/LV sizes valid |
| 1 | Disk: GPT + 512 MiB EFI (FAT32) + LUKS2 → LVM (root/swap/home) via `FilesystemHandler` |
| 2 | Base: `archinstall.Installer` context — pacstrap, locale, mkinitcpio, GRUB, users, profiles |
| 3 | Post-install: UFW, post-boot validation service, transaction log, unmount, reboot |

### Profile inheritance

```
BLK7BaseProfile
    └── BLK7WorkstationProfile    (adds Hyprland + Waybar + GDM)
            └── BLK7PentestProfile  (adds pentest tools + IDSProfile)
```

`IDSProfile` is composed (not inherited) — it is triggered by `cfg.enable_ids` or `profile == 'pentest'`, and delegates to `IDSSnortConfig` + `IDSSuricataConfig` to write config files into the chroot target.

### BLK7Config (`config/schema.py`)

Single source of truth for the entire install. Validated `@dataclass` — `__post_init__` enforces every field on construction. Fields fed into config files or subprocesses all have regex validators. Passwords carry `repr=False` and are cleared via `clear_passwords()` immediately after `archinstall.Installer` exits.

### archinstall coupling

All disk operations, pacstrap, genfstab, mkinitcpio, and user creation go through `archinstall` APIs. BLK7rch only writes files into `target / path` (chroot-scoped) and runs commands via `chroot_run()`. The import is guarded with `_ARCHINSTALL_AVAILABLE` throughout — the package can be imported and tested without archinstall present (dry-run mode covers all code paths without it).

### dry_run propagation

`dry_run: bool` flows from `BLK7Installer` into every subsystem. The contract is strict: when `dry_run=True`, **nothing writes to disk and no subprocess executes** — all actions are logged with `log.dry()`. Adding new features must honour this contract. `run_cmd()` and `chroot_run()` in `utils/run.py` are the only subprocess entry points; both short-circuit when `dry_run=True`.

---

## Key Constraints

**IDS config injection** — `ids_home_net` is validated against `_IDS_HOME_NET_RE` (CIDR chars only, no newlines). The same field is double-quote-escaped before being written into `suricata.yaml`. Never interpolate `ids_home_net` into a file without these guards.

**UUID in GRUB cmdline** — `blkid` output is validated against `_UUID_RE` (8-4-4-4-12 hex) before being written into `/etc/default/grub`. The regex is defined in `config/schema.py` and imported by `chroot_config.py`.

**No `shell=True`** — all subprocess calls use list argv. `shlex.split()` is the only accepted way to convert a string command to tokens. All `# noqa: S603` suppressions include a justification comment.

**Exception narrowing** — broad `except Exception` is forbidden. The two archinstall API fallbacks in `chroot_config.py` catch `(ImportError, AttributeError, TypeError)`. The TUI fallback in `main.py` catches `(ImportError, AttributeError, TypeError, RuntimeError)`. Any new broad catch must be justified with a comment.

**File writes in `desktop/`** — always wrap `Path.write_text()` calls in `try/except OSError` and re-raise as `RuntimeError` with context. This ensures the rollback stack in `BLK7Installer` sees the failure.

---

## Testing Strategy

All 42 tests run without archinstall installed and without root. `test_dry_run.py` exercises every subsystem via `dry_run=True`. `test_config.py` covers validation, JSON round-trip, and IDS config content assertions (HOME_NET, Hyprland snort bind, Waybar custom/ids module).

The canonical "does everything work?" check is `python -m blk7rch self-test` — it instantiates a pentest config, runs `BLK7Installer(cfg, dry_run=True).run()`, and exits 0. Add a dry-run test for every new subsystem before adding the real implementation.

---

## Config Files (`configs/`)

Three ready-made JSON presets mirror the three main use cases. They are valid inputs to `--config`. Passwords are intentionally absent — pass them via a separate `--creds` file that is never committed.
