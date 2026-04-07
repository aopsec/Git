# BLK7rch.py — Architecture Plan & Code Prompt
## archinstall-Based Encrypted Arch Linux Pentest Installer

**Date:** 2026-04-06 | **Iteration:** 3

---

## PART 1 — ARCHINSTALL PROJECT REVIEW

### archinstall Architecture (from official repo analysis)

```
archinstall/
├── __init__.py              # Library entry + run_as_a_module()
├── main.py                  # CLI entry point
├── lib/
│   ├── installer.py         # Installer class — core orchestrator
│   ├── args.py              # ArchConfig, Arguments (Pydantic), ArchConfigHandler
│   ├── global_menu.py       # GlobalMenu — interactive TUI menu builder
│   ├── storage.py           # Global runtime state dict
│   ├── logger.py            # Logger (file + systemd journal)
│   ├── locale.py            # Locale/keyboard listing from system
│   ├── mirrors.py           # Mirrorlist management
│   ├── luks.py              # Luks2 class — LUKS2 encryption lifecycle
│   ├── crypt.py             # Credential encryption
│   ├── packages/            # Package management helpers
│   ├── models/              # Pydantic data models
│   │   ├── bootloader.py    # Bootloader config
│   │   ├── audio_config.py  # Audio config
│   │   ├── users.py         # User model
│   │   ├── network_config.py
│   │   └── ...
│   ├── disk/
│   │   ├── device_handler.py    # DeviceHandler — low-level disk ops via parted
│   │   ├── filesystem_handler.py # FilesystemHandler — high-level disk workflow
│   │   ├── utils.py             # lsblk parsing, partition helpers
│   │   └── ...
│   ├── profile/
│   │   ├── profiles_handler.py  # ProfileHandler — loads/applies profiles
│   │   └── ...
│   └── hardware/
│       ├── __init__.py      # Hardware detection (GPU, CPU, etc.)
│       └── ...
├── tui/                     # TUI framework (curses-based)
│   ├── curses_menu.py       # Menu rendering
│   └── ...
├── scripts/
│   ├── guided.py            # Default guided installer script
│   ├── swiss.py             # Swiss army knife script
│   └── list.py              # Script listing
├── default_profiles/        # Built-in profile definitions
│   ├── desktops/            # KDE, GNOME, Hyprland, Sway, i3...
│   ├── servers/             # httpd, mariadb, docker...
│   └── minimal.py
└── locales/                 # i18n translations (18+ languages)
    ├── languages.json       # Supported language registry
    └── <lang>/LC_MESSAGES/  # Gettext .po/.mo files
```

### Key archinstall APIs we will use:

| API | Module | Purpose |
|-----|--------|---------|
| `Installer` | `lib/installer.py` | Core installation orchestrator — pacstrap, chroot, mkinitcpio, bootloader |
| `ArchConfig` | `lib/args.py` | Configuration dataclass — disk, users, packages, profiles |
| `DeviceHandler` | `lib/disk/device_handler.py` | Disk discovery, partitioning via parted, LUKS encrypt, format |
| `FilesystemHandler` | `lib/disk/filesystem_handler.py` | High-level partition+mount workflow |
| `Luks2` | `lib/luks.py` | LUKS2 create, open, close, key management |
| `GlobalMenu` | `lib/global_menu.py` | Interactive TUI menu system |
| `ProfileHandler` | `lib/profile/profiles_handler.py` | Profile loading and application |
| `locale` helpers | `lib/locale.py` | List keymaps, timezones, locales from system |
| `SysCommand` | `lib/general.py` | Safe subprocess wrapper with logging |
| `hardware` | `lib/hardware/` | GPU/CPU detection for driver packages |

### Why archinstall as the base (not raw bash):

1. **Timezone/keymap/locale menus are already built** — archinstall reads from `/usr/share/kbd/keymaps`, `/usr/share/zoneinfo`, `/etc/locale.gen` natively
2. **Disk management with parted** — no manual sgdisk; proper partition alignment, NVMe/MMC/SCSI handling
3. **LUKS2 + LVM native support** — `Luks2` class + `DeviceHandler` handles encrypt→open→pvcreate→vgcreate→lvcreate
4. **TUI framework** — curses-based menus, accessible, no external deps
5. **Profile system** — extensible, we add a `blk7rch` profile
6. **JSON config import/export** — `--config` + `--creds` for reproducible installs
7. **i18n** — 18+ languages free
8. **Tested on real hardware** — archinstall is the official installer, battle-tested

