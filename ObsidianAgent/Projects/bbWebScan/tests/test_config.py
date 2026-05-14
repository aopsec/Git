from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from bbwebscan.config import (
    REDACTED_PLACEHOLDER,
    build_run_config,
    config_to_dict,
    load_profile,
    resolve_selected_tools,
)


def _ns(**overrides: object) -> Namespace:
    base: dict[str, object] = {
        "profile": None,
        "target": ["example.com"],
        "input": None,
        "mode": None,
        "ack_authorized": False,
        "header": [],
        "cookie": [],
        "raw_request": None,
        "output_dir": "/tmp/out",
        "wordlist": None,
        "check_tools": False,
        "dry_run": True,
        "enable_tool": [],
        "disable_tool": [],
        "threads": None,
        "rate": None,
        "tool_timeout": None,
        "cmd_timeout": None,
        "max_attempts": None,
        "backoff_s": None,
        "run_label": "test",
        "severity": "info",
        "enumerate_subdomains": False,
        "api_discovery": False,
        "amass_mode": "passive",
        "scrapy_deep": False,
        "scrapy_max_depth": 2,
        "scrapy_js_render": False,
    }
    base.update(overrides)
    return Namespace(**base)


def test_build_run_config_requires_ack_for_aggressive() -> None:
    with pytest.raises(ValueError, match="ack-authorized"):
        build_run_config(_ns(mode="aggressive"))


def test_build_run_config_aggressive_with_ack_passes() -> None:
    config = build_run_config(_ns(mode="aggressive", ack_authorized=True))
    assert config.mode == "aggressive"
    assert "nuclei" in config.enabled_tools


def test_resolve_selected_tools_safe_default() -> None:
    tools = resolve_selected_tools("safe", [], [], [])
    # [v0.5.3] scrapy joined SAFE_DEFAULT_TOOLS for information-disclosure recon.
    assert tools == ["httpx", "katana", "scrapy"]


def test_resolve_selected_tools_safe_disable_scrapy() -> None:
    tools = resolve_selected_tools("safe", [], [], ["scrapy"])
    assert "scrapy" not in tools


def test_build_run_config_scrapy_flags_round_trip() -> None:
    config = build_run_config(
        _ns(scrapy_deep=True, scrapy_max_depth=4, scrapy_js_render=True),
    )
    assert config.scrapy_deep is True
    assert config.scrapy_max_depth == 4
    assert config.scrapy_js_render is True
    assert "scrapy" in config.enabled_tools


def test_build_run_config_rejects_scrapy_max_depth_out_of_range() -> None:
    with pytest.raises(ValueError):
        build_run_config(_ns(scrapy_max_depth=10))


def test_resolve_selected_tools_disable_overrides_enable() -> None:
    tools = resolve_selected_tools("safe", [], ["nuclei"], ["nuclei"])
    assert "nuclei" not in tools


def test_resolve_selected_tools_rejects_unsupported() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        resolve_selected_tools("safe", [], ["wfuzz"], [])


def test_build_run_config_adds_amass_for_subdomain_enumeration() -> None:
    config = build_run_config(_ns(enumerate_subdomains=True))

    assert "amass" in config.enabled_tools


def test_build_run_config_adds_kiterunner_for_api_discovery() -> None:
    config = build_run_config(_ns(api_discovery=True))

    assert "kiterunner" in config.enabled_tools


def test_build_run_config_rejects_disabling_amass_when_enumerating() -> None:
    with pytest.raises(ValueError, match="requires amass"):
        build_run_config(_ns(enumerate_subdomains=True, disable_tool=["amass"]))


def test_build_run_config_rejects_disabling_kiterunner_for_api_discovery() -> None:
    with pytest.raises(ValueError, match="requires kiterunner"):
        build_run_config(_ns(api_discovery=True, disable_tool=["kiterunner"]))


def test_load_profile_roundtrip(tmp_path: Path) -> None:
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {"program_name": "demo", "tool_timeout_s": 5, "command_wall_clock_s": 60}
        ),
        encoding="utf-8",
    )
    profile = load_profile(str(profile_path))
    assert profile.program_name == "demo"
    assert profile.tool_timeout_s == 5
    assert profile.command_wall_clock_s == 60


def test_load_profile_missing_path_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Profile not found"):
        load_profile(str(tmp_path / "missing.yaml"))


def test_build_run_config_splits_timeout_args() -> None:
    config = build_run_config(_ns(tool_timeout=7, cmd_timeout=300))
    assert config.tool_timeout_s == 7
    assert config.command_wall_clock_s == 300


def test_build_run_config_derives_allowed_hosts_from_single_target() -> None:
    """v0.4.0 smart default: profile-less single-target run derives scope."""
    config = build_run_config(_ns(target=["example.com"]))
    assert config.allowed_hosts == ["example.com"]


def test_build_run_config_does_not_derive_for_multi_target() -> None:
    """Multi-host without explicit allowed_hosts must still trip the scope gate later."""
    config = build_run_config(_ns(target=["a.example.com", "b.other.test"]))
    assert config.allowed_hosts == []


def test_build_run_config_threads_strict_identity(tmp_path: Path) -> None:
    config = build_run_config(_ns(strict_identity=True))
    assert config.strict_identity is True
    config = build_run_config(_ns())
    assert config.strict_identity is False


def test_build_run_config_threads_verbose_from_quiet(tmp_path: Path) -> None:
    config = build_run_config(_ns(quiet=True))
    assert config.verbose is False
    config = build_run_config(_ns())
    assert config.verbose is True


