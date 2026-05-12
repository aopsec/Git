from __future__ import annotations

import hashlib
import shutil
from collections import defaultdict
from pathlib import Path

from tools.cyber_pdf_ref.extractor import slug
from tools.cyber_pdf_ref.models import PdfRecord, VaultRenderResult
from tools.cyber_pdf_ref.sections import (
    certification,
    command_index,
    index,
    manifest,
    policy,
    roadmap,
    scripts,
    source_filename,
    technique_index,
    tool_index,
)
from tools.cyber_pdf_ref.source_note import source_note


def write_vault(
    records: list[PdfRecord],
    output_root: Path,
    *,
    copy_pdfs: bool = False,
    replace: bool = False,
    expected_paths: tuple[Path, ...] = (),
    missing_paths: tuple[Path, ...] = (),
) -> VaultRenderResult:
    pdf_output_dir = output_root / "PDFs"
    stale_removed = _replace_generated(output_root) if replace else _clear_sources(output_root)
    attachment_names = _copy_pdfs(records, pdf_output_dir) if copy_pdfs else {}
    result = _result(records, expected_paths, missing_paths, attachment_names, pdf_output_dir, stale_removed)

    _write(output_root / "Index.md", index(records))
    _write(output_root / "Source Manifest.md", manifest(records, expected_paths))
    _write(output_root / "Tool Index.md", tool_index(records))
    _write(output_root / "Command Cheat Index.md", command_index(records))
    _write(output_root / "Scripts And Snippets.md", scripts(records))
    _write(output_root / "Technique Index.md", technique_index(records))
    _write(output_root / "Study Roadmap.md", roadmap(records))
    _write(output_root / "Certification.md", certification(result, records))
    _write(output_root / "Cyber PDF Reference Policy.md", policy())
    _write_source_notes(records, output_root / "Sources", attachment_names)
    return result


def attachment_name(record: PdfRecord) -> str:
    return f"{slug(record.meta.path.stem)}-{record.meta.sha256[:8]}.pdf"


def _write_source_notes(
    records: list[PdfRecord],
    sources: Path,
    attachment_names: dict[str, str],
) -> None:
    duplicate_paths = _duplicate_paths(records)
    sources.mkdir(parents=True, exist_ok=True)
    for record in records:
        _write(
            sources / f"{source_filename(record)}.md",
            source_note(
                record,
                duplicate_paths.get(record.meta.sha256, []),
                attachment_names.get(record.meta.sha256),
            ),
        )


def _replace_generated(output_root: Path) -> int:
    _assert_safe_output_root(output_root)
    removed = 0
    if not output_root.exists():
        return removed
    for child in output_root.iterdir():
        if child.name in {"Sources", "PDFs"} and child.is_dir():
            shutil.rmtree(child)
            removed += 1
        elif child.is_file() and child.suffix.lower() in {".md", ".txt"}:
            child.unlink()
            removed += 1
    return removed


def _clear_sources(output_root: Path) -> int:
    sources = output_root / "Sources"
    if not sources.exists():
        return 0
    removed = 0
    for old in sources.glob("*.md"):
        old.unlink()
        removed += 1
    return removed


def _assert_safe_output_root(output_root: Path) -> None:
    expected_tail = ("Vault", "References", "CyberPDFs")
    if output_root.parts[-3:] != expected_tail:
        msg = f"refusing to replace unexpected CyberPDF output path: {output_root}"
        raise ValueError(msg)


def _copy_pdfs(records: list[PdfRecord], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    names: dict[str, str] = {}
    for record in records:
        name = attachment_name(record)
        shutil.copy2(record.meta.path, output_dir / name)
        names[record.meta.sha256] = name
    return names


def _result(
    records: list[PdfRecord],
    expected_paths: tuple[Path, ...],
    missing_paths: tuple[Path, ...],
    attachment_names: dict[str, str],
    pdf_output_dir: Path,
    stale_removed: int,
) -> VaultRenderResult:
    return VaultRenderResult(
        expected_sources=len(expected_paths) if expected_paths else len(records),
        found_sources=len(records),
        copied_pdfs=len(attachment_names),
        source_notes=len(records),
        needs_ocr=sum(1 for record in records if record.status == "needs-ocr"),
        stale_files_removed=stale_removed,
        missing_paths=missing_paths,
        hash_mismatches=tuple(_hash_mismatches(records, attachment_names, pdf_output_dir)),
    )


def _hash_mismatches(
    records: list[PdfRecord],
    attachment_names: dict[str, str],
    pdf_output_dir: Path,
) -> list[str]:
    mismatches: list[str] = []
    for record in records:
        if record.meta.sha256 not in attachment_names:
            continue
        copied = pdf_output_dir / attachment_names[record.meta.sha256]
        if copied.is_file() and _sha256(copied) != record.meta.sha256:
            mismatches.append(str(record.meta.path))
    return mismatches


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _duplicate_paths(records: list[PdfRecord]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for record in records:
        if record.status == "duplicate":
            grouped[record.meta.sha256].append(record.meta.path)
    return grouped


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