---

## PART 2 — BLK7rch.py FEATURE MAP

Every feature from the original BLK7ARCHv1_0.sh (1870 lines) + v1.0.3 patch plan, mapped to the new Python architecture.

### Feature Matrix

| # | Feature | Bash Original | Python Implementation |
|---|---------|--------------|----------------------|
| F01 | LUKS2 full-disk encryption | `cryptsetup luksFormat` | `archinstall.lib.luks.Luks2` + `DeviceHandler.encrypt()` |
| F02 | LVM on LUKS (root/swap/home) | Manual `pvcreate/vgcreate/lvcreate` | `archinstall.lib.disk` LVM support |
| F03 | GPT + UEFI + GRUB | `sgdisk` + `grub-install` | `DeviceHandler` + `Installer.add_bootloader()` |
| F04 | Hyprland desktop (pentest-optimized) | `install_workstation_profile()` | Custom profile class `HyprlandPentest` |
| F05 | BlackArch repo bootstrap | `curl strap.sh` + SHA256 verify | `BlackArchBootstrap` class with async verify |
| F06 | IDS/IPS (Snort + Suricata) | `install_ids_profile()` | `IDSProfile` class — config gen, service enable |
| F07 | UFW firewall | chroot `ufw enable` | `Installer.chroot_command()` for ufw setup |
| F08 | Timezone menu | ❌ Missing → PATCH-01 | **FREE** — `archinstall.lib.locale.list_timezones()` |
| F09 | Keymap menu | ❌ Missing → PATCH-02 | **FREE** — `archinstall.lib.locale.list_keyboard_languages()` |
| F10 | Locale menu | ❌ Missing → PATCH-03 | **FREE** — `archinstall.lib.locale.list_locales()` |
| F11 | GDM auto-enable | ❌ Missing → PATCH-04 | `Installer.enable_service('gdm')` |
| F12 | Auto-reboot | ❌ Missing → PATCH-05 | Python `os.system('reboot')` after unmount |
| F13 | Pentest Hyprland config | ❌ Missing → PATCH-06 | `write_pentest_hyprland_config()` |
| F14 | Waybar IDS status | ❌ Missing → PATCH-07 | `write_pentest_waybar_config()` |
| F15 | Dry-run mode | `GLOBAL_DRY_RUN` | `archinstall --dry-run` (built-in) |
| F16 | Config file mode | `load_config_file()` | `archinstall --config` (built-in JSON) |
| F17 | Rollback/cleanup | `cleanup_on_exit()` EXIT trap | Python `try/finally` + `Installer` context manager |
| F18 | Input validation | `validate_hostname/username` | Pydantic models + archinstall validators |
| F19 | Post-boot validation service | `setup_postboot_validation()` | systemd unit + script written via `Installer` |
| F20 | Transaction log | `append_transaction_log()` | archinstall logger + custom log file |
| F21 | Self-test mode | `self-test` subcommand | `--dry-run` with preset config |

---

## PART 3 — PROJECT STRUCTURE

