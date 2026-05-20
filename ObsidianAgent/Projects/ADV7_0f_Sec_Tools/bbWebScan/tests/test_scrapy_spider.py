"""Spider-level tests for bbWebScan's Scrapy crawler.

These tests exercise the pure helpers in ``bbwebscan.stages.scrapy.bbspider``
without actually spinning up a Scrapy crawler — the crawler itself is
covered indirectly through ``test_scrapy_stage.py`` (which exercises the
output schema via a fixture).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bbwebscan.stages.scrapy import bbspider


def test_load_patterns_returns_compiled_rules() -> None:
    patterns = bbspider._load_patterns()
    assert patterns, "vendored secrets_patterns.yml must yield at least one rule"
    names = {name for name, _, _ in patterns}
    assert "aws-access-key-id" in names
    assert "github-personal-access-token" in names
    assert "pem-private-key" in names
    for name, compiled, confidence in patterns:
        assert isinstance(name, str)
        assert hasattr(compiled, "search")
        assert confidence in {"low", "medium", "high"}


def test_sha256_prefix_matches_stdlib() -> None:
    value = "AKIAIOSFODNN7EXAMPLE"
    expected = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    assert bbspider._sha256_prefix(value) == expected
    assert bbspider._sha256_prefix(value, length=8) == expected[:8]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True), (False, False),
        (1, True), (0, False),
        ("1", True), ("0", False),
        ("true", True), ("FALSE", False),
        ("yes", True), ("no", False),
        ("", False), (None, False),
    ],
)
def test_truthy_normalises_scrapy_kwargs(value: object, expected: bool) -> None:
    assert bbspider._truthy(value) is expected


def test_derive_allowed_domains_lowercases_and_dedups() -> None:
    urls = [
        "https://APP.example.com/", "https://app.example.com/x",
        "https://other.example.org/", "ftp://bad-url-but-still:21/",
    ]
    result = bbspider.BbSpider._derive_allowed_domains(urls)
    assert "app.example.com" in result
    assert "other.example.org" in result
    # mixed case in input lowercased
    assert "APP.example.com" not in result


def test_email_extractor_dedups_and_caps(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    text = "contact alice@example.com, alice@example.com, bob@example.com"
    out = spider._extract_emails(text)
    assert out == ["alice@example.com", "bob@example.com"]


def test_email_extractor_cap_enforced(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    body = " ".join(f"user{i}@example.com" for i in range(120))
    out = spider._extract_emails(body)
    assert len(out) == bbspider._MAX_EMAILS_PER_PAGE


def test_secret_extractor_redacts_raw_value(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path, deep=True)
    fake_key = "AKIAIOSFODNN7EXAMPLE"
    hits = spider._extract_secrets(
        f"const cfg = {{ id: '{fake_key}' }};",
        "https://app.example.com/leak.js",
    )
    assert hits, "AWS key pattern should match"
    for hit in hits:
        assert fake_key not in hit.get("evidence_sha256", "")
        assert fake_key not in hit.get("name", "")
        assert fake_key not in hit.get("source_url", "")
        assert len(hit["evidence_sha256"]) == 16


def test_secret_extractor_disabled_when_not_deep(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path, deep=False)
    hits = spider._extract_secrets(
        "AKIAIOSFODNN7EXAMPLE", "https://app.example.com/leak.js",
    )
    assert hits == []


def test_in_scope_matches_subdomains_only(tmp_path: Path) -> None:
    spider = _make_spider(tmp_path)
    assert spider._in_scope("https://app.example.com/foo")
    assert spider._in_scope("https://sub.app.example.com/x")
    assert not spider._in_scope("https://evil.com/")


def _make_spider(tmp_path: Path, *, deep: bool = False) -> bbspider.BbSpider:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("https://app.example.com/\n", encoding="utf-8")
    return bbspider.BbSpider(
        urls_file=str(urls_file), max_depth=2, deep_mode=deep, js_render=False,
    )
