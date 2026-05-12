from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from tools.cyber_pdf_ref.extractor import slug
from tools.cyber_pdf_ref.models import ExtractedItem, PdfRecord, VaultRenderResult

TOP_LEVEL_FILES = (
    "Index.md",
    "Source Manifest.md",
    "Tool Index.md",
    "Command Cheat Index.md",
    "Scripts And Snippets.md",
    "Technique Index.md",
    "Study Roadmap.md",
    "Certification.md",
    "Cyber PDF Reference Policy.md",
)


def source_filename(record: PdfRecord) -> str:
    return slug(f"{record.meta.path.stem}-{record.meta.sha256[:8]}")


def index(records: list[PdfRecord]) -> str:
    counts = Counter(record.status for record in records)
    lines = [
        "# Cyber PDF Reference Index",
        "",
        "Machine-generated reference vault. Use this material only for cyber/security tasks.",
        "",
        "## Counts",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(counts.items()))
    lines.extend(["", "## Active Sources"])
    for record in _active(records):
        lines.append(f"- [[{source_filename(record)}]] - `{record.status}` - {record.meta.title}")
    lines.extend(["", "## Core Indexes"])
    lines.extend(f"- [[{Path(name).stem}]]" for name in TOP_LEVEL_FILES if name != "Index.md")
    return "\n".join(lines) + "\n"


def manifest(records: list[PdfRecord], expected_paths: tuple[Path, ...]) -> str:
    lines = ["# Source Manifest", "", "| Status | Pages | SHA256 | Path | Reason |", "|---|---:|---|---|---|"]
    expected = {str(path): path for path in expected_paths}
    for record in records:
        expected.pop(str(record.meta.path), None)
        lines.append(
            f"| `{record.status}` | {record.meta.pages} | `{record.meta.sha256[:12]}` | "
            f"`{record.meta.path}` | {record.reason} |"
        )
    for path in expected.values():
        lines.append(f"| `missing` | 0 | `n/a` | `{path}` | listed source not found |")
    return "\n".join(lines) + "\n"


def tool_index(records: list[PdfRecord]) -> str:
    refs: dict[str, list[tuple[PdfRecord, int]]] = defaultdict(list)
    for record in _active(records):
        for tool in record.tools:
            refs[tool.value].append((record, tool.page))
    lines = ["# Tool Index", ""]
    for tool_name in sorted(refs):
        lines.append(f"## {tool_name}")
        lines.extend(
            f"- [[{source_filename(record)}]] - p. {page}"
            for record, page in refs[tool_name]
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def command_index(records: list[PdfRecord]) -> str:
    return _item_index("# Command Cheat Index", records, "commands", code=True)


def scripts(records: list[PdfRecord]) -> str:
    lines = ["# Scripts And Snippets", ""]
    for record in _active(records):
        lines.append(f"## [[{source_filename(record)}]]")
        lines.extend(_item_lines(record.scripts, code=True))
        lines.extend(_item_lines(record.snippets))
        lines.append("")
    return "\n".join(lines) + "\n"


def technique_index(records: list[PdfRecord]) -> str:
    return _item_index("# Technique Index", records, "techniques", code=False)


def roadmap(records: list[PdfRecord]) -> str:
    tools = sorted({tool.value for record in _active(records) for tool in record.tools})
    lines = [
        "# Study Roadmap",
        "",
        "1. Python, Bash, Go, Linux, HTTP, and networking fundamentals.",
        "2. Bug bounty recon, content discovery, fuzzing, and parameter discovery.",
        "3. Web and API testing: OWASP, GraphQL, auth, SSRF, XSS, SQLi, IDOR, JWT.",
        "4. Exploitation workflow: validate findings, reduce false positives, report clearly.",
        "5. Automation: turn repeated commands into scoped scripts with logs and dry-runs.",
        "",
        "## Tools To Practice",
    ]
    lines.extend(f"- `{tool}`" for tool in tools)
    return "\n".join(lines) + "\n"


def certification(result: VaultRenderResult, records: list[PdfRecord]) -> str:
    lines = [
        "# Certification",
        "",
        "## Result",
        f"- objective_complete=`{_completion_status(result)}`",
        f"- expected_sources=`{result.expected_sources}`",
        f"- found_sources=`{result.found_sources}`",
        f"- copied_pdfs=`{result.copied_pdfs}`",
        f"- source_notes=`{result.source_notes}`",
        f"- missing_sources=`{len(result.missing_paths)}`",
        f"- needs_ocr=`{result.needs_ocr}`",
        f"- hash_mismatches=`{len(result.hash_mismatches)}`",
        f"- stale_files_removed=`{result.stale_files_removed}`",
        "",
        "## Source Statuses",
    ]
    lines.extend(f"- `{record.status}` - {record.meta.path.name}" for record in records)
    lines.extend(["", "## Verification Commands"])
    lines.append("- `python3 -m py_compile tools/extract_cyber_pdf_reference.py tools/cyber_pdf_ref/*.py`")
    lines.append("- `python3 $HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py --check --repo .`")
    return "\n".join(lines) + "\n"


def _completion_status(result: VaultRenderResult) -> str:
    complete = (
        result.expected_sources == result.found_sources
        and result.expected_sources == result.copied_pdfs
        and result.expected_sources == result.source_notes
        and len(result.missing_paths) == 0
        and result.needs_ocr == 0
        and len(result.hash_mismatches) == 0
    )
    return "100%" if complete else "blocked"


def policy() -> str:
    return (
        "# Cyber PDF Reference Policy\n\n"
        "Use this reference set only for cyber/security work: pentest, bug bounty, "
        "Linux hardening, defensive monitoring, infrastructure security, and related "
        "automation. Do not use these PDFs as general-purpose answer context.\n"
    )


def _item_index(
    title: str,
    records: list[PdfRecord],
    attribute: Literal["commands", "techniques"],
    *,
    code: bool,
) -> str:
    lines = [title, ""]
    for record in _active(records):
        items = _record_items(record, attribute)
        if not items:
            continue
        lines.append(f"## [[{source_filename(record)}]]")
        lines.extend(_item_lines(items, code=code))
        lines.append("")
    return "\n".join(lines) + "\n"


def _item_lines(items: list[ExtractedItem], *, code: bool = False) -> list[str]:
    if code:
        return [f"- p. {item.page}: `{item.value}`" for item in items]
    return [f"- p. {item.page}: {item.value}" for item in items]


def _record_items(
    record: PdfRecord,
    attribute: Literal["commands", "techniques"],
) -> list[ExtractedItem]:
    if attribute == "commands":
        return record.commands
    return record.techniques


def _active(records: list[PdfRecord]) -> list[PdfRecord]:
    return [record for record in records if record.status in {"cyber-active", "cyber-adjacent"}]
