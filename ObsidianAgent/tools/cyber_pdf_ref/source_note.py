from __future__ import annotations

from pathlib import Path

from tools.cyber_pdf_ref.models import ExtractedItem, PdfRecord


def source_note(record: PdfRecord, duplicates: list[Path], attachment_name: str | None) -> str:
    lines = [
        f"# {record.meta.title}",
        "",
        "## Metadata",
        f"- Status: `{record.status}`",
        f"- Reason: {record.reason}",
        f"- Source path: `{record.meta.path}`",
        f"- SHA256: `{record.meta.sha256}`",
        f"- Pages: `{record.meta.pages}`",
        f"- Text characters: `{record.text_chars}`",
        f"- Author: `{record.meta.author or 'n/a'}`",
        f"- Copied PDF: {_pdf_link(attachment_name)}",
        "",
        "## Duplicate Paths",
    ]
    if duplicates:
        lines.extend(f"- `{path}`" for path in duplicates)
    else:
        lines.append("- none")
    lines.extend(["", "## Tools"])
    lines.extend(_item_lines(record.tools))
    lines.extend(["", "## Commands"])
    lines.extend(_item_lines(record.commands, code=True))
    lines.extend(["", "## Code And Script Lines"])
    lines.extend(_item_lines(record.scripts, code=True))
    lines.extend(["", "## URLs"])
    lines.extend(_item_lines(record.urls))
    lines.extend(["", "## Technique Signals"])
    lines.extend(_item_lines(record.techniques))
    lines.extend(["", "## Extracted Operational Notes"])
    lines.extend(_item_lines(record.snippets, fallback="No cyber snippets extracted."))
    return "\n".join(lines) + "\n"


def _pdf_link(attachment_name: str | None) -> str:
    if attachment_name is None:
        return "`not copied`"
    return f"[[PDFs/{attachment_name}|Open copied PDF]]"


def _item_lines(
    items: list[ExtractedItem],
    *,
    code: bool = False,
    fallback: str = "none",
) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    if code:
        return [f"- p. {item.page}: `{item.value}`" for item in items]
    return [f"- p. {item.page}: {item.value}" for item in items]