```
blk7rch/
├── pyproject.toml               # Package config (depends on archinstall)
├── README.md
├── LICENSE
│
├── blk7rch/
│   ├── __init__.py              # Version, entry point
│   ├── __main__.py              # python -m blk7rch
│   ├── main.py                  # CLI: blk7rch [install|config-init|self-test|help]
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py            # BLK7Config — Pydantic model extending ArchConfig
│   │   ├── defaults.py          # Default values for all BLK7-specific fields
│   │   └── loader.py            # JSON/TOML config loader + CLI merge
│   │
│   ├── installer/
│   │   ├── __init__.py
│   │   ├── core.py              # BLK7Installer — extends archinstall.Installer
│   │   ├── disk_setup.py        # LUKS2+LVM partition layout builder
│   │   ├── chroot_config.py     # Chroot configuration (locale, hostname, mkinitcpio, GRUB)
│   │   └── post_install.py      # Post-install: passwords, services, reboot
│   │
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── base.py              # BLK7BaseProfile — minimal encrypted install
│   │   ├── workstation.py       # BLK7WorkstationProfile — Hyprland + GDM
│   │   ├── pentest.py           # BLK7PentestProfile — Hyprland-pentest + IDS + BlackArch
│   │   └── ids.py               # IDSProfile — Snort + Suricata config generator
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── blackarch.py         # BlackArchBootstrap — download, verify, install
│   │   ├── ufw.py               # UFW setup helper
│   │   ├── ids_snort.py         # Snort config + rules generator
│   │   ├── ids_suricata.py      # Suricata YAML + rules generator
│   │   └── validation.py        # Post-boot validation service generator
│   │
│   ├── desktop/
│   │   ├── __init__.py
│   │   ├── hyprland.py          # Hyprland config writer (base + pentest variants)
│   │   ├── waybar.py            # Waybar config writer (base + pentest IDS variant)
│   │   └── gdm.py               # GDM setup + session registration
│   │
│   ├── tui/
│   │   ├── __init__.py
│   │   └── menu.py              # BLK7Menu — extends archinstall GlobalMenu with custom items
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # BLK7 logger wrapping archinstall logger
│       ├── rollback.py          # RollbackStack — undo actions on failure
│       └── run.py               # run_cmd() — dry-run aware command executor
│
├── configs/
│   ├── blk7rch_default.json     # Default archinstall-compatible config
│   ├── blk7rch_pentest.json     # Pentest preset config
│   └── blk7rch_minimal.json     # Minimal encrypted install config
│
└── tests/
    ├── test_config.py
    ├── test_profiles.py
    ├── test_ids.py
    ├── test_blackarch.py
    └── test_dry_run.py
```

---

## PART 4 — DETAILED DESIGN

### 4.1 Entry Point (`main.py`)

```python
#!/usr/bin/env python3
"""BLK7rch — Encrypted Arch Linux Pentest Installer built on archinstall."""

import argparse
import sys
from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.config.loader import load_config, merge_cli_args
from blk7rch.installer.core import BLK7Installer
from blk7rch.tui.menu import BLK7Menu
from blk7rch.utils.logger import log

def main():
    parser = argparse.ArgumentParser(prog='blk7rch')
    sub = parser.add_subparsers(dest='command')

    # install
    p_install = sub.add_parser('install')
    p_install.add_argument('--config', type=Path)
    p_install.add_argument('--creds', type=Path)
    p_install.add_argument('--dry-run', action='store_true')
    p_install.add_argument('--unattended', action='store_true')
    p_install.add_argument('--profile', choices=['minimal','core','workstation','pentest'])
    p_install.add_argument('--disk', type=str)
    p_install.add_argument('--advanced', action='store_true')

    # config-init
    p_config = sub.add_parser('config-init')
    p_config.add_argument('output', nargs='?', default='blk7rch.json')

    # self-test
    sub.add_parser('self-test')

    args = parser.parse_args()

    if args.command == 'install':
        run_install(args)
    elif args.command == 'config-init':
        config_init(args.output)
    elif args.command == 'self-test':
        run_self_test()
    else:
        parser.print_help()
```

### 4.2 Config Schema (`config/schema.py`)

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BLK7Config:
    """Extends archinstall ArchConfig with BLK7-specific fields."""
    # Inherited from archinstall (mapped to ArchConfig)
    disk: str = ""
    hostname: str = "blk7arch"
    username: str = "user"
    timezone: str = "America/Sao_Paulo"
    locale: str = "en_US.UTF-8"
    keymap: str = "us"
    bootloader: str = "grub"

    # BLK7-specific
    profile: str = "workstation"           # minimal|core|workstation|pentest
    workstation_mode: str = "base"         # none|base|dev|pentest
    enable_blackarch: bool = False
    enable_ids: bool = False
    ids_home_net: str = "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    ids_snort_profile: str = "balanced"    # balanced|strict
    ids_mode: str = "minimal-local"        # minimal-local|managed-rules
    allow_ssh_inbound: bool = False
    wifi_backend: str = "nm"               # nm|nm-iwd
    enable_gdm: bool = True
    auto_reboot: bool = True
    root_lv_size: str = "50G"
    swap_lv_size: str = "8G"
    encryption_password: Optional[str] = None
    user_password: Optional[str] = None
    root_password: Optional[str] = None
```

### 4.3 Core Installer (`installer/core.py`)

```python
import archinstall
from archinstall.lib.installer import Installer
from archinstall.lib.disk.device_handler import device_handler
from archinstall.lib.disk.filesystem_handler import FilesystemHandler
from archinstall.lib.models.bootloader import Bootloader

