from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.cyber_pdf_ref import extractor
from tools.cyber_pdf_ref.models import ExtractedItem, PdfMeta, PdfRecord
from tools.cyber_pdf_ref.pdf_inputs import collect_pdf_inputs, read_pdf_list
from tools.cyber_pdf_ref.render import write_vault


def test_read_pdf_list_skips_comments_and_blanks(tmp_path: Path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    source_list = tmp_path / "sources.txt"
    source_list.write_text(f"# comment\n\n{first}\n  {second}  \n", encoding="utf-8")

    assert read_pdf_list(source_list) == [first, second]


def test_collect_pdf_inputs_reports_missing_files(tmp_path: Path) -> None:
    present = tmp_path / "present.pdf"
    missing = tmp_path / "missing.pdf"
    present.write_bytes(b"pdf")

    inputs = collect_pdf_inputs(root=None, pdfs=[present, missing], pdf_lists=[])

    assert inputs.existing_paths == (present,)
    assert inputs.missing_paths == (missing,)


def test_encrypted_copyable_pdf_is_extracted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "Black-Hat-Bash.pdf"
    pdf.write_bytes(b"fake")

    def fake_meta(path: Path) -> PdfMeta:
        return PdfMeta(
            path=path,
            sha256="a" * 64,
            size_bytes=4,
            title="Black Hat Bash",
            author="tester",
            pages=2,
            encrypted=True,
            javascript=False,
        )

    text = (
        "pentest bug bounty OWASP nmap exploit vulnerability recon XSS SSRF SQLi\n"
        "nmap -sV target.example\n"
        "\f"
        "GraphQL API JWT fuzzing vulnerability payload scan bypass enumeration\n"
    )
    monkeypatch.setattr(extractor, "_pdf_meta", fake_meta)
    monkeypatch.setattr(extractor, "_pdf_text", lambda _path: text)

    record = extractor.build_records([pdf])[0]

    assert record.status == "cyber-active"
    assert record.text_chars == len(text)
    assert any(item.value.startswith("nmap -sV") for item in record.commands)


def test_write_vault_replaces_stale_content_and_copies_pdf(tmp_path: Path) -> None:
    source_pdf = tmp_path / "source.pdf"
    source_pdf.write_bytes(b"minimal pdf bytes")
    digest = hashlib.sha256(source_pdf.read_bytes()).hexdigest()
    output_root = tmp_path / "Vault" / "References" / "CyberPDFs"
    (output_root / "Sources").mkdir(parents=True)
    (output_root / "Sources" / "stale.md").write_text("old", encoding="utf-8")
    (output_root / "Old.md").write_text("old", encoding="utf-8")

    record = PdfRecord(
        meta=PdfMeta(
            path=source_pdf,
            sha256=digest,
            size_bytes=source_pdf.stat().st_size,
            title="Test Book",
            author="tester",
            pages=1,
            encrypted=False,
            javascript=False,
        ),
        status="cyber-active",
        reason="test",
        canonical_sha=digest,
        text_chars=200,
        tools=[ExtractedItem("nmap", 1)],
        commands=[ExtractedItem("nmap -sV target.example", 1)],
    )

    result = write_vault(
        [record],
        output_root,
        copy_pdfs=True,
        replace=True,
        expected_paths=(source_pdf,),
    )

    copied = list((output_root / "PDFs").glob("*.pdf"))
    source_notes = list((output_root / "Sources").glob("*.md"))
    note_text = source_notes[0].read_text(encoding="utf-8")

    assert result.expected_sources == 1
    assert result.copied_pdfs == 1
    assert result.source_notes == 1
    assert result.hash_mismatches == ()
    assert len(copied) == 1
    assert "stale" not in note_text
    assert "[[PDFs/" in note_text
    assert not (output_root / "Old.md").exists()
