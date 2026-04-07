"""BLK7Config — validated configuration dataclass for the BLK7rch installer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_HOSTNAME_RE = re.compile(
    r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)$"
)
_USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_LV_SIZE_RE = re.compile(r"^[1-9][0-9]*(G|M|T|GiB|MiB|TiB)$")
_VALID_PROFILES = {"minimal", "core", "workstation", "pentest"}
_VALID_BOOTLOADERS = {"grub", "systemd-boot"}
_VALID_IDS_MODES = {"minimal-local", "managed-rules"}
_VALID_IDS_SNORT_PROFILES = {"balanced", "strict"}
_VALID_WIFI_BACKENDS = {"nm", "nm-iwd"}
# Mirrors the bash validation from BLK7ARCHv1_0.sh:
#   [[ "$IDS_HOME_NET" =~ ^[\[\]0-9./:,\ a-fA-F!]+$ ]]
# Allows only CIDR characters: brackets, digits, dots, slashes, colons, commas,
# spaces, hex letters (IPv6), and negation (!). Newlines are explicitly excluded.
_IDS_HOME_NET_RE = re.compile(r"^[\[\]0-9./:, a-fA-F!]+$")
# UUID format returned by blkid: 8-4-4-4-12 hex digits
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _validate_hostname(value: str) -> str:
    """Validate RFC 952/1123 hostname; raise ValueError on failure."""
    if not value or not _HOSTNAME_RE.match(value):
        raise ValueError(
            f"Invalid hostname '{value}'. Must match RFC 952/1123 "
            "(1-63 alphanumeric/hyphen chars, no leading/trailing hyphen)."
        )
    return value


def _validate_username(value: str) -> str:
    """Validate POSIX username; raise ValueError on failure."""
    if not _USERNAME_RE.match(value):
        raise ValueError(
            f"Invalid username '{value}'. Must start with a letter or underscore, "
            "contain only [a-z0-9_-], max 32 characters."
        )
    return value


def _validate_lv_size(name: str, value: str) -> str:
    """Validate a LVM logical volume size string; raise ValueError on failure."""
    if not _LV_SIZE_RE.match(value):
        raise ValueError(
            f"Invalid LV size for '{name}': '{value}'. "
            "Expected format: <number>(G|M|T|GiB|MiB|TiB), e.g. 50G."
        )
    return value


def _validate_timezone(value: str) -> str:
    """Check that the timezone exists under /usr/share/zoneinfo."""
    tz_path = Path("/usr/share/zoneinfo") / value
    if not tz_path.exists():
        raise ValueError(
            f"Timezone '{value}' not found under /usr/share/zoneinfo."
        )
    return value


def _validate_keymap(value: str) -> str:
    """Accept any non-empty keymap string (validation deferred to archinstall)."""
    if not value:
        raise ValueError("Keymap must not be empty.")
    return value


def _validate_ids_home_net(value: str) -> str:
    """Validate IDS HOME_NET against allowed CIDR characters.

    Permits only: ``[ ] 0-9 . / : , space a-f A-F !``
    This mirrors the bash validation in BLK7ARCHv1_0.sh and prevents
    config-file injection into snort.conf / suricata.yaml.
    """
    if not value:
        raise ValueError("ids_home_net must not be empty.")
    if not _IDS_HOME_NET_RE.match(value):
        raise ValueError(
            f"Invalid ids_home_net '{value}'. "
            "Use CIDR notation only, e.g. [192.168.0.0/16,10.0.0.0/8]. "
            "No newlines, semicolons, quotes, or shell metacharacters allowed."
        )
    return value


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class BLK7Config:
    """Complete configuration for a BLK7rch installation.

    Fields prefixed with *inherited* map 1-to-1 to archinstall ``ArchConfig``.
    BLK7-specific fields control pentest/security/desktop behaviour.
    """

    # ------------------------------------------------------------------
    # Inherited from archinstall
    # ------------------------------------------------------------------
    disk: str = ""
    """Block device path, e.g. '/dev/sda' or '/dev/nvme0n1'."""

    hostname: str = "blk7arch"
    """System hostname (RFC 952/1123)."""

    username: str = "user"
    """Primary unprivileged user (POSIX, added to wheel group)."""

    timezone: str = "America/Sao_Paulo"
    """Olson timezone name, must exist in /usr/share/zoneinfo."""

    locale: str = "en_US.UTF-8"
    """System locale, e.g. 'en_US.UTF-8'."""

    keymap: str = "us"
    """Console/X11 keyboard layout, e.g. 'us', 'br-abnt2'."""

    bootloader: str = "grub"
    """Bootloader to install: 'grub' or 'systemd-boot'."""

    # ------------------------------------------------------------------
    # BLK7-specific
    # ------------------------------------------------------------------
    profile: str = "workstation"
    """Installation profile: minimal | core | workstation | pentest."""

    workstation_mode: str = "base"
    """Hyprland variant: none | base | dev | pentest."""

    enable_blackarch: bool = False
    """Bootstrap the BlackArch Linux repository."""

    enable_ids: bool = False
    """Install and configure Snort + Suricata IDS/IPS."""

    ids_home_net: str = "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    """IDS HOME_NET variable in Snort/Suricata CIDR notation."""

    ids_snort_profile: str = "balanced"
    """Snort rule set: 'balanced' or 'strict' (adds RDP rule sid:1000003)."""

    ids_mode: str = "minimal-local"
    """Suricata rule mode: 'minimal-local' or 'managed-rules' (suricata-update)."""

    allow_ssh_inbound: bool = False
    """Allow incoming SSH through UFW (port 22)."""

    wifi_backend: str = "nm"
    """WiFi backend: 'nm' (NetworkManager) or 'nm-iwd' (iwd backend)."""

    enable_gdm: bool = True
    """Enable GDM display manager service."""

    auto_reboot: bool = True
    """Reboot automatically after installation completes."""

    root_lv_size: str = "50G"
    """LVM root logical volume size, e.g. '50G'."""

    swap_lv_size: str = "8G"
    """LVM swap logical volume size, e.g. '8G'."""

    encryption_password: Optional[str] = field(default=None, repr=False)
    """LUKS2 encryption passphrase (cleared from memory after use)."""

    user_password: Optional[str] = field(default=None, repr=False)
    """Primary user password (cleared from memory after use)."""

    root_password: Optional[str] = field(default=None, repr=False)
    """Root account password (cleared from memory after use)."""

    # ------------------------------------------------------------------
    # Post-construction validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Validate all fields after dataclass initialisation."""
        if self.hostname:
            _validate_hostname(self.hostname)
        if self.username:
            _validate_username(self.username)
        _validate_lv_size("root_lv_size", self.root_lv_size)
        _validate_lv_size("swap_lv_size", self.swap_lv_size)
        if self.profile not in _VALID_PROFILES:
            raise ValueError(f"Invalid profile '{self.profile}'. Choose from {_VALID_PROFILES}.")
        if self.bootloader not in _VALID_BOOTLOADERS:
            raise ValueError(f"Invalid bootloader '{self.bootloader}'.")
        if self.ids_mode not in _VALID_IDS_MODES:
            raise ValueError(f"Invalid ids_mode '{self.ids_mode}'.")
        if self.ids_snort_profile not in _VALID_IDS_SNORT_PROFILES:
            raise ValueError(f"Invalid ids_snort_profile '{self.ids_snort_profile}'.")
        if self.wifi_backend not in _VALID_WIFI_BACKENDS:
            raise ValueError(f"Invalid wifi_backend '{self.wifi_backend}'.")
        _validate_ids_home_net(self.ids_home_net)

    def validate_disk(self) -> None:
        """Check that the configured disk device exists."""
        if not self.disk:
            raise ValueError("No disk configured. Set 'disk' before installing.")
        if not Path(self.disk).exists():
            raise ValueError(f"Disk device '{self.disk}' does not exist.")

    def validate_passwords(self) -> None:
        """Ensure all required passwords are set."""
        missing = [
            name
            for name, value in [
                ("encryption_password", self.encryption_password),
                ("user_password", self.user_password),
                ("root_password", self.root_password),
            ]
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required passwords: {missing}")

    def clear_passwords(self) -> None:
        """Overwrite password fields with None to minimise memory exposure."""
        import gc

        self.encryption_password = None
        self.user_password = None
        self.root_password = None
        gc.collect()
