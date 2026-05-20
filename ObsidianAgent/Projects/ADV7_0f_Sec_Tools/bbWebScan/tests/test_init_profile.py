from pathlib import Path

import pytest
import yaml

from bbwebscan.init_profile import scaffold_profile
from bbwebscan.models import ProgramProfile


def test_scaffold_profile_writes_round_trippable_yaml(tmp_path: Path) -> None:
    out = tmp_path / "profiles" / "demo.yaml"
    written = scaffold_profile(
        "demo",
        ["app.example.com", "https://api.example.com"],
        out,
    )
    assert written == out
    assert out.is_file()
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    profile = ProgramProfile.model_validate(payload)
    assert profile.program_name == "demo"
    assert profile.allowed_hosts == ["api.example.com", "app.example.com"]
    assert profile.seed_urls == ["https://app.example.com", "https://api.example.com"]


def test_scaffold_profile_includes_guidance_hint(tmp_path: Path) -> None:
    """v0.4.2 (FIX-BBW-I): the YAML carries a comment block hinting at how to
    enable aggressive recon, so users don't get stuck with the safe-mode defaults."""
    out = tmp_path / "demo.yaml"
    scaffold_profile("demo", ["app.example.com"], out)
    body = out.read_text(encoding="utf-8")
    assert "# tip:" in body
    assert "enabled_tools: [ffuf, feroxbuster, arjun, nuclei]" in body
    assert "--mode aggressive --ack-authorized" in body
    # Comments must not break YAML parsing — file still loads to a valid profile.
    profile = ProgramProfile.model_validate(yaml.safe_load(body))
    assert profile.program_name == "demo"


def test_scaffold_profile_refuses_overwrite_without_force(tmp_path: Path) -> None:
    out = tmp_path / "demo.yaml"
    out.write_text("placeholder", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        scaffold_profile("demo", ["app.example.com"], out)


def test_scaffold_profile_force_overwrites(tmp_path: Path) -> None:
    out = tmp_path / "demo.yaml"
    out.write_text("placeholder", encoding="utf-8")
    scaffold_profile("demo", ["app.example.com"], out, force=True)
    assert "placeholder" not in out.read_text(encoding="utf-8")


def test_scaffold_profile_requires_target(tmp_path: Path) -> None:
    out = tmp_path / "demo.yaml"
    with pytest.raises(ValueError, match="at least one"):
        scaffold_profile("demo", [], out)


def test_scaffold_profile_rejects_public_suffix_target(tmp_path: Path) -> None:
    """normalize_target raises on bare TLDs; init must surface the same refusal."""
    out = tmp_path / "demo.yaml"
    with pytest.raises(ValueError, match="public-suffix"):
        scaffold_profile("demo", ["com"], out)
