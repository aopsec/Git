import pytest

from bbwebscan.auth import (
    build_header_args,
    merge_auth,
    parse_cookie_values,
    parse_header_values,
)
from bbwebscan.models import AuthConfig


def test_parse_header_values_strips_whitespace() -> None:
    assert parse_header_values(["X-Foo:  bar  "]) == {"X-Foo": "bar"}


def test_parse_header_values_rejects_missing_colon() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_header_values(["bad-header"])


def test_parse_header_values_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="empty name"):
        parse_header_values([": value"])


def test_parse_cookie_values_keeps_equals_inside_value() -> None:
    assert parse_cookie_values(["session=abc=def"]) == {"session": "abc=def"}


def test_parse_cookie_values_rejects_no_equals() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_cookie_values(["lonely-cookie"])


def test_merge_auth_appends_cli_over_profile() -> None:
    base = AuthConfig(headers={"X-Profile": "p"}, cookies={"sid": "1"})
    merged = merge_auth(base, ["X-CLI: c"], ["sid=2"], None)
    assert merged.headers == {"X-Profile": "p", "X-CLI": "c"}
    assert merged.cookies == {"sid": "2"}


def test_build_header_args_emits_cookie_header() -> None:
    auth = AuthConfig(headers={"X-Token": "t"}, cookies={"a": "1", "b": "2"})
    args = build_header_args(auth)
    assert args == ["-H", "X-Token: t", "-H", "Cookie: a=1; b=2"]