def test_build_run_config_loads_profile_tool_identity(tmp_path: Path) -> None:
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(
        yaml.safe_dump({
            "program_name": "demo",
            "tool_identity": {"httpx": "^FAKE"},
        }),
        encoding="utf-8",
    )
    config = build_run_config(_ns(profile=str(profile_path), target=["example.com"]))
    assert config.profile_tool_identity == {"httpx": "^FAKE"}


def test_build_run_config_warns_when_ack_authorized_in_safe_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.2 (FIX-BBW-H): redundant --ack-authorized in safe mode emits a stderr note."""
    build_run_config(_ns(mode="safe", ack_authorized=True))
    err = capsys.readouterr().err
    assert "--ack-authorized has no effect in safe mode" in err


def test_build_run_config_silent_when_ack_authorized_in_aggressive_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_run_config(_ns(mode="aggressive", ack_authorized=True))
    err = capsys.readouterr().err
    assert err == ""


def test_build_run_config_silent_when_safe_mode_without_ack(
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_run_config(_ns(mode="safe"))
    err = capsys.readouterr().err
    assert err == ""


def test_config_to_dict_redacts_auth_header_values(tmp_path: Path) -> None:
    """v0.4.4 #1: resolved auth header values must NOT appear in run_config.json
    serialisation. Header KEYS are preserved so the audit trail records which
    headers were set."""
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(yaml.safe_dump({
        "program_name": "demo",
        "auth": {
            "headers": {"Authorization": "Bearer top-secret-xyz"},
            "cookies": {"session": "private-cookie-abc"},
        },
    }), encoding="utf-8")
    config = build_run_config(_ns(profile=str(profile_path), target=["example.com"]))
    payload = config_to_dict(config)
    headers = payload["auth"]["headers"]
    cookies = payload["auth"]["cookies"]
    # Keys preserved
    assert "Authorization" in headers
    assert "session" in cookies
    # Values redacted
    assert headers["Authorization"] == REDACTED_PLACEHOLDER
    assert cookies["session"] == REDACTED_PLACEHOLDER
    # Secret nowhere in the payload string
    assert "top-secret-xyz" not in str(payload)
    assert "private-cookie-abc" not in str(payload)


def test_config_to_dict_no_op_when_auth_empty() -> None:
    """v0.4.4 #1: empty auth produces empty dicts (no errors, no synthetic keys)."""
    config = build_run_config(_ns())  # no auth in default
    payload = config_to_dict(config)
    assert payload["auth"]["headers"] == {}
    assert payload["auth"]["cookies"] == {}


def test_amass_active_mode_requires_ack_authorized() -> None:
    """v0.5.0 Item 1+2: amass active makes detectable queries; gate it
    behind --ack-authorized (same posture as aggressive mode)."""
    with pytest.raises(ValueError, match=r"--amass-mode active requires --ack-authorized"):
        build_run_config(_ns(amass_mode="active"))


def test_amass_intel_mode_requires_ack_authorized() -> None:
    with pytest.raises(ValueError, match=r"--amass-mode intel requires --ack-authorized"):
        build_run_config(_ns(amass_mode="intel"))


def test_amass_active_passes_with_ack() -> None:
    config = build_run_config(_ns(amass_mode="active", ack_authorized=True))
    assert config.amass_mode == "active"


def test_amass_passive_default_no_ack_needed() -> None:
    config = build_run_config(_ns(amass_mode="passive"))
    assert config.amass_mode == "passive"


def test_severity_flag_threads_through_to_run_config() -> None:
    """v0.4.3 (Item 5): --severity values flow into RunConfig.min_severity."""
    config = build_run_config(_ns(severity="medium"))
    assert config.min_severity == "medium"
    config = build_run_config(_ns())  # default
    assert config.min_severity == "info"


def test_auth_env_var_interpolation_substitutes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 7): env vars in auth.headers / auth.cookies are resolved."""
    monkeypatch.setenv("BBP_TEST_TOKEN", "secret-xyz")
    monkeypatch.setenv("BBP_TEST_SESSION", "sess-abc")
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(yaml.safe_dump({
        "program_name": "demo",
        "auth": {
            "headers": {"Authorization": "Bearer ${BBP_TEST_TOKEN}"},
            "cookies": {"session": "${BBP_TEST_SESSION}"},
        },
    }), encoding="utf-8")
    config = build_run_config(_ns(profile=str(profile_path), target=["example.com"]))
    assert config.auth.headers["Authorization"] == "Bearer secret-xyz"
    assert config.auth.cookies["session"] == "sess-abc"


def test_auth_env_var_missing_raises_actionable_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 7): missing env var raises ValueError naming the var."""
    monkeypatch.delenv("BBP_TEST_MISSING", raising=False)
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(yaml.safe_dump({
        "program_name": "demo",
        "auth": {"headers": {"Authorization": "Bearer ${BBP_TEST_MISSING}"}},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match=r"BBP_TEST_MISSING"):
        build_run_config(_ns(profile=str(profile_path), target=["example.com"]))


def test_auth_env_var_does_not_apply_outside_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """v0.4.3 (Item 7): ${VAR} in non-auth fields (e.g. wordlist) is left literal,
    so $HOME-style references in paths don't accidentally expand."""
    monkeypatch.delenv("HOME", raising=False)  # ensure no fallback
    profile_path = tmp_path / "p.yaml"
    profile_path.write_text(yaml.safe_dump({
        "program_name": "demo",
        "wordlist": "/usr/share/wordlists/${SHOULD_NOT_EXPAND}/foo.txt",
    }), encoding="utf-8")
    # Should NOT raise — interpolation is scoped to auth only.
    config = build_run_config(_ns(profile=str(profile_path), target=["example.com"]))
    assert "${SHOULD_NOT_EXPAND}" in str(config.wordlist)
