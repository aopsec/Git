"""argparse smoke for the v0.5.5 jwt_tool + sqlmap flags."""
from __future__ import annotations

import pytest

from bbwebscan.cli import build_parser


def test_v055_flags_default_off() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com"])
    assert args.jwt_analysis is False
    assert args.sqlmap_mode == "off"
    assert args.sqlmap_timeout == 600


def test_jwt_analysis_flag_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com", "--jwt-analysis"])
    assert args.jwt_analysis is True


@pytest.mark.parametrize("mode", ["smooth", "aggressive"])
def test_sqlmap_mode_accepts_known_modes(mode: str) -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--sqlmap-mode", mode],
    )
    assert args.sqlmap_mode == mode


def test_sqlmap_mode_rejects_unknown() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["scan", "--target", "example.com", "--sqlmap-mode", "apocalyptic"],
        )


def test_sqlmap_timeout_accepts_int() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--sqlmap-timeout", "120"],
    )
    assert args.sqlmap_timeout == 120
