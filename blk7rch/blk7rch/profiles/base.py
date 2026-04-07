"""BLK7BaseProfile — minimal encrypted install with essential packages."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log

if TYPE_CHECKING:
    pass


class BLK7BaseProfile:
    """Minimal profile: base system + NetworkManager + sudo + vim + git + ufw.

    This profile is the foundation for all other profiles.  It installs only
    the packages required for a functional, encrypted, network-connected system.

    Parameters
    ----------
    cfg:
        BLK7 configuration instance.
    installer:
        An active ``archinstall.lib.installer.Installer`` context.
    dry_run:
        When *True*, package installation and service enablement are skipped.
    """

    BASE_PACKAGES: list[str] = [
        "base",
        "base-devel",
        "linux",
        "linux-firmware",
        "lvm2",
        "cryptsetup",
        "grub",
        "efibootmgr",
        "networkmanager",
        "sudo",
        "vim",
        "git",
        "ufw",
        "openssh",
        "man-db",
        "man-pages",
        "bash-completion",
    ]

    BASE_SERVICES: list[str] = [
        "NetworkManager",
    ]

    def __init__(self, cfg: BLK7Config, installer: object, dry_run: bool = False) -> None:
        """Initialise the base profile."""
        self.cfg = cfg
        self.installer = installer
        self.dry_run = dry_run

    def install(self) -> None:
        """Install base packages and enable essential services.

        The ``archinstall.Installer.add_additional_packages`` and
        ``enable_service`` APIs are used so that all operations go through
        archinstall's pacstrap/chroot machinery.
        """
        log.step("Profile [base]: installing minimal packages")

        if not self.dry_run:
            self.installer.add_additional_packages(self.BASE_PACKAGES)  # type: ignore[attr-defined]
            for svc in self.BASE_SERVICES:
                self.installer.enable_service(svc)  # type: ignore[attr-defined]
        else:
            log.dry(f"add_additional_packages({self.BASE_PACKAGES})")
            for svc in self.BASE_SERVICES:
                log.dry(f"enable_service({svc})")

        log.ok("Profile [base]: complete")
