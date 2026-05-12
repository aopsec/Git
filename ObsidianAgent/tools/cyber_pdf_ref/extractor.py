from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from tools.cyber_pdf_ref.items import (
    extract_commands,
    extract_scripts,
    extract_snippets,
    extract_techniques,
    extract_tools,
    extract_urls,
    split_pages,
)
from tools.cyber_pdf_ref.models import PdfMeta, PdfRecord
from tools.cyber_pdf_ref.patterns import (
    CYBER_KEYWORDS,
    EXCLUDED_PARTS,
    EXCLUDED_SUBPATHS,
    HARD_NON_CYBER_MARKERS,
    NON_CYBER_MARKERS,
    STRONG_CYBER_KEYWORDS,
)


def discover_pdfs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        if _is_excluded(path):
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: str(item))


def build_records(paths: list[Path]) -> list[PdfRecord]:
    records: list[PdfRecord] = []
    seen: dict[str, Path] = {}
    for path in paths:
        meta = _pdf_meta(path)
        text = _pdf_text(path)
        pages = split_pages(text)
        status, reason = _classify(path, text, meta, meta.sha256 in seen)
        canonical_sha = meta.sha256 if meta.sha256 not in seen else _sha256(seen[meta.sha256])
        seen.setdefault(meta.sha256, path)
        tools = extract_tools(pages)
        commands = extract_commands(pages)
        urls = extract_urls(pages)
        snippets = extract_snippets(pages)
        techniques = extract_techniques(pages)
        scripts = extract_scripts(pages)
        records.append(
            PdfRecord(
                meta=meta,
                status=status,
                reason=reason,
                canonical_sha=canonical_sha,
                text_chars=len(text),
                tools=tools,
                commands=commands,
                urls=urls,
                snippets=snippets,
                techniques=techniques,
                scripts=scripts,
            )
        )
    return records


def slug(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-") or "source"


def _is_excluded(path: Path) -> bool:
    text = str(path)
    return any(part in EXCLUDED_PARTS for part in path.parts) or any(
        item in text for item in EXCLUDED_SUBPATHS
    )


def _pdf_meta(path: Path) -> PdfMeta:
    info = _run_text(["pdfinfo", str(path)])
    values: dict[str, str] = {}
    for line in info.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return PdfMeta(
        path=path,
        sha256=_sha256(path),
        size_bytes=path.stat().st_size,
        title=values.get("Title", "") or path.stem,
        author=values.get("Author", ""),
        pages=_to_int(values.get("Pages", "0")),
        encrypted=values.get("Encrypted", "no").lower().startswith("yes"),
        javascript=values.get("JavaScript", "no").lower().startswith("yes"),
    )


def _pdf_text(path: Path) -> str:
    return _run_text(["pdftotext", "-layout", str(path), "-"])


def _run_text(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    return completed.stdout if completed.returncode == 0 else ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classify(path: Path, text: str, meta: PdfMeta, duplicate: bool) -> tuple[str, str]:
    if duplicate:
        return ("duplicate", "exact sha256 duplicate of another discovered PDF")
    if len(text.strip()) < max(100, meta.pages * 20):
        return ("needs-ocr", "low extracted text coverage or extraction unavailable")
    source_label = f"{path.name}\n{meta.title}".lower()
    if any(marker in source_label for marker in HARD_NON_CYBER_MARKERS):
        return ("non-cyber", "filename/title identifies academic/admin non-cyber source")
    haystack = f"{source_label}\n{text}".lower()
    hits = sum(1 for keyword in CYBER_KEYWORDS if keyword in haystack)
    strong_hits = sum(1 for keyword in STRONG_CYBER_KEYWORDS if keyword in haystack)
    non_cyber = any(marker in haystack for marker in NON_CYBER_MARKERS)
    if non_cyber and strong_hits < 2:
        return ("non-cyber", "academic/admin PDF without enough cyber-specific signals")
    if "portfolio" in haystack and strong_hits > 0:
        return ("cyber-adjacent", "portfolio/course document with cyber skills listed")
    if strong_hits >= 3 or (strong_hits >= 1 and hits >= 6):
        return ("cyber-active", f"{strong_hits} strong cyber signals, {hits} total signals")
    if strong_hits > 0 or hits >= 3:
        return ("cyber-adjacent", f"{strong_hits} strong cyber signals, {hits} total signals")
    return ("non-cyber", "no cyber/security signals above threshold")


def _to_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
