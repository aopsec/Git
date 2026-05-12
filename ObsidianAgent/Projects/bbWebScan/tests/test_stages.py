import shutil
import subprocess
from pathlib import Path

import pytest

from bbwebscan.models import AuthConfig, NormalizedTarget, RetryPolicy, RunArtifacts, RunConfig
from bbwebscan.stages import (
    amass_stage,
    discovery_stage,
    httpx_stage,
    katana_stage,
    kiterunner_stage,
    nuclei_stage,
    params_stage,
)


def _run_config(auth: AuthConfig | None = None) -> RunConfig:
    return RunConfig(
        program_name="test",
        seed_urls=[],
        allowed_hosts=["example.com"],
        denied_hosts=[],
        auth=auth or AuthConfig(),
        mode="safe",
        enabled_tools=[],
        wordlist=Path("words.txt"),
        threads=5,
        rate=10,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(),
        output_dir=Path("runs/test"),
        target_inputs=["https://app.example.com"],
        dry_run=True,
    )


def _artifacts(tmp_path: Path) -> RunArtifacts:
    return RunArtifacts(root=tmp_path, logs=tmp_path / "logs", artifacts=tmp_path / "artifacts")


def test_httpx_parse_skips_malformed_and_empty(fixtures_dir: Path) -> None:
    findings, urls = httpx_stage.parse_results(fixtures_dir / "httpx.jsonl")
    assert urls == [
        "https://app.example.com",
        "https://api.example.com",
        "https://www.example.com",
    ]
    assert len(findings) == 3
    assert all(f.kind == "inventory" for f in findings)
    assert "status=200" in findings[0].title


def test_httpx_parse_missing_file_returns_empty(tmp_path: Path) -> None:
    findings, urls = httpx_stage.parse_results(tmp_path / "missing.jsonl")
    assert findings == []
    assert urls == []


def test_katana_parse_handles_endpoint_or_url(fixtures_dir: Path) -> None:
    findings, urls = katana_stage.parse_results(fixtures_dir / "katana.jsonl")
    assert "https://app.example.com/login" in urls
    assert "https://app.example.com/about" in urls
    assert len(findings) == 1
    assert "Discovered" in findings[0].title


def test_nuclei_parse_extracts_severity(fixtures_dir: Path) -> None:
    findings, _ = nuclei_stage.parse_results(fixtures_dir / "nuclei.jsonl")
    severities = {f.severity for f in findings}
    assert "high" in severities
    assert "medium" in severities
    # Robust to malformed lines and ones missing 'info'
    assert len(findings) == 3


def test_discovery_parse_per_artifact_finding(fixtures_dir: Path) -> None:
    findings, urls = discovery_stage.parse_results(
        [fixtures_dir / "ffuf.json", fixtures_dir / "feroxbuster.json"]
    )
    # ffuf has 3 URLs, feroxbuster has 2 valid → both artifacts produce findings
    assert len(findings) == 2
    assert findings[0].evidence.endswith("ffuf.json")
    assert findings[1].evidence.endswith("feroxbuster.json")
    assert "https://app.example.com/admin" in urls
    assert "https://app.example.com/api" in urls


def test_discovery_parse_missing_artifact_yields_no_finding(tmp_path: Path) -> None:
    findings, urls = discovery_stage.parse_results([tmp_path / "missing.json"])
    assert findings == []
    assert urls == []


def test_discovery_parse_empty_artifact_yields_no_finding(tmp_path: Path) -> None:
    """Bug from bbscan: cumulative URL list polluted later artifacts. Verify fix."""
    empty = tmp_path / "empty.json"
    empty.write_text('{"results": []}', encoding="utf-8")
    populated = tmp_path / "good.json"
    populated.write_text(
        '{"results": [{"url": "https://app.example.com/x"}]}', encoding="utf-8"
    )
    findings, urls = discovery_stage.parse_results([populated, empty])
    assert len(findings) == 1
    assert findings[0].evidence.endswith("good.json")
    assert urls == ["https://app.example.com/x"]