from blk7rch.config.schema import BLK7Config
from blk7rch.installer.disk_setup import build_disk_layout
from blk7rch.installer.chroot_config import configure_chroot
from blk7rch.installer.post_install import post_install
from blk7rch.profiles.pentest import BLK7PentestProfile
from blk7rch.profiles.workstation import BLK7WorkstationProfile
from blk7rch.security.blackarch import BlackArchBootstrap
from blk7rch.security.ufw import setup_ufw
from blk7rch.utils.logger import log
from blk7rch.utils.rollback import RollbackStack

class BLK7Installer:
    """Orchestrates the full BLK7ARCH installation using archinstall as backend."""

    def __init__(self, config: BLK7Config, dry_run: bool = False):
        self.cfg = config
        self.dry_run = dry_run
        self.rollback = RollbackStack()
        self.target = Path('/mnt')

    def run(self):
        log.step("BLK7rch installer started")

        # 1. Build disk layout (GPT + EFI + LUKS2 + LVM)
        disk_config = build_disk_layout(self.cfg)

        # 2. Use archinstall's FilesystemHandler
        fs_handler = FilesystemHandler(disk_config, self.cfg.encryption_password)
        fs_handler.perform_filesystem_operations(show_countdown=not self.dry_run)

        # 3. Use archinstall's Installer for base system
        with Installer(self.target, disk_config, ...) as installer:
            installer.mount_ordered_layout()
            installer.minimal_installation(
                hostname=self.cfg.hostname,
                locale_config=LocaleConfiguration(
                    kb_layout=self.cfg.keymap,
                    sys_lang=self.cfg.locale,
                    sys_enc='UTF-8'
                )
            )
            installer.set_timezone(self.cfg.timezone)
            installer.add_bootloader(Bootloader.Grub)

            # 4. User creation
            installer.create_users(...)
            installer.set_root_password(self.cfg.root_password)

            # 5. Apply BLK7 profiles
            self._apply_profiles(installer)

            # 6. Enable services
            installer.enable_service('NetworkManager')
            if self.cfg.enable_gdm:
                installer.enable_service('gdm')

        # 7. Post-install
        post_install(self.cfg, self.target, self.dry_run)

        log.ok("BLK7rch installation complete!")

    def _apply_profiles(self, installer: Installer):
        # Workstation / Pentest
        if self.cfg.profile in ('workstation', 'pentest'):
            ws = BLK7WorkstationProfile(self.cfg, installer)
            ws.install()

        if self.cfg.profile == 'pentest' or self.cfg.enable_ids:
            pentest = BLK7PentestProfile(self.cfg, installer)
            pentest.install()

        # BlackArch
        if self.cfg.enable_blackarch:
            ba = BlackArchBootstrap(installer, self.target)
            ba.install()

        # UFW
        setup_ufw(installer, self.cfg)
```

### 4.4 Disk Setup (`installer/disk_setup.py`)

Uses archinstall's `DiskLayoutConfiguration` to build LUKS2+LVM:

```python
from archinstall.lib.disk import (
    DiskLayoutConfiguration, DiskLayoutType,
    DeviceModification, PartitionModification,
    FilesystemType, Size, Unit, PartitionFlag
)
from archinstall.lib.disk.device_handler import device_handler

def build_disk_layout(cfg: BLK7Config) -> DiskLayoutConfiguration:
    """Build GPT: 512M EFI (fat32) + rest LUKS2→LVM(root+swap+home)."""

    device = device_handler.get_device(Path(cfg.disk))

    # EFI partition: 512 MiB, fat32, /boot, boot flag
    efi = PartitionModification(
        fs_type=FilesystemType.Fat32,
        start=Size(1, Unit.MiB),
        length=Size(512, Unit.MiB),
        mountpoint=Path('/boot'),
        flags=[PartitionFlag.Boot, PartitionFlag.ESP],
    )

    # LUKS partition: rest of disk, ext4 root + swap + home via LVM
    luks = PartitionModification(
        fs_type=FilesystemType.Ext4,  # inner FS after LUKS open
        start=Size(513, Unit.MiB),
        length=Size(0, Unit.Percent, total=100),  # rest
        mountpoint=Path('/'),
        flags=[],
        encrypt=True,
        # LVM volumes configured separately
    )

    mod = DeviceModification(device=device, partitions=[efi, luks])
    return DiskLayoutConfiguration(
        config_type=DiskLayoutType.Default,
        device_modifications=[mod]
    )
