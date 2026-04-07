"""GDM setup — enable service, register Hyprland Wayland session."""

from __future__ import annotations

from pathlib import Path

from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run

_HYPRLAND_SESSION = """\
[Desktop Entry]
Name=Hyprland
Comment=A dynamic tiling Wayland compositor
Exec=Hyprland
Type=Application
"""

_ACCOUNTS_SERVICE_TEMPLATE = """\
[User]
Session=hyprland
SystemAccount=false
"""


class GDMSetup:
    """Configures GDM display manager and registers the Hyprland session.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    username:
        Primary user whose AccountsService entry will be configured.
    dry_run:
        When *True*, writes and chroot commands are skipped.
    """

    def __init__(self, target: Path, username: str, dry_run: bool = False) -> None:
        """Initialise GDM setup."""
        self.target = target
        self.username = username
        self.dry_run = dry_run

    def setup(self) -> None:
        """Enable GDM, register Hyprland as a Wayland session, set default session.

        Steps:
        1. Enable ``gdm.service`` via systemctl.
        2. Write ``/usr/share/wayland-sessions/hyprland.desktop``.
        3. Write ``/var/lib/AccountsService/users/<username>`` with default session.
        """
        log.step("GDM: configuring display manager")

        self._write_session_file()
        self._write_accounts_service()
        self._enable_gdm()

        log.ok("GDM: configured")

    def _write_session_file(self) -> None:
        """Write the Hyprland Wayland session desktop entry."""
        dest = self.target / "usr" / "share" / "wayland-sessions" / "hyprland.desktop"

        if self.dry_run:
            log.dry(f"write {dest}")
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(_HYPRLAND_SESSION)
        except OSError as exc:
            raise RuntimeError(f"GDM: failed to write session file {dest}") from exc

    def _write_accounts_service(self) -> None:
        """Write the AccountsService user config to set the default session."""
        dest = (
            self.target / "var" / "lib" / "AccountsService" / "users" / self.username
        )

        if self.dry_run:
            log.dry(f"write {dest}")
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(_ACCOUNTS_SERVICE_TEMPLATE)
        except OSError as exc:
            raise RuntimeError(f"GDM: failed to write accounts-service file {dest}") from exc

    def _enable_gdm(self) -> None:
        """Enable the gdm systemd service inside the chroot."""
        chroot_run(self.target, ["systemctl", "enable", "gdm"], dry_run=self.dry_run)
