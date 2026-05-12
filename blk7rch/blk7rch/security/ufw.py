"""UFW firewall setup — default deny-incoming policy with optional SSH allowance."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run


def setup_ufw(target: Path, cfg: BLK7Config, dry_run: bool = False) -> None:
    """Configure UFW inside the installed system.

    Policy applied:
    * Default deny incoming, allow outgoing.
    * SSH (port 22) allowed only when ``cfg.allow_ssh_inbound`` is *True*.
    * UFW forced-enabled and the ``ufw`` systemd service is enabled.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    cfg:
        BLK7 configuration instance.
    dry_run:
        When *True*, commands are logged but not executed.
    """
    log.step("UFW: configuring firewall")

    def _run(cmd: str) -> None:
        chroot_run(target, cmd, dry_run=dry_run)

    _run("ufw --force reset")
    _run("ufw default deny incoming")
    _run("ufw default allow outgoing")

    if cfg.allow_ssh_inbound:
        log.info("UFW: allowing SSH inbound (port 22)")
        _run("ufw allow ssh")
    else:
        log.info("UFW: SSH inbound DENIED (allow_ssh_inbound=False)")

    _run("ufw --force enable")
    _run("systemctl enable ufw")

    log.ok("UFW: firewall configured")
