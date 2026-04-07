"""Post-install finalisation — transaction log, services, unmount, reboot."""

from __future__ import annotations

import datetime
import time
from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.security.ufw import setup_ufw
from blk7rch.security.validation import install_postboot_validation
from blk7rch.utils.logger import LOG_PATH, log
from blk7rch.utils.run import run_cmd


def post_install(cfg: BLK7Config, target: Path, dry_run: bool = False) -> None:
    """Execute all post-installation steps.

    Steps:
    1. Write the transaction log to ``/var/log/blk7rch-install.log``.
    2. Install the post-boot validation systemd service.
    3. Configure UFW firewall.
    4. Unmount all filesystems mounted under *target*.
    5. Reboot (unattended: auto; interactive: prompt; dry-run: log only).

    Parameters
    ----------
    cfg:
        Completed installation configuration.
    target:
        Mount point of the installed system.
    dry_run:
        When *True*, unmount and reboot are skipped.
    """
    _write_transaction_log(cfg, target, dry_run)
    install_postboot_validation(target, dry_run)
    setup_ufw(target, cfg, dry_run)
    _unmount(target, dry_run)
    _handle_reboot(cfg, dry_run)


def _write_transaction_log(cfg: BLK7Config, target: Path, dry_run: bool) -> None:
    """Write a human-readable installation summary log.

    The log is written both to the host ``/var/log/blk7rch-install.log``
    and to the installed system's ``/var/log/blk7rch-install.log``.
    """
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

    lines = [
        f"# BLK7rch installation log — {timestamp}",
        f"dry_run       : {dry_run}",
        f"disk          : {cfg.disk}",
        f"hostname      : {cfg.hostname}",
        f"username      : {cfg.username}",
        f"timezone      : {cfg.timezone}",
        f"locale        : {cfg.locale}",
        f"keymap        : {cfg.keymap}",
        f"profile       : {cfg.profile}",
        f"bootloader    : {cfg.bootloader}",
        f"enable_blackarch : {cfg.enable_blackarch}",
        f"enable_ids    : {cfg.enable_ids}",
        f"enable_gdm    : {cfg.enable_gdm}",
        f"root_lv_size  : {cfg.root_lv_size}",
        f"swap_lv_size  : {cfg.swap_lv_size}",
        "",
        "# STATUS: COMPLETE",
    ]

    content = "\n".join(lines) + "\n"

    if dry_run:
        log.dry("write transaction log (dry-run — not written to disk)")
    else:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            LOG_PATH.write_text(content)
        except OSError:
            pass

        target_log = target / "var" / "log" / "blk7rch-install.log"
        try:
            target_log.parent.mkdir(parents=True, exist_ok=True)
            target_log.write_text(content)
        except OSError:
            log.warn("Could not write transaction log to installed system")

    log.ok("Transaction log written")


def _unmount(target: Path, dry_run: bool) -> None:
    """Unmount all filesystems under *target* with ``umount -R``."""
    log.step(f"Unmounting {target}")
    run_cmd(["umount", "-R", str(target)], dry_run=dry_run, check=False)
    log.ok("Filesystems unmounted")


def _handle_reboot(cfg: BLK7Config, dry_run: bool) -> None:
    """Reboot the host system.

    Behaviour depends on mode:
    * **dry-run**: log only, no reboot.
    * **auto_reboot=True**: countdown from 5 s then reboot.
    * **auto_reboot=False**: prompt the user interactively.
    """
    if dry_run:
        log.dry("reboot skipped in dry-run mode")
        return

    if not cfg.auto_reboot:
        answer = input("Reboot now? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            _do_reboot()
        else:
            log.info("Reboot skipped — you can reboot manually with: reboot")
        return

    log.info("Installation complete. Rebooting in 5 seconds … (Ctrl+C to cancel)")
    try:
        for remaining in range(5, 0, -1):
            print(f"  {remaining}…", end="\r", flush=True)
            time.sleep(1)
        print()
        _do_reboot()
    except KeyboardInterrupt:
        log.info("Reboot cancelled. Reboot manually when ready.")


def _do_reboot() -> None:
    """Execute system reboot."""
    log.ok("Rebooting…")
    run_cmd(["reboot"], dry_run=False)
