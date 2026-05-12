import socket
from pathlib import Path

import pytest

from bbwebscan import targets as targets_module
from bbwebscan.models import AuthConfig, RetryPolicy, RunConfig
from bbwebscan.targets import (
    collect_targets,
    enforce_scope_gate,
    filter_urls_in_scope,
    host_in_scope,
    is_public_suffix_only,
    normalize_target,
    resolve_host,
)


def _config(target_inputs: list[str], allowed: list[str] | None = None) -> RunConfig:
    return RunConfig(
        program_name="t",
        seed_urls=[],
        allowed_hosts=allowed or [],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx"],
        wordlist=Path("/tmp/w"),
        threads=1,
        rate=1,
        tool_timeout_s=1,
        command_wall_clock_s=1,
        retry=RetryPolicy(),
        output_dir=Path("/tmp/o"),
        target_inputs=target_inputs,
    )


def test_normalize_target_adds_https() -> None:
    target = normalize_target("example.com")
    assert target.host == "example.com"
    assert target.seed_url == "https://example.com"


def test_normalize_target_refuses_bare_tld() -> None:
    with pytest.raises(ValueError, match="public-suffix"):
        normalize_target("com")


def test_normalize_target_refuses_compound_suffix() -> None:
    with pytest.raises(ValueError, match="public-suffix"):
        normalize_target("co.uk")


def test_normalize_target_refuses_exact_shared_hosting_suffix() -> None:
    with pytest.raises(ValueError, match="public-suffix"):
        normalize_target("github.io")


def test_normalize_target_allows_owned_shared_hosting_subdomain() -> None:
    target = normalize_target("App.GitHub.IO.")
    assert target.host == "app.github.io"
    assert target.seed_url == "https://app.github.io"


def test_is_public_suffix_only() -> None:
    assert is_public_suffix_only("com") is True
    assert is_public_suffix_only("CO.UK") is True
    assert is_public_suffix_only("pages.dev") is True
    assert is_public_suffix_only("app.pages.dev") is False
    assert is_public_suffix_only("example.com") is False


def test_collect_targets_single_host_no_allowed_hosts_ok() -> None:
    targets, decisions, allowed = collect_targets(_config(["example.com"]))
    assert len(targets) == 1
    assert all(d.allowed for d in decisions)
    assert allowed == ["example.com"]


def test_scope_gate_refuses_multi_host_without_allowed() -> None:
    with pytest.raises(ValueError, match="implicit scope"):
        collect_targets(_config(["example.com", "evil.test"]))


def test_scope_gate_allows_multi_host_when_allowed_set() -> None:
    targets, decisions, _ = collect_targets(
        _config(["example.com", "api.example.com"], allowed=["example.com"])
    )
    assert len(targets) == 2
    assert all(d.allowed for d in decisions)


def test_enforce_scope_gate_passes_with_explicit_allowed() -> None:
    enforce_scope_gate(_config([], allowed=["example.com"]), [])


def test_filter_urls_in_scope_rejects_outside() -> None:
    urls, decisions = filter_urls_in_scope(
        ["https://example.com/a", "https://evil.test/b"], ["example.com"], []
    )
    assert urls == ["https://example.com/a"]
    assert any(not d.allowed for d in decisions)


def test_filter_urls_in_scope_denies_subdomain_in_denylist() -> None:
    urls, decisions = filter_urls_in_scope(
        ["https://admin.example.com/x"], ["example.com"], ["admin.example.com"]
    )
    assert urls == []
    assert decisions[0].reason.startswith("denied")


def test_filter_urls_in_scope_skips_already_decided() -> None:
    seen = {"https://example.com/a"}
    urls, decisions = filter_urls_in_scope(
        ["https://example.com/a", "https://example.com/b"],
        ["example.com"],
        [],
        already_decided=seen,
    )
    assert urls == ["https://example.com/b"]
    assert len(decisions) == 1
    assert decisions[0].value == "https://example.com/b"


def test_filter_urls_in_scope_default_keeps_all() -> None:
    urls, decisions = filter_urls_in_scope(
        ["https://example.com/a", "https://example.com/b"], ["example.com"], []
    )
    assert len(urls) == 2
    assert len(decisions) == 2


def test_host_in_scope_canonicalizes_mixed_case_deny_rule_first() -> None:
    decision = host_in_scope(
        "ADMIN.Example.COM.",
        ["Example.COM."],
        ["Admin.Example.Com."],
    )
    assert decision.allowed is False
    assert decision.reason == "denied:admin.example.com"


def test_host_in_scope_canonicalizes_mixed_case_allow_rule() -> None:
    decision = host_in_scope("Api.Example.COM.", ["Example.COM."], [])
    assert decision.allowed is True
    assert decision.reason == "allowed:example.com"


def test_filter_urls_in_scope_canonicalizes_trailing_dot_hosts() -> None:
    urls, decisions = filter_urls_in_scope(
        ["https://App.Example.COM./login"], ["example.com"], []
    )
    assert urls == ["https://App.Example.COM./login"]
    assert decisions[0].allowed is True


def test_collect_targets_refuses_shared_suffix_allowed_host() -> None:
    with pytest.raises(ValueError, match="shared-hosting suffix"):
        collect_targets(_config(["app.github.io"], allowed=["github.io"]))


def test_is_public_suffix_only_uses_psl_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[SEC-BBW-02] Public-suffix checks route through get_tld, not get_sld."""
    fake_tld_calls: list[str] = []
    fake_sld_calls: list[str] = []

    def fake_sld(host: str) -> str:
        fake_sld_calls.append(host)
        return "leaf.example.zz"

    def fake_tld(host: str) -> str:
        fake_tld_calls.append(host)
        return "co.zz" if host == "co.zz" else "zz"

    monkeypatch.setattr(
        targets_module,
        "_PSL_ADAPTER",
        targets_module.PublicSuffixAdapter(get_sld=fake_sld, get_tld=fake_tld),
    )
    assert targets_module.is_public_suffix_only("co.zz") is True
    assert targets_module.is_public_suffix_only("acme.example.com") is False
    assert fake_tld_calls == ["co.zz", "acme.example.com"]
    assert fake_sld_calls == []


def test_is_public_suffix_only_fails_closed_without_psl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(targets_module, "_PSL_ADAPTER", None)
    monkeypatch.setattr(targets_module, "_PSL_IMPORT_ERROR", None)
    with pytest.raises(RuntimeError, match="publicsuffix2 is required"):
        targets_module.is_public_suffix_only("example.com")


def test_resolve_host_returns_ip_for_public_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v0.4.3 (Item 8): successful gethostbyname returns the IP string."""
    monkeypatch.setattr(socket, "gethostbyname", lambda _h: "93.184.216.34")
    assert resolve_host("example.com") == "93.184.216.34"


def test_resolve_host_returns_none_on_gaierror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v0.4.3 (Item 8): unresolvable host yields None, not an exception."""

    def boom(_h: str) -> str:
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "gethostbyname", boom)
    assert resolve_host("definitely-not-real.test") is None


def test_resolve_host_returns_none_on_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_h: str) -> str:
        raise OSError("network unreachable")

    monkeypatch.setattr(socket, "gethostbyname", boom)
    assert resolve_host("definitely-not-real.test") is None
