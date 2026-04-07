"""IDSProfile — Snort + Suricata installation and configuration."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.security.ids_snort import IDSSnortConfig
from blk7rch.security.ids_suricata import IDSSuricataConfig
from blk7rch.utils.logger import log


class IDSProfile:
    """Installs Snort and Suricata, generates configs, and enables services.

    Parameters
    ----------
    cfg:
        BLK7 configuration instance.
    installer:
        Active ``archinstall.lib.installer.Installer`` context.
    target:
        Mount point of the installed system.
    dry_run:
        When *True*, package operations, writes, and service enablement are skipped.
    """

    IDS_PACKAGES: list[str] = [
        "snort",
        "suricata",
    ]

    IDS_SERVICES: list[str] = [
        "snort",
        "suricata",
    ]

    def __init__(
        self,
        cfg: BLK7Config,
        installer: object,
        target: Path,
        dry_run: bool = False,
    ) -> None:
        """Initialise the IDS profile."""
        self.cfg = cfg
        self.installer = installer
        self.target = target
        self.dry_run = dry_run

    def install(self) -> None:
        """Install Snort + Suricata, write configs, and enable systemd services.

        Execution order:
        1. Install ``snort`` and ``suricata`` packages.
        2. Generate Snort configuration files via :class:`IDSSnortConfig`.
        3. Generate Suricata configuration files via :class:`IDSSuricataConfig`.
        4. Enable ``snort`` and ``suricata`` services.
        """
        log.step("Profile [ids]: installing IDS/IPS")

        if not self.dry_run:
            self.installer.add_additional_packages(self.IDS_PACKAGES)  # type: ignore[attr-defined]
        else:
            log.dry(f"add_additional_packages({self.IDS_PACKAGES})")

        IDSSnortConfig(self.target, self.cfg, self.dry_run).install()
        IDSSuricataConfig(self.target, self.cfg, self.dry_run).install()

        for svc in self.IDS_SERVICES:
            if not self.dry_run:
                self.installer.enable_service(svc)  # type: ignore[attr-defined]
            else:
                log.dry(f"enable_service({svc})")

        log.ok("Profile [ids]: complete")
