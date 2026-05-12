from __future__ import annotations

import argparse
from pathlib import Path

from tools.cyber_pdf_ref.extractor import build_records
from tools.cyber_pdf_ref.pdf_inputs import collect_pdf_inputs
from tools.cyber_pdf_ref.render import write_vault


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CyberPDF Obsidian references")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--pdf", action="append", default=[], type=Path)
    parser.add_argument("--pdf-list", action="append", default=[], type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--copy-pdfs", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # [REF-CYBERPDF-02] Support curated manifests in addition to broad discovery.
    inputs = collect_pdf_inputs(root=args.root, pdfs=args.pdf, pdf_lists=args.pdf_list)
    if inputs.missing_paths:
        for path in inputs.missing_paths:
            print(f"missing\t{path}")
        return 2

    records = build_records(list(inputs.existing_paths))
    output_root = args.repo / "Vault" / "References" / "CyberPDFs"
    if args.dry_run:
        print(f"requested={len(inputs.requested_paths)}")
        print(f"records={len(records)}")
        for record in records:
            print(
                f"{record.status}\tpages={record.meta.pages}\tchars={record.text_chars}\t"
                f"{record.meta.path}"
            )
        return 0
    result = write_vault(
        records,
        output_root,
        copy_pdfs=args.copy_pdfs,
        replace=args.replace,
        expected_paths=inputs.requested_paths,
        missing_paths=inputs.missing_paths,
    )
    print(
        f"wrote {result.source_notes} source notes and {result.copied_pdfs} PDFs "
        f"to {output_root}"
    )
    if result.needs_ocr or result.hash_mismatches:
        return 1
    return 0
