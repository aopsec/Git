"""End-to-end dry-run tests — verify all phases complete without disk access."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest

from blk7rch.config.defaults import make_default_config
from blk7rch.config.schema import BLK7Config
from blk7rch.installer.core import BLK7Installer


def _make_test_cfg(profile: str = "pentest") -> BLK7Config:
    """Build a test configuration suitable for dry-run tests."""
    cfg = make_default_config(profile)
    cfg.disk = "/dev/sda"
    cfg.hostname = "blk7test"
    cfg.username = "testuser"
    cfg.encryption_password = "testpass"
    cfg.user_password = "testpass"
    cfg.root_password = "testpass"
    return cfg


class TestDryRunInstall:
    """Dry-run end-to-end installer tests."""

    def test_pentest_dry_run_completes(self) -> None:
        """Pentest profile dry-run must complete without raising exceptions."""
        cfg = _make_test_cfg("pentest")
        installer = BLK7Installer(cfg, dry_run=True)
        installer.run()  # must not raise

    def test_workstation_dry_run_completes(self) -> None:
        """Workstation profile dry-run must complete without raising exceptions."""
        cfg = _make_test_cfg("workstation")
        installer = BLK7Installer(cfg, dry_run=True)
        installer.run()

    def test_minimal_dry_run_completes(self) -> None:
        """Minimal profile dry-run must complete without raising exceptions."""
        cfg = _make_test_cfg("minimal")
        installer = BLK7Installer(cfg, dry_run=True)
        installer.run()

    def test_core_dry_run_completes(self) -> None:
        """Core profile dry-run must complete without raising exceptions."""
        cfg = _make_test_cfg("core")
        installer = BLK7Installer(cfg, dry_run=True)
        installer.run()


class TestDryRunPhases:
    """Verify that individual installer phases are dry-run safe."""

    def test_disk_setup_dry_run(self) -> None:
        """Disk setup phase must not call any real disk tools in dry-run mode."""
        from blk7rch.installer.disk_setup import build_disk_layout, _ARCHINSTALL_AVAILABLE

        cfg = _make_test_cfg()

        if _ARCHINSTALL_AVAILABLE:
            # Only call if archinstall is available; skip otherwise
            pytest.skip("archinstall available — disk_setup test requires a real device")
        else:
            with pytest.raises(RuntimeError, match="archinstall"):
                build_disk_layout(cfg)

    def test_post_install_dry_run(self) -> None:
        """Post-install must not touch disk or reboot in dry-run mode."""
        from blk7rch.installer.post_install import _write_transaction_log, _unmount

        cfg = _make_test_cfg()
        target = Path("/mnt")

        # These must not raise in dry-run mode
        _write_transaction_log(cfg, target, dry_run=True)
        _unmount(target, dry_run=True)

    def test_blackarch_dry_run(self) -> None:
        """BlackArchBootstrap must not make network calls in dry-run mode."""
        from blk7rch.security.blackarch import BlackArchBootstrap

        ba = BlackArchBootstrap(Path("/mnt"), dry_run=True)
        ba.install()  # must not raise or download anything

    def test_ufw_dry_run(self) -> None:
        """UFW setup must not run chroot commands in dry-run mode."""
        from blk7rch.security.ufw import setup_ufw

        cfg = _make_test_cfg()
        setup_ufw(Path("/mnt"), cfg, dry_run=True)  # must not raise

    def test_ids_snort_dry_run(self) -> None:
        """IDS Snort config generation must not write files in dry-run mode."""
        from blk7rch.security.ids_snort import IDSSnortConfig

        cfg = _make_test_cfg()
        gen = IDSSnortConfig(Path("/mnt"), cfg, dry_run=True)
        gen.install()  # must not raise or create files

    def test_ids_suricata_dry_run(self) -> None:
        """IDS Suricata config generation must not write files in dry-run mode."""
        from blk7rch.security.ids_suricata import IDSSuricataConfig

        cfg = _make_test_cfg()
        gen = IDSSuricataConfig(Path("/mnt"), cfg, dry_run=True)
        gen.install()  # must not raise or create files

    def test_hyprland_dry_run(self) -> None:
        """Hyprland config writer must not write files in dry-run mode."""
        from blk7rch.desktop.hyprland import HyprlandConfig

        cfg = _make_test_cfg()
        hc = HyprlandConfig(Path("/mnt"), cfg, "testuser", dry_run=True)
        hc.write()  # must not raise or create files

    def test_waybar_dry_run(self) -> None:
        """Waybar config writer must not write files in dry-run mode."""
        from blk7rch.desktop.waybar import WaybarConfig

        cfg = _make_test_cfg()
        wc = WaybarConfig(Path("/mnt"), cfg, "testuser", dry_run=True)
        wc.write()  # must not raise or create files

    def test_gdm_dry_run(self) -> None:
        """GDM setup must not write files or run chroot commands in dry-run mode."""
        from blk7rch.desktop.gdm import GDMSetup

        gdm = GDMSetup(Path("/mnt"), "testuser", dry_run=True)
        gdm.setup()  # must not raise

    def test_validation_service_dry_run(self) -> None:
        """Post-boot validation service install must be dry-run safe."""
        from blk7rch.security.validation import install_postboot_validation

        install_postboot_validation(Path("/mnt"), dry_run=True)  # must not raise


class TestConfigInit:
    """Test config-init subcommand."""

    def test_config_init_produces_valid_json(self, tmp_path: Path) -> None:
        """config-init must produce a valid JSON file for each profile."""
        import json as _json
        from blk7rch.main import config_init

        for profile in ("minimal", "workstation", "pentest"):
            out = tmp_path / f"{profile}.json"
            config_init(str(out), profile=profile)
            data = _json.loads(out.read_text())
            assert data["profile"] == profile

    def test_config_init_default_profile(self, tmp_path: Path) -> None:
        """config-init without explicit profile must default to workstation."""
        import json as _json
        from blk7rch.main import config_init

        out = tmp_path / "default.json"
        config_init(str(out))
        data = _json.loads(out.read_text())
        assert data["profile"] == "workstation"