```

### 4.5 Profiles

**Workstation Profile (`profiles/workstation.py`):**
```python
class BLK7WorkstationProfile:
    PACKAGES = [
        'hyprland', 'waybar', 'foot', 'wofi', 'mako',
        'xdg-desktop-portal-hyprland', 'xdg-desktop-portal-gtk',
        'xorg-xwayland', 'brightnessctl', 'wl-clipboard', 'gdm',
    ]
    PENTEST_EXTRA = [
        'firefox', 'grim', 'slurp', 'htop', 'nethogs',
        'nmap', 'wireshark-qt', 'python', 'python-pip', 'tmux', 'ranger',
    ]

    def install(self):
        pkgs = self.PACKAGES.copy()
        if self.cfg.profile == 'pentest':
            pkgs.extend(self.PENTEST_EXTRA)
        self.installer.add_additional_packages(pkgs)
        self._write_hyprland_config()
        self._write_waybar_config()
        self._setup_gdm_session()
```

**IDS Profile (`profiles/ids.py`):**
```python
class IDSProfile:
    def install(self):
        self.installer.add_additional_packages(['snort', 'suricata'])
        self._write_snort_config()
        self._write_suricata_config()
        self._write_rules()
        if self.cfg.ids_enable_services:
            self.installer.enable_service('snort')
            self.installer.enable_service('suricata')
```

### 4.6 TUI Menu (`tui/menu.py`)

Extends archinstall's GlobalMenu with BLK7-specific items:

```python
from archinstall.lib.global_menu import GlobalMenu
from archinstall.tui import MenuItemGroup, MenuItem, SelectMenu

class BLK7Menu(GlobalMenu):
    """BLK7 installer menu — adds security/pentest options to archinstall's menu."""

    def setup_selection_menu_options(self):
        # First, inherit all standard archinstall menu items
        super().setup_selection_menu_options()

        # Then add BLK7-specific items
        self._menu_options['blk7_profile'] = MenuItem(
            text='BLK7 Profile',
            action=self._select_blk7_profile,
            preview=lambda: self._config.profile,
        )
        self._menu_options['enable_blackarch'] = MenuItem(
            text='Enable BlackArch',
            action=self._toggle_blackarch,
        )
        self._menu_options['enable_ids'] = MenuItem(
            text='IDS/IPS (Snort+Suricata)',
            action=self._toggle_ids,
        )
        self._menu_options['security_options'] = MenuItem(
            text='Security Options',
            action=self._security_submenu,
        )
```

---

## PART 5 — EXECUTION FLOW

```
User runs: blk7rch install [--profile pentest] [--config file.json]
     │
     ├─→ Parse CLI args
     ├─→ Load config (JSON or defaults)
     ├─→ If interactive: launch BLK7Menu (inherits archinstall TUI)
     │    ├─→ Language selection          (archinstall built-in)
     │    ├─→ Keyboard layout             (archinstall built-in — all keymaps)
     │    ├─→ Timezone                    (archinstall built-in — region→city)
     │    ├─→ Locale                      (archinstall built-in — full list)
     │    ├─→ Disk selection              (archinstall built-in — auto-detect)
     │    ├─→ Encryption password         (archinstall built-in)
     │    ├─→ Hostname/Username/Password  (archinstall built-in)
     │    ├─→ BLK7 Profile               (NEW: minimal|core|workstation|pentest)
     │    ├─→ Enable BlackArch?           (NEW: toggle)
     │    ├─→ Enable IDS?                 (NEW: toggle)
     │    └─→ Security Options            (NEW: submenu — SSH, UFW, IDS tuning)
     │
     ├─→ Validate config
     ├─→ Show summary → Confirm ERASE
     │
     ├─→ PHASE 1: Disk (archinstall DeviceHandler + FilesystemHandler)
     │    ├─→ Partition GPT (EFI + LUKS)
     │    ├─→ cryptsetup luksFormat (via Luks2 class)
     │    ├─→ LVM: pvcreate → vgcreate → lvcreate (root/swap/home)
     │    └─→ mkfs + mount
     │
     ├─→ PHASE 2: Base Install (archinstall Installer)
     │    ├─→ pacstrap base linux linux-firmware lvm2 grub ...
     │    ├─→ genfstab
     │    ├─→ Configure locale, keymap, timezone, hostname
     │    ├─→ mkinitcpio (encrypt + lvm2 hooks)
     │    └─→ grub-install + grub-mkconfig (cryptdevice=UUID)
     │
     ├─→ PHASE 3: Users + Services
     │    ├─→ Create user + wheel group
     │    ├─→ Set passwords (root + user)
     │    ├─→ Enable NetworkManager, GDM
     │    └─→ UFW setup
     │
     ├─→ PHASE 4: Profiles (BLK7-specific)
     │    ├─→ Hyprland + Waybar + config (pentest-optimized if pentest)
     │    ├─→ GDM session registration
     │    ├─→ BlackArch bootstrap (if enabled)
     │    ├─→ Snort + Suricata (if IDS enabled)
     │    └─→ Post-boot validation service
     │
     ├─→ PHASE 5: Finalize
     │    ├─→ Transaction log
     │    ├─→ Unmount all
     │    └─→ Auto-reboot (or prompt)
     │
     └─→ Done
