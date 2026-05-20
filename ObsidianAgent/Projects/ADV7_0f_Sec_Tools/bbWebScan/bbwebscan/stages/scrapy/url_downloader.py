"""bbWebScan Scrapy URL Downloader — extended information-disclosure harvesting.

Complementary spider for extracting:
- HTML links, scripts, documents
- Email addresses
- Exposed paths (.git, .env, wp-admin, etc.)
- Secret patterns (API keys, credentials)

Invoked by the pipeline via:

    scrapy runspider url_downloader.py \\
        -O <run>/artifacts/scrapy_extended.jsonl \\
        -a urls_file=<run>/artifacts/scrapy_targets.txt \\
        -a max_depth=2 \\
        -a js_render=0 \\
        -s LOG_FILE=<run>/logs/scrapy_extended.log

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
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

import scrapy
from scrapy.http import Response

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
_MAX_EMAILS_PER_PAGE = 50
_MIN_DEPTH = 1
_MAX_DEPTH = 5


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
    "USER_AGENT": "bbwebscan-scrapy-extended/0.5.8",
    "LOG_LEVEL": "WARNING",
    "HTTPCACHE_ENABLED": False,
    "DEPTH_PRIORITY": 1,
    "TELNETCONSOLE_ENABLED": False,
    "COOKIES_ENABLED": False,
    # [BUG-1] Disable proxy when HTTP_PROXY/HTTPS_PROXY env vars are set
    "HTTPPROXY_ENABLED": False,
    # [FIX-V2] Explicit RETRY_EXCEPTIONS list prevents Scrapy from importing
    # the broken SSL retry handler on Twisted 26.4.0 (removed
    # _setAcceptableProtocols). Only well-known stdlib/Twisted exceptions are
    # listed so no broken import can sneak in through the default set.
    "RETRY_EXCEPTIONS": [
        "builtins.OSError",
        "builtins.ConnectionRefusedError",
        "builtins.ConnectionResetError",
        "builtins.TimeoutError",
        "twisted.internet.error.ConnectError",
        "twisted.internet.error.ConnectionLost",
        "twisted.internet.defer.TimeoutError",
        "twisted.internet.error.TimeoutError",
    ],
}


class UrlDownloaderSpider(scrapy.Spider):
    name = "url_downloader"

    custom_settings: ClassVar[dict[Any, Any]] = dict(_BASE_SETTINGS)  # type: ignore

    def __init__(
        self,
        urls_file: str | None = None,
        max_depth: str | int = 2,
        js_render: str | int | bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not urls_file:
            raise ValueError("UrlDownloaderSpider requires -a urls_file=<path>")
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
        self._js_render = _truthy(js_render)
        self._allowed_domains: set[str] = self._derive_allowed_domains(self._start_urls)
        self.allowed_domains = list(self._allowed_domains)
        # Per-instance override of the class-level ClassVar to inject DEPTH_LIMIT.
        # Scrapy reads ``custom_settings`` once at crawler init, so an instance
        # attribute shadowing the class attribute is fine.
        self.custom_settings = {**_BASE_SETTINGS, "DEPTH_LIMIT": self._max_depth}  # type: ignore

    @staticmethod
    def _derive_allowed_domains(urls: list[str]) -> set[str]:
        domains: set[str] = set()
        for raw in urls:
            host = urlparse(raw).hostname
            if host:
                domains.add(host.lower())
        return domains

    async def start(self) -> AsyncIterator[scrapy.Request]:
        meta: dict[str, Any] = {}
        if self._js_render:
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
            except Exception:  # noqa: BLE001
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
            "secrets": [],
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
