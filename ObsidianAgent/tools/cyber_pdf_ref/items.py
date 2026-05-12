from __future__ import annotations

import re

from tools.cyber_pdf_ref.models import ExtractedItem
from tools.cyber_pdf_ref.patterns import (
    CODE_RE,
    COMMAND_RE,
    CYBER_KEYWORDS,
    TECHNIQUE_KEYWORDS,
    TOOL_NAMES,
    URL_RE,
)

MAX_SNIPPETS = 120
MAX_TECHNIQUES = 160


def split_pages(text: str) -> list[tuple[int, str]]:
    chunks = text.split("\f")
    pages: list[tuple[int, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        if chunk.strip():
            pages.append((index, chunk))
    return pages or [(1, text)]


def extract_tools(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    tools: list[ExtractedItem] = []
    for tool in TOOL_NAMES:
        lowered_tool = tool.lower()
        for page, text in pages:
            if lowered_tool in text.lower():
                tools.append(ExtractedItem(value=tool, page=page))
                break
    return tools


def extract_commands(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    commands: list[ExtractedItem] = []
    for page, text in pages:
        for line in text.splitlines():
            cleaned = _clean_line(line)
            if len(cleaned) <= 220 and COMMAND_RE.match(cleaned) and _looks_like_command(cleaned):
                commands.append(ExtractedItem(value=cleaned, page=page))
    return unique_items(commands)


def extract_urls(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    urls: list[ExtractedItem] = []
    for page, text in pages:
        urls.extend(ExtractedItem(value=url, page=page) for url in URL_RE.findall(text))
    return unique_items(urls)


def extract_snippets(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    snippets: list[ExtractedItem] = []
    for page, text in pages:
        for line in text.splitlines():
            cleaned = _clean_line(line)
            if not _is_short_operational_line(cleaned):
                continue
            if any(keyword in cleaned.lower() for keyword in CYBER_KEYWORDS):
                snippets.append(ExtractedItem(value=cleaned, page=page))
    return unique_items(snippets)[:MAX_SNIPPETS]


def extract_techniques(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    techniques: list[ExtractedItem] = []
    for page, text in pages:
        for line in text.splitlines():
            cleaned = _clean_line(line)
            lowered = cleaned.lower()
            if not _is_short_operational_line(cleaned):
                continue
            if any(keyword in lowered for keyword in TECHNIQUE_KEYWORDS):
                techniques.append(ExtractedItem(value=cleaned, page=page))
    return unique_items(techniques)[:MAX_TECHNIQUES]


def extract_scripts(pages: list[tuple[int, str]]) -> list[ExtractedItem]:
    scripts: list[ExtractedItem] = []
    for page, text in pages:
        for line in text.splitlines():
            cleaned = _clean_line(line)
            if 4 <= len(cleaned) <= 180 and CODE_RE.match(cleaned):
                scripts.append(ExtractedItem(value=cleaned, page=page))
    return unique_items(scripts)


def unique_items(values: list[ExtractedItem]) -> list[ExtractedItem]:
    unique: dict[str, ExtractedItem] = {}
    for item in values:
        unique.setdefault(item.value, item)
    return list(unique.values())


def _is_short_operational_line(value: str) -> bool:
    words = value.split()
    return 35 <= len(value) <= 180 and 5 <= len(words) <= 28


def _looks_like_command(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith(("$", "#")):
        return True
    if re.match(r"^(?:sudo\s+)?[a-z0-9_-]+[,.;:]", stripped):
        return False
    command_markers = (" -", " --", "/", "|", ">", "<", "&&", "http://", "https://", ".sh", ".py", ".go", "=")
    if any(marker in stripped for marker in command_markers):
        return True
    return stripped.startswith(("git clone", "docker ps", "docker compose", "systemctl ", "journalctl "))


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
