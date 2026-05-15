from bbwebscan.menu_templates import SCAN_TEMPLATES, select_template
from bbwebscan.menu_types import ScanSettings


def test_scan_templates_defined() -> None:
    """Verify all 4 templates are defined and accessible."""
    assert len(SCAN_TEMPLATES) == 4
    for key in ("1", "2", "3", "4"):
        assert key in SCAN_TEMPLATES


def test_template_1_passive_recon() -> None:
    """Template 1: Passive Recon — safe mode, dry-run."""
    name, settings = SCAN_TEMPLATES["1"]
    assert "Passive" in name
    assert settings.mode == "safe"
    assert settings.dry_run is True


def test_template_2_full_web() -> None:
    """Template 2: Full Web — aggressive mode, run immediately."""
    name, settings = SCAN_TEMPLATES["2"]
    assert "Full" in name
    assert settings.mode == "aggressive"
    assert settings.dry_run is False


def test_template_3_api_recon() -> None:
    """Template 3: API Recon — aggressive + kiterunner, ffuf/feroxbuster disabled."""
    name, settings = SCAN_TEMPLATES["3"]
    assert "API" in name
    assert settings.mode == "aggressive"
    assert settings.api_discovery is True
    assert "ffuf" in settings.disable_tool
    assert "feroxbuster" in settings.disable_tool


def test_template_4_manual() -> None:
    """Template 4: Manual — blank slate defaults."""
    name, settings = SCAN_TEMPLATES["4"]
    assert "Manual" in name or "Custom" in name
    assert settings == ScanSettings()


def test_select_template_returns_first() -> None:
    """select_template('1') returns Template 1 settings."""
    _, expected = SCAN_TEMPLATES["1"]

    def mock_input(prompt: str) -> str:
        return "1"

    result = select_template(mock_input)
    assert result.mode == expected.mode
    assert result.dry_run == expected.dry_run


def test_select_template_invalid_choice() -> None:
    """select_template() with invalid choice returns blank ScanSettings."""

    def mock_input(prompt: str) -> str:
        return "9"

    result = select_template(mock_input)
    assert result == ScanSettings()


def test_select_template_empty_choice() -> None:
    """select_template() with empty choice returns blank ScanSettings."""

    def mock_input(prompt: str) -> str:
        return ""

    result = select_template(mock_input)
    assert result == ScanSettings()


def test_template_all_have_names() -> None:
    """Every template has a non-empty name."""
    for _key, (name, _) in SCAN_TEMPLATES.items():
        assert name
        assert len(name) > 0
