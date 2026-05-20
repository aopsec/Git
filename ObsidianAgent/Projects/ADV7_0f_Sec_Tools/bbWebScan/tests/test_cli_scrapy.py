"""argparse smoke for the v0.5.3 Scrapy flags."""
from __future__ import annotations

import pytest

from bbwebscan.cli import build_parser


def test_scrapy_flags_default_off() -> None:
    parser = build_parser()
    args = parser.parse_args(["scan", "--target", "example.com"])
    assert args.scrapy_deep is False
    assert args.scrapy_max_depth == 2
    assert args.scrapy_js_render is False


def test_scrapy_deep_flag_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--scrapy-deep"],
    )
    assert args.scrapy_deep is True


def test_scrapy_max_depth_accepts_in_range() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--scrapy-max-depth", "4"],
    )
    assert args.scrapy_max_depth == 4


@pytest.mark.parametrize("bad", ["0", "6", "-1"])
def test_scrapy_max_depth_rejects_out_of_range(bad: str) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["scan", "--target", "example.com", "--scrapy-max-depth", bad],
        )


def test_scrapy_js_render_flag_parses() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["scan", "--target", "example.com", "--scrapy-js-render"],
    )
    assert args.scrapy_js_render is True