def test_dirsearch_command_uses_v043_output_and_raw_flags(tmp_path: Path) -> None:
    raw_request = tmp_path / "request.txt"
    config = _run_config(auth=AuthConfig(raw_request=raw_request))
    config.enabled_tools.append("dirsearch")
    plans = discovery_stage.build_plans(config, _artifacts(tmp_path), ["https://app.example.com"])
    command = plans[0].command

    assert command[command.index("-O") + 1] == "json"
    assert command[command.index("-o") + 1].endswith("dirsearch_1.json")
    assert f"--raw={raw_request}" in command
    assert "--format" not in command
    assert "--output" not in command
    assert "--raw-request" not in command


def test_params_parse_arjun_dict(fixtures_dir: Path) -> None:
    findings, _ = params_stage.parse_results([fixtures_dir / "arjun.json"])
    assert len(findings) == 1
    title = findings[0].title
    assert "csrf_token" in title or "limit" in title or "page" in title


def test_arjun_command_uses_newline_headers(tmp_path: Path) -> None:
    auth = AuthConfig(
        headers={"X-Token": "secret", "Accept": "application/json"},
        cookies={"sid": "1"},
    )
    plans = params_stage.build_plans(
        _run_config(auth=auth),
        _artifacts(tmp_path),
        ["https://app.example.com/login"],
    )
    command = plans[0].command

    assert "-H" not in command
    assert command[command.index("--headers") + 1] == (
        "Accept: application/json\nX-Token: secret\nCookie: sid=1"
    )


