import socket
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, cast
from urllib.parse import urlparse

from bbwebscan.models import NormalizedTarget, RunConfig, ScopeDecision


class PublicSuffixAdapter(NamedTuple):
    get_sld: Callable[[str], str | None]
    get_tld: Callable[[str], str | None]


try:
    import publicsuffix2 as _publicsuffix2  # type: ignore[import-untyped]
except ImportError as exc:
    _PSL_IMPORT_ERROR: ImportError | None = exc
    _PSL_ADAPTER: PublicSuffixAdapter | None = None
else:
    _PSL_IMPORT_ERROR = None
    _PSL_ADAPTER = PublicSuffixAdapter(
        get_sld=cast(Callable[[str], str | None], _publicsuffix2.get_sld),
        get_tld=cast(Callable[[str], str | None], _publicsuffix2.get_tld),
    )

SHARED_HOSTING_SUFFIX_DENYLIST: frozenset[str] = frozenset(
    {
        "github.io",
        "pages.dev",
        "azurewebsites.net",
        "appspot.com",
        "web.app",
        "netlify.app",
        "vercel.app",
        "herokuapp.com",
    }
)


def canonical_host(host: str) -> str:
    """[SEC-BBW-01] Canonicalize host policy inputs before scope decisions."""
    return host.strip().lower().rstrip(".")


def _require_psl_adapter() -> PublicSuffixAdapter:
    if _PSL_ADAPTER is not None:
        return _PSL_ADAPTER
    detail = f" ({_PSL_IMPORT_ERROR})" if _PSL_IMPORT_ERROR is not None else ""
    raise RuntimeError(
        "publicsuffix2 is required for scope-safe target validation; install "
        "bbwebscan dependencies or run `./.venv/bin/pip install 'publicsuffix2>=2.20191221'`"
        f"{detail}"
    )


def public_suffix(host: str) -> str:
    adapter = _require_psl_adapter()
    suffix = adapter.get_tld(canonical_host(host))
    return canonical_host(suffix) if isinstance(suffix, str) else ""


def registrable_domain(host: str) -> str:
    adapter = _require_psl_adapter()
    root = adapter.get_sld(canonical_host(host))
    if not isinstance(root, str) or not root:
        raise ValueError(f"Could not derive registrable domain for host: {host}")
    return canonical_host(root)


def is_shared_hosting_suffix(host: str) -> bool:
    return canonical_host(host) in SHARED_HOSTING_SUFFIX_DENYLIST


def load_target_lines(config: RunConfig) -> list[str]:
    lines = list(config.target_inputs)
    if config.input_file is not None:
        lines.extend(Path(config.input_file).read_text(encoding="utf-8").splitlines())
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def is_public_suffix_only(host: str) -> bool:
    lowered = canonical_host(host)
    # [SEC-BBW-02] PSL is mandatory now; exact high-risk shared suffixes are
    # blocked as roots, while owned subdomains such as app.github.io remain valid.
    return public_suffix(lowered) == lowered or is_shared_hosting_suffix(lowered)


def normalize_target(value: str) -> NormalizedTarget:
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    if parsed.hostname is None:
        raise ValueError(f"Could not normalize target: {value}")
    host = canonical_host(parsed.hostname)
    if is_public_suffix_only(host):
        raise ValueError(f"Refusing public-suffix or bare TLD as target: {value}")
    netloc = f"{host}:{parsed.port}" if parsed.port is not None else host
    seed_url = f"{parsed.scheme}://{netloc}".rstrip("/")
    return NormalizedTarget(raw=value, host=host, seed_url=seed_url)


def derive_allowed_hosts(config: RunConfig, targets: list[NormalizedTarget]) -> list[str]:
    if config.allowed_hosts:
        allowed_hosts = [canonical_host(host) for host in config.allowed_hosts]
        unsafe_hosts = [host for host in allowed_hosts if is_public_suffix_only(host)]
        if unsafe_hosts:
            raise ValueError(
                "Refusing public-suffix or shared-hosting suffix in allowed_hosts: "
                f"{', '.join(unsafe_hosts)}"
            )
        return allowed_hosts
    return sorted({target.host for target in targets})


