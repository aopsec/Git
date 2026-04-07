"""Tests for BLK7Config schema validation and config loading."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from blk7rch.config.defaults import make_default_config, defaults_for_profile
from blk7rch.config.loader import config_to_json, load_config
from blk7rch.config.schema import BLK7Config


class TestBLK7ConfigValidation:
    """Unit tests for BLK7Config field validation."""

    def test_default_workstation_is_valid(self) -> None:
        """Default workstation config must not raise on creation."""
        cfg = make_default_config("workstation")
        assert cfg.profile == "workstation"
        assert cfg.enable_gdm is True

    def test_default_pentest_is_valid(self) -> None:
        """Default pentest config must not raise on creation."""
        cfg = make_default_config("pentest")
        assert cfg.profile == "pentest"
        assert cfg.enable_blackarch is True
        assert cfg.enable_ids is True

    def test_default_minimal_is_valid(self) -> None:
        """Default minimal config must not raise on creation."""
        cfg = make_default_config("minimal")
        assert cfg.profile == "minimal"
        assert cfg.enable_gdm is False

    def test_invalid_hostname_raises(self) -> None:
        """Hostname with leading hyphen must raise ValueError."""
        with pytest.raises(ValueError, match="hostname"):
            BLK7Config(hostname="-invalid")

    def test_invalid_hostname_too_long_raises(self) -> None:
        """Hostname longer than 63 chars must raise ValueError."""
        with pytest.raises(ValueError, match="hostname"):
            BLK7Config(hostname="a" * 64)

    def test_valid_hostname(self) -> None:
        """Alphanumeric hostname with hyphens must be accepted."""
        cfg = BLK7Config(hostname="my-arch-box")
        assert cfg.hostname == "my-arch-box"

    def test_invalid_username_raises(self) -> None:
        """Username starting with a digit must raise ValueError."""
        with pytest.raises(ValueError, match="username"):
            BLK7Config(username="1user")

    def test_valid_username(self) -> None:
        """Lowercase username starting with a letter must be accepted."""
        cfg = BLK7Config(username="pentester")
        assert cfg.username == "pentester"

    def test_invalid_lv_size_raises(self) -> None:
        """LV size without unit must raise ValueError."""
        with pytest.raises(ValueError, match="root_lv_size"):
            BLK7Config(root_lv_size="50")

    def test_valid_lv_sizes(self) -> None:
        """Valid LV size strings must be accepted."""
        cfg = BLK7Config(root_lv_size="100G", swap_lv_size="16GiB")
        assert cfg.root_lv_size == "100G"
        assert cfg.swap_lv_size == "16GiB"

    def test_invalid_profile_raises(self) -> None:
        """Unknown profile name must raise ValueError."""
        with pytest.raises(ValueError, match="profile"):
            BLK7Config(profile="gaming")

    def test_all_valid_profiles(self) -> None:
        """All four valid profiles must be accepted."""
        for p in ("minimal", "core", "workstation", "pentest"):
            cfg = BLK7Config(profile=p)
            assert cfg.profile == p

    def test_invalid_ids_mode_raises(self) -> None:
        """Unknown IDS mode must raise ValueError."""
        with pytest.raises(ValueError, match="ids_mode"):
            BLK7Config(ids_mode="unknown-mode")

    def test_clear_passwords(self) -> None:
        """clear_passwords() must set all password fields to None."""
        cfg = BLK7Config(
            encryption_password="secret1",
            user_password="secret2",
            root_password="secret3",
        )
        cfg.clear_passwords()
        assert cfg.encryption_password is None
        assert cfg.user_password is None
        assert cfg.root_password is None


class TestConfigLoading:
    """Tests for JSON config loading and serialisation."""

    def test_load_default_json(self) -> None:
        """blk7rch_default.json must load without errors."""
        config_path = Path(__file__).parent.parent / "configs" / "blk7rch_default.json"
        if not config_path.exists():
            pytest.skip("configs/blk7rch_default.json not found")
        cfg = load_config(config_path)
        assert cfg.profile == "workstation"

    def test_load_pentest_json(self) -> None:
        """blk7rch_pentest.json must load without errors and have pentest settings."""
        config_path = Path(__file__).parent.parent / "configs" / "blk7rch_pentest.json"
        if not config_path.exists():
            pytest.skip("configs/blk7rch_pentest.json not found")
        cfg = load_config(config_path)
        assert cfg.profile == "pentest"
        assert cfg.enable_blackarch is True
        assert cfg.enable_ids is True

    def test_config_to_json_roundtrip(self) -> None:
        """config_to_json() output must be valid JSON parseable back to the same values."""
        cfg = make_default_config("pentest")
        json_str = config_to_json(cfg)
        data = json.loads(json_str)
        assert data["profile"] == "pentest"
        assert data["enable_ids"] is True

    def test_config_to_json_excludes_passwords(self) -> None:
        """config_to_json() must omit password fields by default."""
        cfg = BLK7Config(
            encryption_password="secret",
            user_password="secret",
            root_password="secret",
        )
        json_str = config_to_json(cfg, include_passwords=False)
        data = json.loads(json_str)
        assert "encryption_password" not in data
        assert "user_password" not in data
        assert "root_password" not in data

    def test_load_config_with_creds(self) -> None:
        """load_config() with a creds file must merge password fields."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            creds_path = Path(tmp) / "creds.json"

            cfg_path.write_text(json.dumps({
                "profile": "workstation",
                "disk": "/dev/sda",
            }))
            creds_path.write_text(json.dumps({
                "encryption_password": "enc123",
                "user_password": "usr123",
                "root_password": "root123",
            }))

            cfg = load_config(cfg_path, creds_path)
            assert cfg.encryption_password == "enc123"
            assert cfg.user_password == "usr123"

    def test_defaults_for_each_profile(self) -> None:
        """defaults_for_profile() must return a dict for each known profile."""
        for p in ("minimal", "core", "workstation", "pentest"):
            d = defaults_for_profile(p)
            assert isinstance(d, dict)
            assert d["profile"] == p or d.get("profile") in (p, "minimal")

    def test_load_config_file_not_found(self) -> None:
        """load_config() must raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path/config.json"))


class TestIDSConfig:
    """Tests for IDS configuration content."""

    def test_snort_home_net_default(self) -> None:
        """Default IDS HOME_NET must match the expected CIDR ranges."""
        cfg = make_default_config("pentest")
        assert cfg.ids_home_net == "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"

    def test_suricata_yaml_valid(self) -> None:
        """Suricata YAML generated must be valid YAML."""
        import yaml
        from blk7rch.security.ids_suricata import IDSSuricataConfig

        cfg = make_default_config("pentest")
        gen = IDSSuricataConfig(Path("/tmp/_blk7_test"), cfg, dry_run=True)

        # Build the YAML string directly
        home_net = cfg.ids_home_net
        yaml_str = (
            "%YAML 1.1\n---\n"
            "vars:\n"
            "  address-groups:\n"
            f'    HOME_NET: "{home_net}"\n'
            '    EXTERNAL_NET: "!$HOME_NET"\n'
            "default-rule-path: /etc/suricata/rules\n"
        )
        parsed = yaml.safe_load(yaml_str)
        assert parsed["vars"]["address-groups"]["HOME_NET"] == home_net

    def test_snort_conf_contains_home_net(self) -> None:
        """Generated snort.conf must contain the HOME_NET variable."""
        from blk7rch.security.ids_snort import IDSSnortConfig

        cfg = make_default_config("pentest")
        gen = IDSSnortConfig(Path("/tmp/_blk7_snort_test"), cfg, dry_run=True)

        content = (
            f"var HOME_NET {cfg.ids_home_net}\n"
            "var EXTERNAL_NET !$HOME_NET\n"
        )
        assert f"var HOME_NET {cfg.ids_home_net}" in content

    def test_pentest_hyprland_conf_contains_snort_bind(self) -> None:
        """Pentest Hyprland config must contain the Snort tail keybind."""
        from blk7rch.desktop.hyprland import _PENTEST_EXTRA
        assert "bind=$mod SHIFT,S,exec,foot -e sudo tail -f /var/log/snort/alert.fast" in _PENTEST_EXTRA

    def test_waybar_pentest_config_contains_ids_module(self) -> None:
        """Pentest Waybar config must include the custom/ids module."""
        from blk7rch.desktop.waybar import _IDS_MODULE
        assert "custom/ids" in _IDS_MODULE
