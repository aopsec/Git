"""BLK7Installer — orchestrates the full installation using archinstall as backend."""

from __future__ import annotations

import gc
from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.installer.chroot_config import configure_chroot
from blk7rch.installer.disk_setup import build_disk_layout
from blk7rch.installer.post_install import post_install
from blk7rch.profiles.base import BLK7BaseProfile
from blk7rch.profiles.pentest import BLK7PentestProfile
from blk7rch.profiles.workstation import BLK7WorkstationProfile
from blk7rch.security.blackarch import BlackArchBootstrap
from blk7rch.utils.logger import log
from blk7rch.utils.rollback import RollbackStack

try:
    import archinstall  # noqa: F401
    from archinstall.lib.installer import Installer
    from archinstall.lib.disk.filesystem_handler import FilesystemHandler
    from archinstall.lib.models.bootloader import Bootloader
    from archinstall.lib.models.users import User
    _ARCHINSTALL_AVAILABLE = True
except ImportError:
    _ARCHINSTALL_AVAILABLE = False


class BLK7Installer:
    """Orchestrates the full BLK7ARCH installation using archinstall as backend.

    Parameters
    ----------
    cfg:
        Fully populated :class:`~blk7rch.config.schema.BLK7Config`.
    dry_run:
        When *True*, no disks are touched, no chroot commands are executed.
        All actions are logged with the ``[DRY-RUN]`` prefix.
    """

    TARGET = Path("/mnt")

    def __init__(self, cfg: BLK7Config, dry_run: bool = False) -> None:
        """Initialise the installer."""
        self.cfg = cfg
        self.dry_run = dry_run
        self.rollback = RollbackStack()

    def run(self) -> None:
        """Execute the complete installation sequence.

        Phases:
        1. Validate configuration (disk, sizes, hostname, username, passwords).
        2. Build and apply GPT + LUKS2 + LVM disk layout.
        3. pacstrap base system via archinstall ``Installer``.
        4. Configure locale, keymap, timezone, hostname, mkinitcpio, GRUB.
        5. Create user accounts and set passwords.
        6. Apply profile packages and desktop configuration.
        7. Post-install: UFW, validation service, transaction log, unmount, reboot.

        Raises
        ------
        RuntimeError
            On any non-recoverable error; rollback actions are executed before
            re-raising.
        """
        log.step("BLK7rch installer started")

        try:
            self._validate()
            self._phase1_disk()
            self._phase2_base()
            self._phase3_post()
        except Exception:  # noqa: BLE001 — intentional broad catch, triggers rollback on any phase failure
            self.rollback.execute()
            raise

        log.ok("BLK7rch installation complete!")

    # ------------------------------------------------------------------
    # Private phases
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Validate configuration before touching any disk."""
        log.step("Phase 0: validating configuration")

        if not self.dry_run:
            self.cfg.validate_disk()
            self.cfg.validate_passwords()
        else:
            log.dry("validation skipped in dry-run mode")

        if not _ARCHINSTALL_AVAILABLE and not self.dry_run:
            raise RuntimeError(
                "archinstall is not installed. "
                "Boot from the Arch Linux ISO or install with: pacman -S archinstall"
            )

        log.ok("Phase 0: configuration valid")

    def _phase1_disk(self) -> None:
        """Partition, encrypt, and mount the target disk."""
        log.step("Phase 1: disk partitioning + LUKS2 + LVM")

        if self.dry_run:
            log.dry("build_disk_layout()")
            log.dry("FilesystemHandler.perform_filesystem_operations()")
            return

        disk_config = build_disk_layout(self.cfg)

        self.rollback.push("umount -R /mnt", lambda: _safe_umount(self.TARGET))

        fs_handler = FilesystemHandler(disk_config, {0: self.cfg.encryption_password})
        fs_handler.perform_filesystem_operations(show_countdown=True)

        log.ok("Phase 1: disk ready")

    def _phase2_base(self) -> None:
        """Run archinstall Installer for pacstrap, users, profiles."""
        log.step("Phase 2: base system installation")

        if self.dry_run:
            self._dry_run_phase2()
            return

        disk_config = build_disk_layout(self.cfg)

        with Installer(
            self.TARGET,
            disk_config,
            kernels=["linux"],
        ) as installer:
            installer.mount_ordered_layout()

            # Configure locale/hostname/timezone using archinstall API
            configure_chroot(self.cfg, self.TARGET, installer, dry_run=False)

            # Bootloader
            installer.add_bootloader(Bootloader.Grub)

            # Users
            user = User(
                username=self.cfg.username,
                password=self.cfg.user_password or "",
                sudo=True,
            )
            installer.create_users(user)
            installer.user_set_pw("root", self.cfg.root_password or "")

            # Services
            installer.enable_service("NetworkManager")
            if self.cfg.enable_gdm:
                installer.enable_service("gdm")

            # BLK7 profiles
            self._apply_profiles(installer)

        # Clear passwords from memory
        self.cfg.clear_passwords()
        gc.collect()

        log.ok("Phase 2: base system installed")

    def _dry_run_phase2(self) -> None:
        """Log all Phase 2 actions without executing them."""
        log.dry("Installer.mount_ordered_layout()")
        log.dry(f"configure_chroot(locale={self.cfg.locale}, keymap={self.cfg.keymap})")
        log.dry("Installer.add_bootloader(Bootloader.Grub)")
        log.dry(f"Installer.create_users({self.cfg.username})")
        log.dry("Installer.enable_service('NetworkManager')")
        if self.cfg.enable_gdm:
            log.dry("Installer.enable_service('gdm')")
        self._apply_profiles(installer=None)

    def _apply_profiles(self, installer: object) -> None:
        """Apply the selected BLK7 profile.

        Dispatches to the appropriate profile class based on ``cfg.profile``.
        """
        profile_name = self.cfg.profile

        if profile_name == "pentest":
            profile: object = BLK7PentestProfile(
                self.cfg, installer, self.TARGET, self.dry_run
            )
        elif profile_name in ("workstation", "core"):
            profile = BLK7WorkstationProfile(
                self.cfg, installer, self.TARGET, self.dry_run
            )
        else:
            # minimal
            profile = BLK7BaseProfile(self.cfg, installer, self.dry_run)

        profile.install()  # type: ignore[attr-defined]

        if self.cfg.enable_blackarch:
            BlackArchBootstrap(self.TARGET, self.dry_run).install()

    def _phase3_post(self) -> None:
        """Post-install: UFW, validation service, transaction log, unmount, reboot."""
        log.step("Phase 3: post-installation")
        post_install(self.cfg, self.TARGET, self.dry_run)
        log.ok("Phase 3: complete")


def _safe_umount(target: Path) -> None:
    """Attempt to unmount *target* recursively; ignore errors."""
    import subprocess

    subprocess.run(["umount", "-R", str(target)], check=False)  # noqa: S603 — safe: hardcoded command, no user input, check=False intentional for rollback
