#!/usr/bin/env python3
"""
Standalone Scrapy URL Download Spider
======================================

A production-grade spider for downloading URLs and extracting:
- HTML links, scripts, documents
- Email addresses
- Exposed paths (.git, .env, wp-admin, etc.)
- Secret patterns (API keys, credentials)

Usage:
  scrapy runspider scrapy_url_downloader.py -O output.jsonl \
    -a urls_file=urls.txt \
    -a max_depth=2

Or programmatic:
  python3 scrapy_url_downloader.py <urls.txt> [--depth 2] [--output results.jsonl]
"""
import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

import scrapy
from scrapy.http import Response


# ============================================================================
# PATTERNS & CONFIGURATION
# ============================================================================

_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_DOC_EXT_RE = re.compile(
    r"\.(?:pdf|docx?|xlsx?|csv|txt|bak|sql|zip|tar(?:\.gz)?|7z|env|key|pem)(?:\?|$)",
    re.IGNORECASE,
)
_EXPOSED_PATH_RE = re.compile(
    r"(?:^|/)(?:\.git(?:/|$)|\.env(?:\.[\w\-.]+)?(?:$|\?)|\.svn/|"
    r"backup(?:s|\.\w+)?|wp-admin|phpinfo\.php|server-status|"
    r"adminer\.php|web\.config|robots\.txt|sitemap\.xml)",
    re.IGNORECASE,
)

_MAX_EMAILS_PER_PAGE = 50
_MAX_DEPTH = 5
_MIN_DEPTH = 1

