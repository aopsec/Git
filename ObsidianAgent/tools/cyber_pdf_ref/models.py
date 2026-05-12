from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExtractedItem:
    value: str
    page: int


@dataclass(frozen=True)
class PdfMeta:
    path: Path
    sha256: str
    size_bytes: int
    title: str
    author: str
    pages: int
    encrypted: bool
    javascript: bool


@dataclass
class PdfRecord:
    meta: PdfMeta
    status: str
    reason: str
    canonical_sha: str
    text_chars: int = 0
    tools: list[ExtractedItem] = field(default_factory=list)
    commands: list[ExtractedItem] = field(default_factory=list)
    urls: list[ExtractedItem] = field(default_factory=list)
    snippets: list[ExtractedItem] = field(default_factory=list)
    techniques: list[ExtractedItem] = field(default_factory=list)
    scripts: list[ExtractedItem] = field(default_factory=list)


@dataclass(frozen=True)
class PdfInputSet:
    requested_paths: tuple[Path, ...]
    existing_paths: tuple[Path, ...]
    missing_paths: tuple[Path, ...]


@dataclass(frozen=True)
class VaultRenderResult:
    expected_sources: int
    found_sources: int
    copied_pdfs: int
    source_notes: int
    needs_ocr: int
    stale_files_removed: int
    missing_paths: tuple[Path, ...] = ()
    hash_mismatches: tuple[str, ...] = ()
