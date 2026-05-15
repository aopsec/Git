from bbwebscan.menu_types import InputFunc, ScanSettings

SCAN_TEMPLATES: dict[str, tuple[str, ScanSettings]] = {
    "1": (
        "Passive Recon",
        ScanSettings(
            mode="safe",
            targets=[],
            dry_run=True,
        ),
    ),
    "2": (
        "Full Web Scan",
        ScanSettings(
            mode="aggressive",
            targets=[],
            dry_run=False,
        ),
    ),
    "3": (
        "API Recon",
        ScanSettings(
            mode="aggressive",
            targets=[],
            api_discovery=True,
            dry_run=False,
            disable_tool=["ffuf", "feroxbuster"],
        ),
    ),
    "4": (
        "Manual (Custom)",
        ScanSettings(),
    ),
}


def select_template(input_func: InputFunc) -> ScanSettings:
    """Present scan templates and return the selected preset as ScanSettings.

    User picks 1-4 to select a template, which pre-fills scan settings.
    """
    panel_text = "\n".join([
        "Scan Templates:",
        *[f"  {key}. {name}" for key, (name, _) in SCAN_TEMPLATES.items()],
    ])

    choice_val = input_func(f"{panel_text}\nSelect template [1-4]: ").strip()

    if choice_val not in SCAN_TEMPLATES:
        return ScanSettings()

    _, template_settings = SCAN_TEMPLATES[choice_val]
    return template_settings
