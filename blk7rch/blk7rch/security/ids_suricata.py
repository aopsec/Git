"""Suricata IDS configuration generator — byte-compatible with BLK7ARCHv1_0.sh output."""

from __future__ import annotations

from pathlib import Path

from blk7rch.config.schema import BLK7Config
from blk7rch.utils.logger import log
from blk7rch.utils.run import chroot_run


class IDSSuricataConfig:
    """Generates Suricata configuration files inside the installed system.

    Produces:

    * ``/etc/suricata/suricata.yaml`` — main config (vars, af-packet, eve/fast logs)
    * ``/etc/suricata/threshold.config`` — per-rule threshold entries
    * ``/etc/suricata/rules/local.rules`` — SSH brute-force + ICMP flood rules

    When ``cfg.ids_mode == 'managed-rules'``, additional ``enable.conf`` and
    ``disable.conf`` files are written and ``suricata-update`` is invoked.

    Parameters
    ----------
    target:
        Mount point of the installed system.
    cfg:
        BLK7 configuration instance.
    dry_run:
        When *True*, file writes and chroot commands are skipped.
    """

    def __init__(self, target: Path, cfg: BLK7Config, dry_run: bool = False) -> None:
        """Initialise the generator."""
        self.target = target
        self.cfg = cfg
        self.dry_run = dry_run
        self._suri_dir = target / "etc" / "suricata"
        self._rules_dir = self._suri_dir / "rules"

    def install(self) -> None:
        """Write all Suricata configuration files and validate.

        Raises
        ------
        RuntimeError
            If ``suricata -T`` exits with a non-zero code.
        """
        log.step("Suricata: writing configuration files")

        if not self.dry_run:
            self._rules_dir.mkdir(parents=True, exist_ok=True)

        self._write_suricata_yaml()
        self._write_threshold_config()
        self._write_local_rules()

        if self.cfg.ids_mode == "managed-rules":
            self._setup_managed_rules()

        self._validate()

        log.ok("Suricata: configuration complete")

    def _write(self, path: Path, content: str) -> None:
        """Write *content* to *path* (no-op in dry-run mode)."""
        if self.dry_run:
            log.dry(f"write {path}")
            return
        try:
            path.write_text(content)
        except OSError as exc:
            raise RuntimeError(f"Suricata: failed to write {path}") from exc

    def _write_suricata_yaml(self) -> None:
        """Write ``/etc/suricata/suricata.yaml``."""
        # Escape any double-quotes in ids_home_net so the YAML stays valid.
        # The schema validator already rejects most special chars, but be explicit.
        safe_home_net = self.cfg.ids_home_net.replace('"', '\\"')
        content = (
            "%YAML 1.1\n"
            "---\n"
            "vars:\n"
            "  address-groups:\n"
            f'    HOME_NET: "{safe_home_net}"\n'
            '    EXTERNAL_NET: "!$HOME_NET"\n'
            "default-rule-path: /etc/suricata/rules\n"
            "threshold-file: /etc/suricata/threshold.config\n"
            "rule-files:\n"
            "  - local.rules\n"
            "af-packet:\n"
            "  - interface: default\n"
            "    cluster-id: 99\n"
            "    cluster-type: cluster_flow\n"
            "    defrag: yes\n"
            "    use-mmap: yes\n"
            "    tpacket-v3: yes\n"
            "outputs:\n"
            "  - eve-log:\n"
            "      enabled: yes\n"
            "      filetype: regular\n"
            "      filename: /var/log/suricata/eve.json\n"
            "      types:\n"
            "        - alert:\n"
            "            payload: no\n"
            "            packet: no\n"
            "            metadata: yes\n"
            "            tagged-packets: no\n"
            "  - fast:\n"
            "      enabled: yes\n"
            "      filename: /var/log/suricata/fast.log\n"
        )
        self._write(self._suri_dir / "suricata.yaml", content)

    def _write_threshold_config(self) -> None:
        """Write ``/etc/suricata/threshold.config``."""
        content = (
            "threshold gen_id 1, sig_id 2100001, type both, track by_src, count 1, seconds 60\n"
            "threshold gen_id 1, sig_id 2100002, type both, track by_src, count 1, seconds 30\n"
        )
        self._write(self._suri_dir / "threshold.config", content)

    def _write_local_rules(self) -> None:
        """Write ``/etc/suricata/rules/local.rules``."""
        rules = (
            'alert ssh any any -> $HOME_NET any (msg:"SURICATA SSH brute force"; '
            "flow:to_server,established; "
            "threshold:type both, track by_src, count 12, seconds 60; sid:2100001; rev:1;)\n"
            'alert icmp any any -> $HOME_NET any (msg:"SURICATA ICMP flood"; '
            "itype:8; "
            "threshold:type both, track by_src, count 80, seconds 10; sid:2100002; rev:1;)\n"
        )
        self._write(self._rules_dir / "local.rules", rules)

    def _setup_managed_rules(self) -> None:
        """Write suricata-update enable/disable configs and run suricata-update."""
        log.info("Suricata: setting up managed rules via suricata-update")

        enable_conf = "emerging-scan.rules\nemerging-dos.rules\n"
        disable_conf = "re:.*policy.*\nre:.*chat.*\nre:.*games.*\n"

        self._write(self._suri_dir / "enable.conf", enable_conf)
        self._write(self._suri_dir / "disable.conf", disable_conf)

        chroot_run(
            self.target,
            [
                "suricata-update",
                "--suricata-conf", "/etc/suricata/suricata.yaml",
                "--enable-conf", "/etc/suricata/enable.conf",
                "--disable-conf", "/etc/suricata/disable.conf",
                "--no-test",
            ],
            dry_run=self.dry_run,
        )
        log.ok("Suricata: managed rules updated")

    def _validate(self) -> None:
        """Run ``suricata -T`` inside the chroot to validate the configuration."""
        log.info("Suricata: validating configuration")
        chroot_run(
            self.target,
            ["suricata", "-T", "-c", "/etc/suricata/suricata.yaml", "-v"],
            dry_run=self.dry_run,
        )
        log.ok("Suricata: configuration validated")
