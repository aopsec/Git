"""[v0.5.6] naabu port-discovery stage — build_plan + parse_results."""
from __future__ import annotations

from pathlib import Path

import pytest

from bbwebscan.models import AuthConfig, NormalizedTarget, RetryPolicy, RunArtifacts, RunConfig
from bbwebscan.stages import naabu_stage


def _config(**overrides: object) -> RunConfig:
    base = RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["naabu"],
        wordlist=Path("words.txt"),
        threads=5,
        rate=10,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(),
        output_dir=Path("runs/test"),
        target_inputs=["https://app.example.com"],
        dry_run=True,
        port_scan=True,
    )
    return base.model_copy(update=overrides)


def _artifacts(tmp_path: Path) -> RunArtifacts:
    return RunArtifacts(root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts")


def _targets(*hosts: str) -> list[NormalizedTarget]:
    return [NormalizedTarget(raw=host, host=host, seed_url=f"https://{host}") for host in hosts]


def test_build_plan_top_100_uses_top_ports_flag(tmp_path: Path) -> None:
    plans = naabu_stage.build_plan(
        _config(), _artifacts(tmp_path), _targets("app.example.com"),
    )
    assert len(plans) == 1
    cmd = plans[0].command
    assert cmd[0] == "naabu"
    assert cmd[cmd.index("-top-ports") + 1] == "100"
    assert "-json" in cmd
    assert "-silent" in cmd
    assert cmd[cmd.index("-host") + 1] == "app.example.com"
    assert cmd[cmd.index("-rate") + 1] == "1000"


def test_build_plan_top_1000_uses_top_ports_flag(tmp_path: Path) -> None:
    plans = naabu_stage.build_plan(
        _config(port_scan_mode="top-1000"),
        _artifacts(tmp_path),
        _targets("app.example.com"),
    )
    cmd = plans[0].command
    assert cmd[cmd.index("-top-ports") + 1] == "1000"


def test_build_plan_full_uses_p_dash(tmp_path: Path) -> None:
    plans = naabu_stage.build_plan(
        _config(port_scan_mode="full"),
        _artifacts(tmp_path),
        _targets("app.example.com"),
    )
    cmd = plans[0].command
    assert "-top-ports" not in cmd
    assert cmd[cmd.index("-p") + 1] == "-"


def test_build_plan_dedupes_and_sorts_hosts(tmp_path: Path) -> None:
    plans = naabu_stage.build_plan(
        _config(),
        _artifacts(tmp_path),
        _targets("api.example.com", "app.example.com", "api.example.com"),
    )
    cmd = plans[0].command
    hosts = cmd[cmd.index("-host") + 1]
    assert hosts == "api.example.com,app.example.com"


def test_build_plan_empty_targets_returns_nothing(tmp_path: Path) -> None:
    assert naabu_stage.build_plan(_config(), _artifacts(tmp_path), []) == []


def test_build_plan_rate_from_config(tmp_path: Path) -> None:
    plans = naabu_stage.build_plan(
        _config(port_scan_rate=500),
        _artifacts(tmp_path),
        _targets("app.example.com"),
    )
    cmd = plans[0].command
    assert cmd[cmd.index("-rate") + 1] == "500"


def test_parse_results_extracts_host_ports(fixtures_dir: Path) -> None:
    findings, host_ports = naabu_stage.parse_results(fixtures_dir / "naabu.jsonl")
    assert "app.example.com:80" in host_ports
    assert "app.example.com:443" in host_ports
    assert "app.example.com:8080" in host_ports
    assert "api.example.com:8443" in host_ports
    assert "api.example.com:443" in host_ports
    assert len(host_ports) == 5
    # Single summary finding, kind=open-port
    assert len(findings) == 1
    assert findings[0].kind == "open-port"
    assert findings[0].severity == "info"
    assert "Discovered 5 open ports" in findings[0].title


def test_parse_results_skips_malformed_lines(fixtures_dir: Path) -> None:
    _, host_ports = naabu_stage.parse_results(fixtures_dir / "naabu.jsonl")
    # The "port":"not-an-int" record must be skipped, leaving only the 5 valid ones.
    assert all(":" in hp and hp.rsplit(":", 1)[1].isdigit() for hp in host_ports)


def test_parse_results_missing_file_returns_empty(tmp_path: Path) -> None:
    findings, host_ports = naabu_stage.parse_results(tmp_path / "missing.jsonl")
    assert findings == []
    assert host_ports == []


@pytest.mark.parametrize(
    "mode",
    ["top-100", "top-1000", "full"],
)
def test_build_plan_always_includes_silent_and_json(tmp_path: Path, mode: str) -> None:
    plans = naabu_stage.build_plan(
        _config(port_scan_mode=mode),
        _artifacts(tmp_path),
        _targets("app.example.com"),
    )
    cmd = plans[0].command
    assert "-silent" in cmd
    assert "-json" in cmd
    assert cmd[cmd.index("-o") + 1].endswith("naabu.jsonl")
