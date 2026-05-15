from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

MIN_WORD_LENGTH = 3


def extract_path_words(urls: list[str]) -> list[str]:
    """Extract path segments and words from discovered URLs.

    Splits paths on `/`, `-`, `_`, `.` and filters to 3+ character alpha-only words.
    Deduplicates before returning.
    """
    words: set[str] = set()

    for url in urls:
        try:
            parsed = urlparse(url)
            path = parsed.path
        except ValueError:
            continue

        # Split on `/`, `-`, `_`, `.`
        parts = re.split(r'[/\-_.]', path)

        for part in parts:
            # Filter: MIN_WORD_LENGTH+ chars, alpha-only (no numbers, special chars)
            if len(part) >= MIN_WORD_LENGTH and part.isalpha():
                words.add(part.lower())

    return sorted(list(words))


def build_supplement(
    words: list[str],
    base_wordlist: Path,
    output_path: Path,
) -> Path:
    """Build a supplemental wordlist merged with the base wordlist.

    Reads the base wordlist, appends extracted words, deduplicates, and writes
    to output_path. Returns the path to the merged wordlist.
    """
    merged: set[str] = set()

    # Load base wordlist
    if base_wordlist.is_file():
        try:
            base_lines = base_wordlist.read_text(encoding="utf-8", errors="ignore")
            merged.update(line.strip().lower() for line in base_lines.split('\n') if line.strip())
        except (OSError, ValueError):
            pass

    # Add extracted words
    merged.update(word.lower() for word in words)

    # Write merged wordlist
    sorted_words = sorted(merged)
    output_path.write_text('\n'.join(sorted_words) + '\n', encoding="utf-8")

    return output_path
