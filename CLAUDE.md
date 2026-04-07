# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Overview

Two parallel installers targeting the same goal — Arch Linux with LUKS2+LVM encryption, Hyprland desktop, and optional pentest/IDS tooling:

| Component | Language | Entry point | Status |
|---|---|---|---|
| `BLK7ARCHv1_0.sh` | Bash | `bash BLK7ARCHv1_0.sh install` | Production (Pass 4, 100/100) |
| `blk7rch/` | Python 3.12+ | `python -m blk7rch install` | Development package |

The bash installer is standalone and self-contained. The Python package wraps the `archinstall` library and mirrors the same feature set with a richer architecture. Both share the same security model and input-validation rules.

---

## Bash Installer — `BLK7ARCHv1_0.sh`

### Common commands

```bash
# Syntax check
bash -n BLK7ARCHv1_0.sh && echo OK

# Lint (requires shellcheck)
shellcheck -S style BLK7ARCHv1_0.sh

# Dry-run self-test (safe, no root, no disk writes)
bash BLK7ARCHv1_0.sh self-test

# Interactive install
bash BLK7ARCHv1_0.sh install

# Unattended install from config
bash BLK7ARCHv1_0.sh install --config install.conf --unattended

# Generate starter config
bash BLK7ARCHv1_0.sh config-init

# Validate input sanitisation (all must exit 5 or 2)
bash BLK7ARCHv1_0.sh install --dry-run --disk /dev/null --hostname 'bad;host' --username u --yes 2>&1; echo "E:$?"
```

### VM integration tests (requires QEMU + Arch ISO + KVM)

```bash
cd tests/vm
./setup.sh
./run-tests.sh --dry-only   # fast (~3 min)
./run-tests.sh              # full install (~40 min)
```

### Key invariants

- All `printf`-based log functions use `%b`/`%s` — never interpolate user input as the format string.
- No passphrase is ever passed as a CLI argument; always via stdin pipe, then `unset`.
- `choose_from_menu()` sends all display output to stderr — it is always called as `$(...)` to capture its return value on stdout.
- IDS dry-run path: `install_ids_profile()` must return early before any `arch-chroot` call when `GLOBAL_DRY_RUN=true`.
- `_to_gib()` is a top-level function (not nested) to avoid bash global namespace pollution.

---

## Python Package — `blk7rch/`

See `blk7rch/CLAUDE.md` for full architecture, key constraints, and testing strategy. Quick reference:

```bash
cd blk7rch

# Run all tests (no root, no archinstall required)
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_config.py::TestBLK7ConfigValidation::test_invalid_hostname_raises -v

# Full dry-run smoke test
python -m blk7rch self-test

# Lint / type-check
ruff check blk7rch/
mypy blk7rch/ --ignore-missing-imports
```

> **Known issue:** `pyproject.toml` line 3 has `build-backend = "setuptools.backends.legacy:build"` — this backend does not exist. The correct value is `"setuptools.build_meta"`. Fix before running `pip install` or building a wheel.

---

## Shared Security Model

Both installers enforce the same validation rules; keep them in sync when modifying either:

| Field | Rule |
|---|---|
| Hostname | RFC 952/1123 regex; no shell metacharacters |
| Username | POSIX regex (`[a-z_][a-z0-9_-]*`) |
| LV sizes | `[1-9][0-9]*(G\|M\|T\|GiB\|MiB\|TiB)` |
| `ids_home_net` | CIDR charset only — validated before writing into `suricata.yaml` |
| LUKS UUID in GRUB cmdline | 8-4-4-4-12 hex (`_UUID_RE`) — validated before writing `/etc/default/grub` |

No `shell=True` (Python) / unquoted variable expansion (Bash) in any code path that touches user-supplied input.
