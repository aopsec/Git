"""bbWebScan Scrapy spider — information-disclosure recon crawler.

Invoked by the pipeline via:

    scrapy runspider bbspider.py \\
        -O <run>/artifacts/scrapy.jsonl \\
        -a urls_file=<run>/artifacts/scrapy_targets.txt \\
        -a max_depth=2 \\
        -a deep_mode=0 \\
        -a js_render=0 \\
        -s LOG_FILE=<run>/logs/scrapy.log

Design inspiration: ivan-sincek/scrapy-scraper (MIT) for JS file beautification
and link-extraction patterns. Re-implemented from scratch; no code re-use.

Output schema (one JSONL record per crawled response):

    {
        "url": str,
        "status": int,
        "title": str,
        "links": [str, ...],
        "scripts": [str, ...],
        "documents": [str, ...],
        "emails": [str, ...],
        "secrets": [{"name": str, "confidence": str, "evidence_sha256": str}, ...],
        "exposed_paths": [str, ...]
    }

Secrets policy: the raw matched string is NEVER persisted. Only a 16-char
SHA-256 prefix is recorded, along with the rule name and the URL where it
was matched. Mirrors the redaction discipline in
``bbwebscan.runner.redact_command_for_log``.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

import scrapy
import yaml
from scrapy.http import Response

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_PATTERNS_FILE = _DATA_DIR / "secrets_patterns.yml"

_EMAIL_RE: re.Pattern[str] = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_DOC_EXT_RE: re.Pattern[str] = re.compile(
    r"\.(?:pdf|docx?|xlsx?|csv|txt|bak|sql|zip|tar(?:\.gz)?|7z|env|key|pem)(?:\?|$)",
    re.IGNORECASE,
)
_EXPOSED_PATH_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:\.git(?:/|$)|\.env(?:\.[\w\-.]+)?(?:$|\?)|\.svn/|"
    r"backup(?:s|\.\w+)?|wp-admin|phpinfo\.php|server-status|"
    r"adminer\.php|web\.config|robots\.txt|sitemap\.xml)",
    re.IGNORECASE,
)
_CONFIDENCE_TO_SEVERITY: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
}
_MAX_EMAILS_PER_PAGE = 50
_MAX_SECRETS_PER_PAGE = 20
_MIN_DEPTH = 1
_MAX_DEPTH = 5


def _load_patterns() -> list[tuple[str, re.Pattern[str], str]]:
    """Load vendored secret patterns. Returns (name, compiled_regex, confidence) tuples."""
    if not _PATTERNS_FILE.is_file():
        return []
    raw = yaml.safe_load(_PATTERNS_FILE.read_text(encoding="utf-8")) or {}
    patterns: list[tuple[str, re.Pattern[str], str]] = []
    for entry in raw.get("patterns", []) or []:
        name = entry.get("name")
        regex = entry.get("regex")
        confidence = entry.get("confidence", "medium")
        if not isinstance(name, str) or not isinstance(regex, str):
            continue
        try:
            compiled = re.compile(regex)
        except re.error:
            continue
        if confidence not in _CONFIDENCE_TO_SEVERITY:
            confidence = "medium"
        patterns.append((name, compiled, confidence))
    return patterns


def _sha256_prefix(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "y"}
    return False


_BASE_SETTINGS: dict[str, Any] = {
    "ROBOTSTXT_OBEY": True,
    "DOWNLOAD_DELAY": 0.5,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
    "USER_AGENT": "bbwebscan-scrapy/0.5.3",
    "LOG_LEVEL": "WARNING",
    "HTTPCACHE_ENABLED": False,
    "DEPTH_PRIORITY": 1,
    "TELNETCONSOLE_ENABLED": False,
    "COOKIES_ENABLED": False,
}


class BbSpider(scrapy.Spider):
    name = "bbwebscan"

    custom_settings: ClassVar[dict[Any, Any]] = dict(_BASE_SETTINGS)

    def __init__(
        self,
        urls_file: str | None = None,
        max_depth: str | int = 2,
        deep_mode: str | int | bool = False,
        js_render: str | int | bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not urls_file:
            raise ValueError("BbSpider requires -a urls_file=<path>")
        targets_path = Path(urls_file)
        if not targets_path.is_file():
            raise FileNotFoundError(f"urls_file not found: {targets_path}")
        self._start_urls: list[str] = [
            line.strip() for line in targets_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not self._start_urls:
            raise ValueError(f"urls_file is empty: {targets_path}")
        try:
            depth = int(max_depth)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"max_depth must be an integer: {max_depth!r}") from exc
        if not _MIN_DEPTH <= depth <= _MAX_DEPTH:
            raise ValueError(
                f"max_depth must be in {_MIN_DEPTH}..{_MAX_DEPTH}, got {depth}",
            )
        self._max_depth = depth
        self._deep_mode = _truthy(deep_mode)
        self._js_render = _truthy(js_render)
        self._patterns = _load_patterns() if self._deep_mode else []
        self._allowed_domains: set[str] = self._derive_allowed_domains(self._start_urls)
        self.allowed_domains = list(self._allowed_domains)
        # Per-instance override of the class-level ClassVar to inject DEPTH_LIMIT.
        # Scrapy reads ``custom_settings`` once at crawler init, so an instance
        # attribute shadowing the class attribute is fine.
        self.custom_settings = {**_BASE_SETTINGS, "DEPTH_LIMIT": self._max_depth}

    @staticmethod
    def _derive_allowed_domains(urls: list[str]) -> set[str]:
        domains: set[str] = set()
        for raw in urls:
            host = urlparse(raw).hostname
            if host:
                domains.add(host.lower())
        return domains

    def start_requests(self) -> Iterator[scrapy.Request]:
        meta: dict[str, Any] = {}
        if self._js_render:
            # Opt-in per-request to scrapy-playwright when available.
            # If scrapy-playwright isn't installed, Scrapy ignores the meta key.
            meta["playwright"] = True
        for url in self._start_urls:
            yield scrapy.Request(url, callback=self.parse, meta=meta, dont_filter=False)

    def parse(self, response: Response) -> Iterator[Any]:
        raw_ct = response.headers.get("Content-Type") or b""
        content_type = raw_ct.decode("ascii", errors="replace") if isinstance(
            raw_ct, bytes,
        ) else str(raw_ct)
        is_html = "text/html" in content_type.lower() or response.url.endswith((
            ".html", ".htm", "/",
        ))

        links: list[str] = []
        scripts: list[str] = []
        documents: list[str] = []
        exposed_paths: list[str] = []
        title = ""
        body_text = ""

        if is_html:
            try:
                title = (response.css("title::text").get() or "").strip()
                links = [
                    response.urljoin(href) for href in response.css("a::attr(href)").getall()
                    if href and not href.lower().startswith(("javascript:", "mailto:", "tel:"))
                ]
                scripts = [
                    response.urljoin(src)
                    for src in response.css("script::attr(src)").getall() if src
                ]
            except Exception:  # noqa: BLE001 — parsel can raise on malformed HTML
                links = []
                scripts = []
            body_text = response.text or ""
        else:
            body_text = response.text or ""

        documents = sorted({
            link for link in links + scripts if _DOC_EXT_RE.search(link)
        })
        exposed_paths = sorted({
            link for link in links + scripts if _EXPOSED_PATH_RE.search(link)
        })

        emails = self._extract_emails(body_text)
        secrets = self._extract_secrets(body_text, response.url) if self._deep_mode else []

        scoped_links = [
            link for link in links if self._in_scope(link)
        ]

        yield {
            "url": response.url,
            "status": response.status,
            "title": title,
            "links": scoped_links,
            "scripts": scripts,
            "documents": documents,
            "emails": emails,
            "secrets": secrets,
            "exposed_paths": exposed_paths,
        }

        depth = response.meta.get("depth", 0)
        if depth >= self._max_depth:
            return

        meta: dict[str, Any] = {}
        if self._js_render:
            meta["playwright"] = True
        for link in scoped_links:
            yield scrapy.Request(link, callback=self.parse, meta=meta)

    def _in_scope(self, url: str) -> bool:
        host = urlparse(url).hostname
        if not host:
            return False
        host = host.lower()
        return any(host == allowed or host.endswith("." + allowed)
                   for allowed in self._allowed_domains)

    def _extract_emails(self, text: str) -> list[str]:
        if not text:
            return []
        found: list[str] = []
        seen: set[str] = set()
        for match in _EMAIL_RE.finditer(text):
            addr = match.group(0).lower()
            if addr not in seen:
                seen.add(addr)
                found.append(addr)
                if len(found) >= _MAX_EMAILS_PER_PAGE:
                    break
        return found

    def _extract_secrets(self, text: str, source_url: str) -> list[dict[str, str]]:
        if not text or not self._patterns:
            return []
        hits: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for name, pattern, confidence in self._patterns:
            for match in pattern.finditer(text):
                value = match.group(0)
                digest = _sha256_prefix(value)
                key = (name, digest)
                if key in seen:
                    continue
                seen.add(key)
                hits.append({
                    "name": name,
                    "confidence": confidence,
                    "evidence_sha256": digest,
                    "source_url": source_url,
                })
                if len(hits) >= _MAX_SECRETS_PER_PAGE:
                    return hits
        return hits
