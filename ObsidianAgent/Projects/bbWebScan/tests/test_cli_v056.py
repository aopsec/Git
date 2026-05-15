"""argparse smoke for the v0.5.6 naabu / port-scan flags."""
from __future__ import annotations

import pytest

from bbwebscan.cli import build_parser
from bbwebscan.config import build_run_config


def test_v056_flags_default_off() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com"])
    assert args.port_scan is False
    assert args.port_scan_mode == "top-100"
    assert args.port_scan_rate == 1000


def test_port_scan_flag_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com", "--port-scan"])
    assert args.port_scan is True


@pytest.mark.parametrize("mode", ["top-100", "top-1000", "full"])
def test_port_scan_mode_accepts_known_modes(mode: str) -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--port-scan", "--port-scan-mode", mode],
    )
    assert args.port_scan_mode == mode


def test_port_scan_mode_rejects_unknown() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["scan", "--target", "example.com", "--port-scan-mode", "lightspeed"],
        )


def test_port_scan_rate_accepts_int() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--port-scan", "--port-scan-rate", "250"],
    )
    assert args.port_scan_rate == 250


def test_port_scan_full_requires_ack_authorized() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "scan", "--target", "example.com",
            "--port-scan", "--port-scan-mode", "full",
        ],
    )
    with pytest.raises(ValueError, match="--port-scan-mode full requires --ack-authorized"):
        build_run_config(args)


def test_port_scan_full_with_ack_builds() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "scan", "--target", "example.com",
            "--port-scan", "--port-scan-mode", "full", "--ack-authorized",
        ],
    )
    config = build_run_config(args)
    assert config.port_scan is True
    assert config.port_scan_mode == "full"
    assert "naabu" in config.enabled_tools


def test_port_scan_enables_naabu_in_tool_set() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com", "--port-scan"])
    config = build_run_config(args)
    assert "naabu" in config.enabled_tools


def test_disable_naabu_conflicts_with_port_scan() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "scan", "--target", "example.com",
            "--port-scan", "--disable-tool", "naabu",
        ],
    )
    with pytest.raises(ValueError, match="--port-scan requires naabu"):
        build_run_config(args)