```

---

## PART 6 — WHAT ARCHINSTALL GIVES US FOR FREE

These features from the v1.0.3 patch plan are **no longer needed as custom code**:

| Patch Plan Item | archinstall Equivalent | Status |
|-----------------|----------------------|--------|
| PATCH-01: Timezone menu | `archinstall.lib.locale.list_timezones()` + TUI | ✅ FREE |
| PATCH-02: Keymap menu | `archinstall.lib.locale.list_keyboard_languages()` + TUI | ✅ FREE |
| PATCH-03: Locale menu | `archinstall.lib.locale.list_locales()` + TUI | ✅ FREE |
| Disk auto-detection | `DeviceHandler.devices` | ✅ FREE |
| Partition alignment | `parted` library | ✅ FREE |
| NVMe/MMC handling | `DeviceHandler` path resolution | ✅ FREE |
| JSON config import/export | `--config` + `--creds` | ✅ FREE |
| Dry-run mode | `--dry-run` | ✅ FREE |
| i18n (18 languages) | `archinstall/locales/` | ✅ FREE |
| LUKS2 class | `lib/luks.py` Luks2 class | ✅ FREE |
| Hardware detection | `lib/hardware/` | ✅ FREE |
| Mirror management | `lib/mirrors.py` | ✅ FREE |

---

## PART 7 — CODE GENERATION PROMPT

### Prompt for Python — BLK7rch.py

**Language:** Python 3.12+  
**Framework:** Built on top of the `archinstall` library (official Arch Linux installer)  
**Package name:** `blk7rch`  
**Entry point:** `python -m blk7rch` or `blk7rch` CLI

---

**ROLE:** You are a senior Python developer building `BLK7rch.py`, an encrypted Arch Linux pentest installer that extends the official `archinstall` library. You must produce a complete, working Python package.

---

#### TASK

Write the complete `blk7rch` Python package with the following file structure. Every file must be complete — no placeholders, no `# TODO`, no `pass` stubs. Every function must have a docstring. Type hints on all function signatures.

#### FILE STRUCTURE (produce every file)

```
blk7rch/
├── pyproject.toml
├── blk7rch/__init__.py
├── blk7rch/__main__.py
├── blk7rch/main.py
├── blk7rch/config/__init__.py
├── blk7rch/config/schema.py
├── blk7rch/config/defaults.py
├── blk7rch/config/loader.py
├── blk7rch/installer/__init__.py
├── blk7rch/installer/core.py
├── blk7rch/installer/disk_setup.py
├── blk7rch/installer/chroot_config.py
├── blk7rch/installer/post_install.py
├── blk7rch/profiles/__init__.py
├── blk7rch/profiles/base.py
├── blk7rch/profiles/workstation.py
├── blk7rch/profiles/pentest.py
├── blk7rch/profiles/ids.py
├── blk7rch/security/__init__.py
├── blk7rch/security/blackarch.py
├── blk7rch/security/ufw.py
├── blk7rch/security/ids_snort.py
├── blk7rch/security/ids_suricata.py
├── blk7rch/security/validation.py
├── blk7rch/desktop/__init__.py
├── blk7rch/desktop/hyprland.py
├── blk7rch/desktop/waybar.py
├── blk7rch/desktop/gdm.py
├── blk7rch/tui/__init__.py
├── blk7rch/tui/menu.py
├── blk7rch/utils/__init__.py
├── blk7rch/utils/logger.py
├── blk7rch/utils/rollback.py
├── blk7rch/utils/run.py
├── configs/blk7rch_default.json
├── configs/blk7rch_pentest.json
├── tests/test_config.py
├── tests/test_dry_run.py
```