def _canonical_host_list(hosts: list[str]) -> list[str]:
    return [canonical for host in hosts if (canonical := canonical_host(host))]


def host_in_scope(host: str, allowed_hosts: list[str], denied_hosts: list[str]) -> ScopeDecision:
    lowered_host = canonical_host(host)
    for denied_host in _canonical_host_list(denied_hosts):
        if lowered_host == denied_host or lowered_host.endswith(f".{denied_host}"):
            return ScopeDecision(value=host, allowed=False, reason=f"denied:{denied_host}")
    for allowed_host in _canonical_host_list(allowed_hosts):
        if lowered_host == allowed_host or lowered_host.endswith(f".{allowed_host}"):
            return ScopeDecision(value=host, allowed=True, reason=f"allowed:{allowed_host}")
    return ScopeDecision(value=host, allowed=False, reason="not-allowed")


def enforce_scope_gate(config: RunConfig, targets: list[NormalizedTarget]) -> None:
    if config.allowed_hosts:
        return
    distinct_hosts = {target.host for target in targets}
    if len(distinct_hosts) > 1:
        raise ValueError(
            "Refusing implicit scope: profile.allowed_hosts is empty and target inputs span "
            f"{len(distinct_hosts)} hosts ({', '.join(sorted(distinct_hosts))}). "
            "Set allowed_hosts in the profile or run one host at a time."
        )


def collect_targets(
    config: RunConfig,
) -> tuple[list[NormalizedTarget], list[ScopeDecision], list[str]]:
    normalized = [normalize_target(value) for value in load_target_lines(config)]
    unique_targets = {target.seed_url: target for target in normalized}
    targets = list(unique_targets.values())
    enforce_scope_gate(config, targets)
    allowed_hosts = derive_allowed_hosts(config, targets)
    decisions = [
        host_in_scope(target.host, allowed_hosts, config.denied_hosts) for target in targets
    ]
    live_targets = [
        target for target, decision in zip(targets, decisions, strict=True) if decision.allowed
    ]
    return live_targets, decisions, allowed_hosts


def resolve_host(host: str, *, timeout: float = 2.0) -> str | None:
    """Best-effort A/AAAA lookup. Returns the first IP, or None on failure.

    [v0.4.3 Item 8] Used by DNS preflight when --check-dns is set. Failure is
    non-fatal — operator may scan an internal/staging host that lacks public DNS.
    The timeout argument is reserved for a future switch to socket.getaddrinfo
    with a select() loop; gethostbyname does not honour it.
    """
    del timeout  # reserved for future use
    try:
        return socket.gethostbyname(host)
    except (OSError, socket.gaierror):
        return None


def filter_urls_in_scope(
    urls: list[str],
    allowed_hosts: list[str],
    denied_hosts: list[str],
    *,
    already_decided: set[str] | None = None,
) -> tuple[list[str], list[ScopeDecision]]:
    # [FIX-BBW-07] Short-circuit URLs whose scope was already decided in a prior stage.
    seen = already_decided if already_decided is not None else set()
    kept_urls: list[str] = []
    decisions: list[ScopeDecision] = []
    for url in urls:
        if url in seen:
            continue
        parsed = urlparse(url)
        if parsed.hostname is None:
            decisions.append(ScopeDecision(value=url, allowed=False, reason="invalid-url"))
            continue
        host_decision = host_in_scope(parsed.hostname, allowed_hosts, denied_hosts)
        # [FIX-BBW-02] Active-stage audit output should name the URL that was filtered.
        decision = ScopeDecision(
            value=url,
            allowed=host_decision.allowed,
            reason=host_decision.reason,
        )
        decisions.append(decision)
        if decision.allowed:
            kept_urls.append(url)
    unique_urls = list(dict.fromkeys(kept_urls))
    return unique_urls, decisions