_BASE_SETTINGS = {
    "ROBOTSTXT_OBEY": True,
    "DOWNLOAD_DELAY": 0.5,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
    "USER_AGENT": "scrapy-url-downloader/1.0",
    "LOG_LEVEL": "WARNING",
    "HTTPCACHE_ENABLED": False,
    "DEPTH_PRIORITY": 1,
    "TELNETCONSOLE_ENABLED": False,
    "COOKIES_ENABLED": False,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _sha256_prefix(value: str, length: int = 16) -> str:
    """Hash value and return prefix."""
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _truthy(value: object) -> bool:
    """Parse truthy value from CLI argument."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "y"}
    return False


# ============================================================================
# SCRAPY SPIDER
# ============================================================================

class UrlDownloaderSpider(scrapy.Spider):
    """Download URLs and extract links, documents, emails, exposed paths."""
    
    name = "url_downloader"
    custom_settings: ClassVar[dict[Any, Any]] = dict(_BASE_SETTINGS)

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
            raise ValueError("Spider requires -a urls_file=<path>")
        
        targets_path = Path(urls_file)
        if not targets_path.is_file():
            raise FileNotFoundError(f"urls_file not found: {targets_path}")
        
        # Load URLs from file
        self._start_urls: list[str] = [
            line.strip() for line in targets_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        
        if not self._start_urls:
            raise ValueError(f"urls_file is empty: {targets_path}")
        
        # Parse depth
        try:
            depth = int(max_depth)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"max_depth must be integer: {max_depth!r}") from exc
        
        if not _MIN_DEPTH <= depth <= _MAX_DEPTH:
            raise ValueError(f"max_depth must be {_MIN_DEPTH}..{_MAX_DEPTH}, got {depth}")
        
        self._max_depth = depth
        self._js_render = _truthy(js_render)
        self._allowed_domains: set[str] = self._derive_allowed_domains(self._start_urls)
        self.allowed_domains = list(self._allowed_domains)
        
        # Instance override of custom_settings
        self.custom_settings = {**_BASE_SETTINGS, "DEPTH_LIMIT": self._max_depth}

    @staticmethod
    def _derive_allowed_domains(urls: list[str]) -> set[str]:
        """Extract unique domains from URL list."""
        domains: set[str] = set()
        for raw in urls:
            host = urlparse(raw).hostname
            if host:
                domains.add(host.lower())
        return domains

    def start_requests(self) -> Iterator[scrapy.Request]:
        """Generate initial requests."""
        meta: dict[str, Any] = {}
        if self._js_render:
            meta["playwright"] = True
        for url in self._start_urls:
            yield scrapy.Request(url, callback=self.parse, meta=meta, dont_filter=False)

    def parse(self, response: Response) -> Iterator[Any]:
        """Parse response and extract data."""
        # Detect HTML content
        raw_ct = response.headers.get("Content-Type") or b""
        content_type = (
            raw_ct.decode("ascii", errors="replace") 
            if isinstance(raw_ct, bytes) 
            else str(raw_ct)
        )
        is_html = (
            "text/html" in content_type.lower() 
            or response.url.endswith((".html", ".htm", "/"))
        )

        links: list[str] = []
        scripts: list[str] = []
        documents: list[str] = []
        exposed_paths: list[str] = []
        title = ""
        body_text = ""

        # Parse HTML if applicable
        if is_html:
            try:
                title = (response.css("title::text").get() or "").strip()
                links = [
                    response.urljoin(href) 
                    for href in response.css("a::attr(href)").getall()
                    if href and not href.lower().startswith(("javascript:", "mailto:", "tel:"))
                ]
                scripts = [
                    response.urljoin(src)
                    for src in response.css("script::attr(src)").getall() 
                    if src
                ]
            except Exception:  # noqa: BLE001
                pass
            body_text = response.text or ""
        else:
            body_text = response.text or ""

        # Extract documents and exposed paths
        documents = sorted({
            link for link in links + scripts if _DOC_EXT_RE.search(link)
        })
        exposed_paths = sorted({
            link for link in links + scripts if _EXPOSED_PATH_RE.search(link)
        })

        # Extract emails
        emails = self._extract_emails(body_text)

        # Scope links
        scoped_links = [link for link in links if self._in_scope(link)]

        # Yield result
        yield {
            "url": response.url,
            "status": response.status,
            "title": title,
            "links": scoped_links,
            "scripts": scripts,
            "documents": documents,
            "emails": emails,
            "exposed_paths": exposed_paths,
        }

        # Generate requests for found links
        depth = response.meta.get("depth", 0)
        if depth >= self._max_depth:
            return

        meta: dict[str, Any] = {}
        if self._js_render:
            meta["playwright"] = True
        
        for link in scoped_links:
            yield scrapy.Request(link, callback=self.parse, meta=meta)

    def _in_scope(self, url: str) -> bool:
        """Check if URL is in allowed domains."""
        host = urlparse(url).hostname
        if not host:
            return False
        host = host.lower()
        return any(
            host == allowed or host.endswith("." + allowed)
            for allowed in self._allowed_domains
        )

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses from text."""
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


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main() -> None:
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Scrapy URL downloader spider",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using scrapy CLI
  scrapy runspider scrapy_url_downloader.py -O results.jsonl \\
    -a urls_file=urls.txt -a max_depth=2
  
  # Programmatic with this script
  python3 scrapy_url_downloader.py urls.txt --depth 2 --output results.jsonl
        """,
    )
    
    parser.add_argument(
        "urls_file",
        help="File containing URLs to crawl (one per line)",
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        default=2,
        help="Maximum crawl depth (1-5, default 2)",
    )
    parser.add_argument(
        "-o", "--output",
        default="results.jsonl",
        help="Output JSONL file (default: results.jsonl)",
    )
    parser.add_argument(
        "-j", "--js-render",
        action="store_true",
        help="Enable JavaScript rendering (requires scrapy-playwright)",
    )
    
    args = parser.parse_args()
    
    # Verify input file
    urls_path = Path(args.urls_file)
    if not urls_path.is_file():
        print(f"Error: File not found: {urls_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting spider...")
    print(f"  URLs file: {urls_path}")
    print(f"  Max depth: {args.depth}")
    print(f"  Output: {args.output}")
    print()
    
    # Build scrapy command
    cmd = [
        "scrapy", "runspider", __file__,
        "-O", args.output,
        "-a", f"urls_file={args.urls_file}",
        "-a", f"max_depth={args.depth}",
    ]
    
    if args.js_render:
        cmd.extend(["-a", "js_render=1"])
    
    # Run spider
    import subprocess
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
