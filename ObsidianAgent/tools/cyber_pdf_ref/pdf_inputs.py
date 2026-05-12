from __future__ import annotations

from pathlib import Path

from tools.cyber_pdf_ref.extractor import discover_pdfs
from tools.cyber_pdf_ref.models import PdfInputSet


def collect_pdf_inputs(
    *,
    root: Path | None,
    pdfs: list[Path],
    pdf_lists: list[Path],
) -> PdfInputSet:
    requested = _unique_paths([*_paths_from_lists(pdf_lists), *pdfs])
    if root is not None:
        requested.extend(discover_pdfs(root.expanduser()))
    if not requested:
        requested = discover_pdfs(Path.home())

    requested = _unique_paths(requested)
    existing = tuple(path for path in requested if path.is_file())
    missing = tuple(path for path in requested if not path.is_file())
    return PdfInputSet(
        requested_paths=tuple(requested),
        existing_paths=existing,
        missing_paths=missing,
    )


def read_pdf_list(path: Path) -> list[Path]:
    paths: list[Path] = []
    for line in path.expanduser().read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        paths.append(Path(cleaned).expanduser())
    return paths


def _paths_from_lists(paths: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    for path in paths:
        discovered.extend(read_pdf_list(path))
    return discovered


def _unique_paths(paths: list[Path]) -> list[Path]:
    unique: dict[str, Path] = {}
    for path in paths:
        expanded = path.expanduser()
        unique.setdefault(str(expanded), expanded)
    return list(unique.values())
