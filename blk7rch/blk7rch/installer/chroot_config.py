"""Chroot configuration — locale, hostname, mkinitcpio hooks, GRUB cryptdevice."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config, _UUID_RE
from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run, run_cmd

try:
    from archinstall.lib.locale import (
        LocaleConfiguration,
        set_keyboard_language,  # noqa: F401
        set_timezone,  # noqa: F401
    )
    _LOCALE_AVAILABLE = True
except ImportError:
    _LOCALE_AVAILABLE = False


def configure_chroot(
    cfg: BLK7Config,
    target: Path,
    installer: object,
    dry_run: bool = False,
) -> None:
    """Apply all chroot-level configuration using archinstall APIs.

    Configures:
    * Locale and keyboard layout.
    * System timezone.
    * Hostname in ``/etc/hostname`` and ``/etc/hosts``.
    * mkinitcpio hooks (``encrypt`` + ``lvm2`` for LUKS2+LVM boot).
    * GRUB with ``cryptdevice`` kernel parameter.

    Parameters
    ----------
    cfg:
        BLK7 configuration instance.
    target:
        Mount point of the installed system.
    installer:
        Active ``archinstall.lib.installer.Installer`` context.
    dry_run:
        When *True*, all chroot commands are logged but not executed.
    """
    log.step("Chroot: configuring system")

    _configure_locale(cfg, installer, dry_run)
    _configure_hostname(cfg, target, dry_run)
    _patch_mkinitcpio(target, dry_run)
    _configure_grub(cfg, target, dry_run)

    log.ok("Chroot: configuration complete")


def _configure_locale(cfg: BLK7Config, installer: object, dry_run: bool) -> None:
    """Set locale, keyboard layout, and timezone via archinstall APIs."""
    if dry_run:
        log.dry(f"set locale: {cfg.locale}, keymap: {cfg.keymap}, timezone: {cfg.timezone}")
        return

    try:
        locale_cfg = LocaleConfiguration(
            kb_layout=cfg.keymap,
            sys_lang=cfg.locale,
            sys_enc="UTF-8",
        )
        installer.minimal_installation(  # type: ignore[attr-defined]
            hostname=cfg.hostname,
            locale_config=locale_cfg,
        )
        installer.set_timezone(cfg.timezone)  # type: ignore[attr-defined]
    except (ImportError, AttributeError, TypeError) as exc:
        # archinstall API shape varies across versions; fall back gracefully.
        log.warn(f"archinstall locale API unavailable ({exc}), falling back to manual config")
        _manual_locale(cfg, installer)


def _manual_locale(cfg: BLK7Config, installer: object) -> None:
    """Fallback manual locale configuration when archinstall API differs."""
    try:
        installer.set_locale(cfg.locale, "UTF-8")  # type: ignore[attr-defined]
        installer.set_keyboard_language(cfg.keymap)  # type: ignore[attr-defined]
        installer.set_timezone(cfg.timezone)  # type: ignore[attr-defined]
    except AttributeError as exc:
        log.warn(f"Manual locale fallback also failed: {exc}")


def _configure_hostname(cfg: BLK7Config, target: Path, dry_run: bool) -> None:
    """Write ``/etc/hostname`` and ``/etc/hosts``."""
    hostname_file = target / "etc" / "hostname"
    hosts_file = target / "etc" / "hosts"

    if dry_run:
        log.dry(f"write hostname={cfg.hostname} to /etc/hostname and /etc/hosts")
        return

    hostname_file.write_text(cfg.hostname + "\n")

    hosts_content = (
        "# Static table lookup for hostnames.\n"
        "# See hosts(5) for details.\n"
        "127.0.0.1\tlocalhost\n"
        "::1\t\tlocalhost\n"
        f"127.0.1.1\t{cfg.hostname}.localdomain\t{cfg.hostname}\n"
    )
    hosts_file.write_text(hosts_content)
    log.ok(f"Chroot: hostname set to '{cfg.hostname}'")


def _patch_mkinitcpio(target: Path, dry_run: bool) -> None:
    """Ensure ``encrypt`` and ``lvm2`` hooks appear in ``/etc/mkinitcpio.conf``.

    Replaces the ``HOOKS`` line with the LUKS2+LVM-compatible hook ordering:
    ``base udev autodetect modconf kms block keyboard keymap encrypt lvm2 filesystems fsck``
    """
    mkinitcpio = target / "etc" / "mkinitcpio.conf"

    if dry_run:
        log.dry("patch mkinitcpio.conf: add encrypt + lvm2 hooks")
        return

    if not mkinitcpio.exists():
        log.warn("mkinitcpio.conf not found — skipping hook patch")
        return

    content = mkinitcpio.read_text()
    new_hooks = (
        "HOOKS=(base udev autodetect modconf kms block keyboard keymap "
        "encrypt lvm2 filesystems fsck)"
    )

    import re

    patched = re.sub(r"^HOOKS=\(.*\)$", new_hooks, content, flags=re.MULTILINE)
    mkinitcpio.write_text(patched)

    chroot_run(target, ["mkinitcpio", "-P"], dry_run=dry_run)
    log.ok("Chroot: mkinitcpio regenerated with encrypt + lvm2 hooks")


def _configure_grub(cfg: BLK7Config, target: Path, dry_run: bool) -> None:
    """Patch ``/etc/default/grub`` and install GRUB with cryptdevice parameter.

    Looks up the LUKS partition UUID from ``blkid`` and injects
    ``cryptdevice=UUID=<uuid>:cryptlvm root=/dev/vg0/root`` into
    ``GRUB_CMDLINE_LINUX``.
    """
    if dry_run:
        log.dry("configure GRUB with cryptdevice=UUID=... kernel parameter")
        return

    grub_default = target / "etc" / "default" / "grub"
    if not grub_default.exists():
        log.warn("/etc/default/grub not found — skipping GRUB config patch")
        return

    # Determine LUKS partition (partition 2 on the disk)
    disk = cfg.disk
    if disk.startswith("/dev/nvme") or disk.startswith("/dev/mmcblk"):
        luks_part = disk + "p2"
    else:
        luks_part = disk + "2"

    uuid_result = run_cmd(
        ["blkid", "-s", "UUID", "-o", "value", luks_part],
        capture=True,
        dry_run=False,
    )
    luks_uuid = uuid_result.stdout.strip()

    if not luks_uuid:
        raise RuntimeError(
            f"Could not determine UUID of {luks_part} via blkid. "
            "Aborting to prevent invalid GRUB cryptdevice entry."
        )
    elif not _UUID_RE.match(luks_uuid):
        raise RuntimeError(
            f"blkid returned an unexpected UUID format: {luks_uuid!r}. "
            "Expected 8-4-4-4-12 hex digits. Aborting to prevent GRUB misconfiguration."
        )

    grub_content = grub_default.read_text()
    cmdline = (
        f"GRUB_CMDLINE_LINUX=\"cryptdevice=UUID={luks_uuid}:cryptlvm "
        f"root=/dev/vg0/root quiet loglevel=3\""
    )

    import re

    patched = re.sub(
        r'^GRUB_CMDLINE_LINUX=.*$',
        cmdline,
        grub_content,
        flags=re.MULTILINE,
    )
    grub_default.write_text(patched)

    chroot_run(
        target,
        ["grub-install", "--target=x86_64-efi", "--efi-directory=/boot", "--bootloader-id=GRUB"],
        dry_run=dry_run,
    )
    chroot_run(target, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"], dry_run=dry_run)
    log.ok("Chroot: GRUB installed and configured with cryptdevice parameter")
