"""BLK7WorkstationProfile — Hyprland desktop environment profile."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.desktop.gdm import GDMSetup
from blk7rch.desktop.hyprland import HyprlandConfig
from blk7rch.desktop.waybar import WaybarConfig
from blk7rch.profiles.base import BLK7BaseProfile
from blk7rch.utils.logger import log


class BLK7WorkstationProfile(BLK7BaseProfile):
    """Workstation profile: base + Hyprland + Waybar + GDM + peripheral tools.

    Parameters
    ----------
    cfg:
        BLK7 configuration instance.
    installer:
        Active ``archinstall.lib.installer.Installer`` context.
    target:
        Mount point of the installed system (for config file writes).
    dry_run:
        When *True*, package operations and file writes are skipped.
    """

    WORKSTATION_PACKAGES: list[str] = [
        "hyprland",
        "waybar",
        "foot",
        "wofi",
        "mako",
        "xdg-desktop-portal-hyprland",
        "xdg-desktop-portal-gtk",
        "xorg-xwayland",
        "brightnessctl",
        "wl-clipboard",
        "gdm",
        "polkit",
        "polkit-gnome",
        "grim",
        "slurp",
    ]

    WORKSTATION_SERVICES: list[str] = []

    def __init__(
        self,
        cfg: BLK7Config,
        installer: object,
        target: Path,
        dry_run: bool = False,
    ) -> None:
        """Initialise the workstation profile."""
        super().__init__(cfg, installer, dry_run)
        self.target = target

    def install(self) -> None:
        """Install workstation packages, write desktop configs, and enable GDM.

        Execution order:
        1. Base profile packages + services.
        2. Workstation packages (Hyprland stack).
        3. Write Hyprland config.
        4. Write Waybar config.
        5. Configure GDM session.
        """
        super().install()

        log.step("Profile [workstation]: installing desktop packages")
        pkgs = self.WORKSTATION_PACKAGES.copy()
        pkgs.extend(self.WORKSTATION_SERVICES)

        if not self.dry_run:
            self.installer.add_additional_packages(pkgs)  # type: ignore[attr-defined]
        else:
            log.dry(f"add_additional_packages({pkgs})")

        HyprlandConfig(self.target, self.cfg, self.cfg.username, self.dry_run).write()
        WaybarConfig(self.target, self.cfg, self.cfg.username, self.dry_run).write()

        if self.cfg.enable_gdm:
            GDMSetup(self.target, self.cfg.username, self.dry_run).setup()

        log.ok("Profile [workstation]: complete")