#### REQUIREMENTS

**1. Core Installer (`installer/core.py`):**
- Class `BLK7Installer` that uses `archinstall.lib.installer.Installer` as the backend
- Method `run()` that executes the full installation in this order:
  1. Validate config (disk exists, sizes valid, hostname/username RFC-compliant)
  2. Build disk layout: GPT → 512M EFI (fat32, /boot) + rest LUKS2 → LVM (root + swap + home)
  3. Use archinstall's `FilesystemHandler.perform_filesystem_operations()`
  4. Use archinstall's `Installer` context manager for pacstrap, genfstab, mkinitcpio, GRUB
  5. Configure locale, keymap, timezone, hostname in chroot using archinstall APIs
  6. Create user with wheel group, set passwords
  7. Apply profiles based on `config.profile`
  8. Post-install: enable services, write logs, unmount, reboot

**2. Disk Setup (`installer/disk_setup.py`):**
- Function `build_disk_layout(cfg: BLK7Config) -> DiskLayoutConfiguration`
- Must use archinstall's `DeviceModification`, `PartitionModification`, `Size`, `Unit`, `FilesystemType`
- EFI: 512 MiB, Fat32, flags=[Boot, ESP], mountpoint=/boot
- LUKS partition: rest of disk, encrypted=True
- LVM volumes: root (cfg.root_lv_size), swap (cfg.swap_lv_size), home (100%FREE)

**3. Profiles:**

- `BLK7BaseProfile`: Minimal packages + NetworkManager + sudo + vim + git + ufw
- `BLK7WorkstationProfile`: Hyprland + Waybar + foot + wofi + mako + GDM + xdg-desktop-portal-hyprland + xorg-xwayland + brightnessctl + wl-clipboard
- `BLK7PentestProfile`: Extends workstation with pentest tools (firefox, grim, slurp, htop, nethogs, nmap, wireshark-qt, tmux, ranger) + pentest Hyprland config + IDS
- `IDSProfile`: Snort + Suricata with full config files (snort.conf, suricata.yaml, threshold, suppress, local.rules with SSH brute-force and ICMP flood detection rules)

**4. Security:**

- `BlackArchBootstrap`: Download strap.sh from blackarch.org, download SHA256, verify integrity, execute in chroot. Must use `--max-time 60 --retry 3` on curl. Must set permissions to 0o700.
- `UFWSetup`: Default deny incoming, allow outgoing, optional SSH allow, force enable, systemctl enable ufw
- `IDSSnortConfig`: Generate snort.conf with HOME_NET variable, threshold.conf, suppress.conf, local.rules (SSH brute-force sid:1000001, ICMP flood sid:1000002, optional RDP sid:1000003 for strict mode). Run `snort -T -c /etc/snort/snort.conf` to validate.
- `IDSSuricataConfig`: Generate suricata.yaml with HOME_NET, af-packet config, eve-log + fast-log outputs, threshold.config, local.rules (SSH sid:2100001, ICMP sid:2100002). Run `suricata -T` to validate. Optional `suricata-update` for managed-rules mode.

**5. Desktop:**

- `HyprlandConfig`: Write `~/.config/hypr/hyprland.conf`. Two variants:
  - **base**: monitor, exec-once waybar+mako, input kb_layout from config.keymap, gaps 5/10, border 2, keybinds SUPER+Return=foot, SUPER+D=wofi, SUPER+Q=killactive, SUPER+M=exit
  - **pentest**: Red/orange gradient border (`rgba(ff0000ee) rgba(ff6600ee) 45deg`), workspace keybinds SUPER+1-0, resize keybinds SUPER+CTRL+arrows, pentest quick-launchers: SUPER+SHIFT+S=Snort tail, SUPER+SHIFT+M=Suricata journal, SUPER+SHIFT+W=Wireshark, SUPER+SHIFT+B=private browser, SUPER+SHIFT+H=htop, SUPER+SHIFT+Return=root terminal. Screenshot bind Print=grim+slurp.
