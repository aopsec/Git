BLK7rch — Encrypted Arch Linux Pentest Installer
=================================================
Version 1.0.0 | Built on archinstall (official Arch Linux installer library)

OVERVIEW
--------
BLK7rch is a Python-based Arch Linux installer focused on:
  - Full-disk LUKS2 encryption with LVM (root + swap + home volumes)
  - Hyprland Wayland compositor with a pentest-optimised variant
  - BlackArch Linux repository integration (optional)
  - Snort + Suricata IDS/IPS with generated configs (optional)
  - UFW firewall (default deny-incoming policy)
  - Post-boot system validation service

It extends the official archinstall library, inheriting its battle-tested disk
management, TUI framework, locale/timezone menus, and JSON config system.


REQUIREMENTS
------------
  - Arch Linux ISO environment (https://archlinux.org/download/)
  - UEFI firmware (GPT layout, ESP at /boot)
  - Python 3.12+ (included on the Arch ISO)
  - archinstall >= 2.8   (included on the Arch ISO since 2021)
  - Internet connection (for pacstrap and optional BlackArch)
  - Target disk: >= 60 GB recommended for pentest profile


INSTALLATION — QUICK START (from Arch ISO)
------------------------------------------
1. Boot the Arch Linux ISO.

2. Connect to the internet:
     # For WiFi:
     iwctl station wlan0 connect <SSID>
     # For Ethernet: automatic via DHCP

3. Install BLK7rch:
     pacman -Sy python-pip
     pip install git+https://github.com/aops-dev/blk7rch.git
     # -- OR -- clone and install locally:
     git clone <repo-url> /tmp/blk7rch
     cd /tmp/blk7rch
     pip install .

4. Run the interactive installer:
     blk7rch install
     # or with a specific profile:
     blk7rch install --profile pentest

5. Answer the prompts:
     - Disk to install on           (e.g. /dev/sda, /dev/nvme0n1)
     - LUKS2 encryption passphrase  (memorise this — it cannot be recovered)
     - Hostname, username, passwords
     - Timezone, locale, keymap     (inherited from archinstall menus)
     - BLK7 Profile                 (minimal / core / workstation / pentest)
     - Enable BlackArch?            (toggle — pentest preset: ON)
     - Enable IDS/IPS?              (toggle — pentest preset: ON)
     - Security options             (SSH, UFW, IDS HOME_NET, Snort profile)

6. Confirm the "ERASE DISK" prompt and let the installer run.
   The system reboots automatically when finished.


INSTALLATION — UNATTENDED (config file)
----------------------------------------
1. Generate a starter config:
     blk7rch config-init my-install.json

2. Edit the JSON — at minimum set:
     "disk":    "/dev/sda"        <- target block device
     "hostname": "myhostname"
     "username": "myuser"

3. Create a separate credentials file (keep it off the disk):
     echo '{
       "encryption_password": "...",
       "user_password": "...",
       "root_password": "..."
     }' > /tmp/creds.json
     chmod 600 /tmp/creds.json

4. Run unattended:
     blk7rch install --config my-install.json --creds /tmp/creds.json --unattended


INSTALLATION — DRY-RUN (no disk writes)
-----------------------------------------
     blk7rch install --dry-run --profile pentest --disk /dev/sda --unattended
     # or run the built-in self-test:
     blk7rch self-test


PROFILES
--------
  minimal       Base system only: kernel, firmware, NetworkManager, sudo,
                vim, git, ufw. No desktop. Smallest footprint.

  core          Same as minimal. Reserved for future server-role extensions.

  workstation   Base + Hyprland + Waybar + foot terminal + wofi launcher
                + mako notifications + GDM display manager.

  pentest       Workstation + pentest toolset + pentest Hyprland config
                (red/orange borders, security quick-launchers) +
                optional BlackArch repo + optional IDS (Snort + Suricata).


DISK LAYOUT
-----------
  /dev/sdX1   512 MiB   FAT32     /boot  (EFI System Partition)
  /dev/sdX2   rest      LUKS2     (encrypted container)
    └─ LVM PV
       └─ vg0
          ├── root   cfg.root_lv_size (default 50G)   ext4   /
          ├── swap   cfg.swap_lv_size (default 8G)    swap
          └── home   100%FREE                          ext4   /home


FEATURES
--------
  F01  LUKS2 full-disk encryption       archinstall Luks2 class + DeviceHandler
  F02  LVM on LUKS (root/swap/home)     archinstall disk LVM support
  F03  GPT + UEFI + GRUB                DeviceHandler + Installer.add_bootloader()
  F04  Hyprland desktop (two variants)  BLK7WorkstationProfile / BLK7PentestProfile
  F05  BlackArch repo bootstrap         BlackArchBootstrap (SHA256 verified)
  F06  IDS/IPS (Snort + Suricata)       IDSProfile — full config + service enable
  F07  UFW firewall                     setup_ufw() — default deny-incoming
  F08  Timezone menu                    archinstall built-in (all IANA zones)
  F09  Keymap menu                      archinstall built-in (all console keymaps)
  F10  Locale menu                      archinstall built-in (full locale list)
  F11  GDM auto-enable                  GDMSetup + AccountsService session
  F12  Auto-reboot                      Countdown + KeyboardInterrupt cancel
  F13  Pentest Hyprland config          Red/orange borders + security keybinds
  F14  Waybar IDS status widget         custom/ids module (Suricata alert count)
  F15  Dry-run mode                     --dry-run (zero disk writes)
  F16  JSON config import/export        --config / --creds / config-init
  F17  Rollback on failure              RollbackStack (LIFO, umount on error)
  F18  Input validation                 RFC 952/1123 hostname, POSIX username,
                                        LV size regex, profile/mode allowlists
  F19  Post-boot validation service     systemd oneshot — checks cryptdevice,
                                        NM enabled, fstab, LUKS mapper device
  F20  Transaction log                  /var/log/blk7rch-install.log (host + target)
  F21  Self-test mode                   blk7rch self-test (full dry-run, exit 0)