def test_dirsearch_help_advertises_v043_flags() -> None:
    """Drift guard: if dirsearch ever drops -O/-o/--raw, this test fails locally
    so the operator knows to update bbwebscan/stages/discovery_stage.py before
    a real run silently produces wrong commands."""
    if shutil.which("dirsearch") is None:
        pytest.skip("dirsearch not installed; drift guard skipped")
    completed = subprocess.run(
        ["dirsearch", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    help_text = (completed.stdout or "") + (completed.stderr or "")
    missing: list[str] = []
    if "-O" not in help_text:
        missing.append("-O (output format)")
    if "-o" not in help_text:
        missing.append("-o (output file)")
    if "--raw" not in help_text:
        missing.append("--raw (raw request)")
    assert not missing, (
        f"dirsearch --help no longer advertises: {', '.join(missing)}. "
        "discovery_stage._tool_command needs updating."
    )


# ---- v0.5.0 amass ----

def _amass_target(host: str = "api.example.com") -> list[NormalizedTarget]:
    return [NormalizedTarget(raw=host, host=host, seed_url=f"https://{host}")]


def test_amass_command_passive_mode(tmp_path: Path) -> None:
    """v0.5.0 Item 3: passive mode uses observed amass v4.2.0 flags;
    -active is absent; -nocolor and -oA prefix produced."""
    config = _run_config()
    plans = amass_stage.build_plan(config, _artifacts(tmp_path), _amass_target())
    assert len(plans) == 1
    cmd = plans[0].command
    assert cmd[0:2] == ["amass", "enum"]
    assert "-d" in cmd
    assert cmd[cmd.index("-d") + 1] == "example.com"  # registrable root
    assert "-oA" in cmd
    assert cmd[cmd.index("-oA") + 1].endswith("amass_1")
    assert "-nocolor" in cmd
    assert "-active" not in cmd  # passive default


def test_amass_command_active_includes_flag(tmp_path: Path) -> None:
    config = _run_config().model_copy(update={"amass_mode": "active"})
    plans = amass_stage.build_plan(config, _artifacts(tmp_path), _amass_target())
    assert "-active" in plans[0].command


@pytest.mark.parametrize(
    ("host", "expected_root"),
    [
        ("api.example.co.uk", "example.co.uk"),
        ("shop.example.com.br", "example.com.br"),
        ("api.example.com", "example.com"),
        ("app.github.io", "app.github.io"),
        ("portal.pages.dev", "portal.pages.dev"),
        ("prod.azurewebsites.net", "prod.azurewebsites.net"),
    ],
)
def test_amass_command_uses_psl_safe_root(
    tmp_path: Path,
    host: str,
    expected_root: str,
) -> None:
    plans = amass_stage.build_plan(_run_config(), _artifacts(tmp_path), _amass_target(host))
    command = plans[0].command
    assert command[command.index("-d") + 1] == expected_root


def test_amass_command_never_uses_public_or_shared_suffix_as_root(tmp_path: Path) -> None:
    hosts = [
        "api.example.co.uk",
        "shop.example.com.br",
        "app.github.io",
        "portal.pages.dev",
        "prod.azurewebsites.net",
    ]
    plans = amass_stage.build_plan(
        _run_config(),
        _artifacts(tmp_path),
        [target for host in hosts for target in _amass_target(host)],
    )
    domains = [plan.command[plan.command.index("-d") + 1] for plan in plans]
    assert not {"co.uk", "com.br", "github.io", "pages.dev", "azurewebsites.net"} & set(
        domains
    )


def test_amass_parse_extracts_fqdns_from_textfile(fixtures_dir: Path) -> None:
    """v0.5.0 Item 3: parse_results reads <prefix>.txt one FQDN per line."""
    findings, fqdns = amass_stage.parse_results(fixtures_dir / "amass.txt")
    assert "api.example.com" in fqdns
    assert "www.example.com" in fqdns
    assert "out-of-scope.evil.test" in fqdns
    # Findings: one summary entry, kind=subdomain
    assert len(findings) == 1
    assert findings[0].kind == "subdomain"
    assert findings[0].severity == "info"
    assert "Discovered 5 subdomains" in findings[0].title


def test_amass_parse_missing_file_returns_empty(tmp_path: Path) -> None:
    findings, fqdns = amass_stage.parse_results(tmp_path / "nope.txt")
    assert findings == []
    assert fqdns == []


# ---- v0.5.0 kiterunner ----

def test_kiterunner_command_includes_wordlist_and_url(tmp_path: Path) -> None:
    """v0.5.0 Item 4: command derived from observed `kiterunner scan -h`.
    `-o json` is a global flag (must precede `scan`)."""
    config = _run_config()
    plans = kiterunner_stage.build_plans(
        config,
        _artifacts(tmp_path),
        ["https://app.example.com"],
    )
    assert len(plans) == 1
    cmd = plans[0].command
    assert cmd[0] == "kiterunner"
    # -o json must come before `scan` subcommand (cobra-style global flag)
    assert cmd[cmd.index("-o") + 1] == "json"
    assert cmd.index("-o") < cmd.index("scan")
    # url passed positional after `scan`
    assert "https://app.example.com" in cmd
    assert "-w" in cmd  # wordlist flag


def test_kiterunner_parse_classifies_status_codes(fixtures_dir: Path) -> None:
    """v0.5.0 Item 4: 200/3xx → info; 401/403 → low; everything else dropped."""
    findings, routes = kiterunner_stage.parse_results([fixtures_dir / "kiterunner.jsonl"])
    by_target = {f.target: f for f in findings}
    assert by_target["https://app.example.com/api/v1/users"].severity == "info"
    assert by_target["https://app.example.com/api/admin"].severity == "low"
    assert by_target["https://app.example.com/internal"].severity == "low"
    assert "https://app.example.com/health" in routes
    # Malformed line is silently skipped (no exception)
    assert len(findings) == 4


def test_kiterunner_parse_missing_artifact_returns_empty(tmp_path: Path) -> None:
    findings, routes = kiterunner_stage.parse_results([tmp_path / "missing.jsonl"])
    assert findings == []
    assert routes == []


# ---- Phase 1 Filtering & Capping Tests ----

def test_discovery_parse_filters_by_status_code(tmp_path: Path) -> None:
    """Test status code filtering in discovery_stage.parse_results()."""
    artifact = tmp_path / "filtered.json"
    artifact.write_text(
        '{"results": ['
        '{"url": "https://app.example.com/200", "status": 200}, '
        '{"url": "https://app.example.com/301", "status": 301}, '
        '{"url": "https://app.example.com/403", "status": 403}, '
        '{"url": "https://app.example.com/404", "status": 404} '
        ']}',
        encoding="utf-8",
    )

    # Create config with status filter for 2xx/3xx only
    config = _run_config()
    config.discovery_status_filter = ["200", "301", "302", "307", "308"]

    findings, urls = discovery_stage.parse_results([artifact], config)

    # Should only include 200 and 301, not 403 or 404
    assert "https://app.example.com/200" in urls
    assert "https://app.example.com/301" in urls
    assert "https://app.example.com/403" not in urls
    assert "https://app.example.com/404" not in urls
    assert len(urls) == 2
    assert len(findings) == 1
    assert findings[0].title == "Discovered 2 web content candidates"


def test_discovery_parse_without_config_no_filter(tmp_path: Path) -> None:
    """Test that without config, all URLs are included (backward compat)."""
    artifact = tmp_path / "unfiltered.json"
    artifact.write_text(
        '{"results": ['
        '{"url": "https://app.example.com/200", "status": 200}, '
        '{"url": "https://app.example.com/403", "status": 403}, '
        '{"url": "https://app.example.com/404", "status": 404} '
        ']}',
        encoding="utf-8",
    )

    # Parse without config (old behavior)
    findings, urls = discovery_stage.parse_results([artifact], config=None)

    # All URLs should be included
    assert len(urls) == 3
    assert all(
        url in urls
        for url in [
            "https://app.example.com/200",
            "https://app.example.com/403",
            "https://app.example.com/404",
        ]
    )


def test_nuclei_build_plan_caps_targets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that nuclei_stage.build_plan respects nuclei_max_targets cap."""
    artifacts = RunArtifacts(
        root=tmp_path,
        logs=tmp_path / "logs",
        artifacts=tmp_path / "artifacts",
    )
    artifacts.artifacts.mkdir(parents=True, exist_ok=True)

    config = _run_config()
    config.nuclei_max_targets = 5

    # Create 10 target URLs
    urls = [f"https://app.example.com/target{i}" for i in range(10)]

    nuclei_stage.build_plan(config, artifacts, urls)

    # Read the written nuclei_targets.txt
    targets_file = artifacts.artifacts / "nuclei_targets.txt"
    assert targets_file.exists()

    written_urls = targets_file.read_text(encoding="utf-8").strip().split("\n")

    # Should only have 5 URLs (capped)
    assert len(written_urls) == 5
    # Should be the first 5 in order
    assert written_urls == urls[:5]
    
    # Should print warning to stderr
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()
    assert "nuclei_max_targets" in captured.err or "max_targets" in captured.err


def test_nuclei_build_plan_no_cap_if_under_limit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that nuclei_stage doesn't warn if targets < max_targets."""
    artifacts = RunArtifacts(
        root=tmp_path,
        logs=tmp_path / "logs",
        artifacts=tmp_path / "artifacts",
    )
    artifacts.artifacts.mkdir(parents=True, exist_ok=True)

    config = _run_config()
    config.nuclei_max_targets = 100

    # Create only 5 target URLs (under cap)
    urls = [f"https://app.example.com/target{i}" for i in range(5)]

    nuclei_stage.build_plan(config, artifacts, urls)

    # Read the written nuclei_targets.txt
    targets_file = artifacts.artifacts / "nuclei_targets.txt"
    written_urls = targets_file.read_text(encoding="utf-8").strip().split("\n")

    # Should have all 5 URLs
    assert len(written_urls) == 5
    
    # Should not print warning
    captured = capsys.readouterr()
    assert "warning" not in captured.err.lower() or "nuclei" not in captured.err.lower()