- `WaybarConfig`: Two variants:
  - **base**: workspaces, clock, tray
  - **pentest**: + custom/ids module (IDS alert count from suricata fast.log, 30s interval, 🛡 prefix), + cpu, memory, network modules
- `GDMSetup`: Enable gdm.service, create `/usr/share/wayland-sessions/hyprland.desktop` entry, set default session via AccountsService

**6. TUI (`tui/menu.py`):**
- Class `BLK7Menu` that extends `archinstall.lib.global_menu.GlobalMenu`
- Add menu items: BLK7 Profile (minimal/core/workstation/pentest), Enable BlackArch (toggle), Enable IDS (toggle), Security Options (submenu with SSH, UFW, IDS tuning)
- All archinstall built-in items (language, keymap, timezone, locale, disk, encryption, users) must remain accessible — do NOT remove them

**7. Post-Install (`installer/post_install.py`):**
- Write transaction log to `/var/log/blk7rch-install.log`
- Install post-boot validation systemd service (check cryptdevice in cmdline, NM enabled, fstab present)
- Unmount all with `umount -R /mnt`
- Auto-reboot: in unattended mode, reboot after 5s. In interactive mode, prompt "Reboot now? [Y/n]". In dry-run, log only.

**8. Config (`config/schema.py`):**
- Pydantic `BaseModel` or `@dataclass` for `BLK7Config` with ALL fields from Part 4.2 above
- Validation: hostname RFC 952/1123, username POSIX (lowercase, starts with letter/underscore, max 32), LV sizes match `^[1-9][0-9]*(G|M|T|GiB|MiB|TiB)$`, timezone exists in `/usr/share/zoneinfo`, keymap exists in keymaps list

**9. JSON configs:**
- `blk7rch_default.json`: workstation profile, Hyprland, GDM, no BlackArch, no IDS
- `blk7rch_pentest.json`: pentest profile, Hyprland-pentest, GDM, BlackArch enabled, IDS enabled, SSH denied

#### CONSTRAINTS

- Must import from `archinstall.lib.*` — do NOT reimplement disk handling, LUKS, locale listing, TUI framework, or partitioning
- All archinstall locale/timezone/keymap menus must work without modification — they read from system files
- `set -euo pipefail` equivalent: all subprocess calls must check return codes and raise on failure
- Every file write to the target system must go through the `Installer` chroot or be written to `self.target / path`
- Dry-run mode must never touch disks, never call cryptsetup, never call pacstrap — log all actions with `[DRY-RUN]` prefix
- IDS config files must be byte-for-byte identical to the configs generated by the original BLK7ARCHv1_0.sh (Snort HOME_NET, Suricata YAML structure, rule SIDs)
- BlackArch strap.sh must be SHA256-verified before execution
- All passwords must be cleared from memory after use (del + gc)
- The package must be installable with `pip install .` and runnable with `python -m blk7rch`

#### TESTING CHECKLIST

After generating all files:
1. `python -m py_compile blk7rch/main.py` → no syntax errors across all files
2. `python -m blk7rch self-test` → dry-run completes, exit 0
3. `python -m blk7rch install --dry-run --profile pentest` → logs all phases, no prompts, exit 0
4. `python -m blk7rch config-init test.json && python -c "import json; json.load(open('test.json'))"` → valid JSON
5. `mypy blk7rch/ --ignore-missing-imports` → 0 errors
6. `ruff check blk7rch/` → 0 errors
7. Verify IDS snort.conf contains `var HOME_NET [192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]`
8. Verify suricata.yaml is valid YAML with `python -c "import yaml; yaml.safe_load(...)"`
9. Verify pentest hyprland.conf contains `bind=SUPER+SHIFT,S,exec,foot -e sudo tail -f /var/log/snort/alert.fast`
10. Verify waybar pentest config contains `"custom/ids"` module

#### ITERATION PROTOCOL

After generating all code:
1. Run `py_compile` on every `.py` file
2. Run `mypy` on the package
3. Run `ruff check`
4. If any errors, fix and re-check
5. Run the self-test dry-run
6. If it fails, analyze the traceback, fix, and re-run
7. Repeat until all 10 checklist items pass