PENTEST PROFILE — INCLUDED PACKAGES
-------------------------------------
  Desktop/WM:   hyprland, waybar, foot, wofi, mako, gdm,
                xdg-desktop-portal-hyprland, xdg-desktop-portal-gtk,
                xorg-xwayland, brightnessctl, wl-clipboard, polkit-gnome,
                grim, slurp

  Pentest:      nmap, wireshark-qt, tcpdump, nethogs, net-tools, iproute2,
                firefox, htop, tmux, ranger, bind, whois, traceroute,
                python, python-pip

  IDS (opt):    snort, suricata

  BlackArch:    Full BlackArch repository (~2900 security tools available
                via pacman after bootstrap)


PENTEST HYPRLAND KEYBINDS
--------------------------
  SUPER+Return        Open foot terminal
  SUPER+SHIFT+Return  Open root terminal (sudo -i)
  SUPER+D             Launcher (wofi)
  SUPER+Q             Kill active window
  SUPER+SHIFT+S       Tail Snort alert log  (sudo tail -f /var/log/snort/alert.fast)
  SUPER+SHIFT+M       Monitor Suricata      (journalctl -fu suricata)
  SUPER+SHIFT+W       Launch Wireshark
  SUPER+SHIFT+B       Firefox private window
  SUPER+SHIFT+H       htop
  Print               Screenshot selection  (grim + slurp → clipboard)
  SUPER+1-0           Switch workspace
  SUPER+CTRL+arrows   Resize active window


IDS CONFIGURATION
-----------------
Snort (/etc/snort/):
  snort.conf        Main config — HOME_NET variable, tap mode, alert_fast output
  threshold.conf    Threshold stubs
  suppress.conf     Suppression stubs
  rules/local.rules SSH brute-force (sid:1000001), ICMP flood (sid:1000002)
                    + RDP brute-force (sid:1000003) in strict mode

Suricata (/etc/suricata/):
  suricata.yaml     Main config — HOME_NET, af-packet, eve-log + fast.log
  threshold.config  Per-rule thresholds for SSH and ICMP rules
  rules/local.rules SSH brute force (sid:2100001), ICMP flood (sid:2100002)

IDS alert count is shown in the Waybar panel (refreshed every 30 s).

DEFAULT HOME_NET: [192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]
Override: set "ids_home_net" in config JSON (CIDR notation only).


CONFIG FILE REFERENCE
----------------------
Field               Default                 Description
----                -------                 -----------
disk                ""                      Block device: /dev/sda, /dev/nvme0n1
hostname            "blk7arch"              System hostname (RFC 952/1123)
username            "user"                  Primary user (POSIX, wheel group)
timezone            "America/Sao_Paulo"     Olson TZ name
locale              "en_US.UTF-8"           System locale
keymap              "us"                    Console keymap
bootloader          "grub"                  grub | systemd-boot
profile             "workstation"           minimal|core|workstation|pentest
workstation_mode    "base"                  none|base|dev|pentest
enable_blackarch    false                   Bootstrap BlackArch repo
enable_ids          false                   Install Snort + Suricata
ids_home_net        "[192.168.0.0/16,...]"  IDS HOME_NET (CIDR, no spaces)
ids_snort_profile   "balanced"              balanced | strict
ids_mode            "minimal-local"         minimal-local | managed-rules
allow_ssh_inbound   false                   UFW allow port 22
wifi_backend        "nm"                    nm | nm-iwd
enable_gdm          true                    Enable GDM service
auto_reboot         true                    Reboot after install
root_lv_size        "50G"                   LVM root LV size
swap_lv_size        "8G"                    LVM swap LV size

Credentials (in separate --creds file):
  encryption_password   LUKS2 passphrase
  user_password         Primary user password
  root_password         Root password


TESTING
-------
  python -m pytest tests/ -v          # Run all 42 tests
  python -m blk7rch self-test         # Full dry-run (pentest profile)
  python -m py_compile blk7rch/**/*.py  # Syntax check all files


PROJECT STRUCTURE
-----------------
  blk7rch/
    config/         BLK7Config dataclass, validation, JSON loader
    installer/      Core orchestrator, disk setup, chroot config, post-install
    profiles/       base, workstation, pentest, ids
    security/       blackarch, ufw, ids_snort, ids_suricata, validation
    desktop/        hyprland, waybar, gdm
    tui/            BLK7Menu (extends archinstall GlobalMenu)
    utils/          logger, rollback stack, subprocess wrapper
  configs/          blk7rch_default.json, blk7rch_pentest.json, blk7rch_minimal.json
  tests/            test_config.py, test_dry_run.py


SECURITY NOTES
--------------
  - All passwords are cleared from memory (None + gc.collect()) after use.
  - Passwords are excluded from transaction logs and config-init output.
  - BlackArch strap.sh is SHA256-verified before execution.
  - UFW default policy: deny incoming, allow outgoing.
  - SSH inbound is DENIED by default (set allow_ssh_inbound=true to enable).
  - All subprocess calls use list arguments — no shell=True, no shell injection.
  - IDS HOME_NET is validated against CIDR notation (brackets, digits, /., commas).
  - Dry-run mode never touches disks, never calls cryptsetup or pacstrap.


LICENSE
-------
  See LICENSE file.
