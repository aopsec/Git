"""v0.4.3 (Item 2): catches version bumps that forget to update CHANGELOG.md."""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _project_version() -> str:
    pyproject = PROJECT_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_changelog_lists_current_version() -> None:
    version = _project_version()
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    pattern = rf"^## \[?{re.escape(version)}\]?(\s|$)"
    assert re.search(pattern, changelog, flags=re.MULTILINE), (
        f"CHANGELOG.md is missing a header for version {version}. "
        "Add an entry before bumping pyproject."
    )


def test_changelog_lists_all_prior_versions() -> None:
    """Every version we have shipped should still have a CHANGELOG section."""
    expected_versions = (
        "0.0.1",
        "0.3.0",
        "0.4.0",
        "0.4.1",
        "0.4.2",
        "0.4.3",
        "0.4.4",
        "0.5.0",
        "0.5.1",
    )
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for version in expected_versions:
        pattern = rf"^## \[?{re.escape(version)}\]?(\s|$)"
        assert re.search(pattern, changelog, flags=re.MULTILINE), (
            f"CHANGELOG.md missing entry for {version}"
        )
