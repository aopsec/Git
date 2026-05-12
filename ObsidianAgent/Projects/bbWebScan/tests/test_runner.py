from pathlib import Path

import pytest

from bbwebscan.models import (
    AuthConfig,
    CommandPlan,
    RetryPolicy,
    RunArtifacts,
    RunConfig,
)
from bbwebscan.runner import (
    REDACT_PLACEHOLDER,
    prepare_run_artifacts,
    redact_command_for_log,
    run_plan,
)


def _config(tmp_path: Path, *, dry_run: bool = False) -> RunConfig:
    return RunConfig(
        program_name="t",
        seed_urls=[],
        allowed_hosts=[],
        denied_hosts=[],
        auth=AuthConfig(),
        mode="safe",
        enabled_tools=["httpx"],
        wordlist=Path("/tmp/w"),
        threads=1,
        rate=1,
        tool_timeout_s=1,
        command_wall_clock_s=5,
        retry=RetryPolicy(max_attempts=2, backoff_s=0.0),
        output_dir=tmp_path / "run",
        target_inputs=[],
        dry_run=dry_run,
    )


def _artifacts(tmp_path: Path) -> RunArtifacts:
    return prepare_run_artifacts(tmp_path / "run")


def test_run_plan_dry_run_writes_command_to_log(tmp_path: Path) -> None:
    config = _config(tmp_path, dry_run=True)
    artifacts = _artifacts(tmp_path)
    plan = CommandPlan(stage="x", label="x", command=["echo", "hi"], artifacts=[])
    result = run_plan(plan, config, artifacts)
    assert result.status == "dry-run"
    assert result.stdout_log is not None
    assert "echo hi" in result.stdout_log.read_text()


def test_run_plan_dry_run_prints_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path, dry_run=True)
    artifacts = _artifacts(tmp_path)
    plan = CommandPlan(stage="x", label="x", command=["echo", "hello world"], artifacts=[])
    run_plan(plan, config, artifacts)
    assert "echo 'hello world'" in capsys.readouterr().out


def test_run_plan_executes_real_command(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifacts = _artifacts(tmp_path)
    plan = CommandPlan(stage="x", label="echo", command=["/bin/echo", "ok"], artifacts=[])
    result = run_plan(plan, config, artifacts)
    assert result.status == "ok"
    assert result.exit_code == 0
    assert result.attempts == 1
    assert result.stdout_log is not None
    assert result.stdout_log.read_text().strip() == "ok"


def test_run_plan_records_missing_binary(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifacts = _artifacts(tmp_path)
    plan = CommandPlan(
        stage="x", label="missing", command=["/nonexistent/binary"], artifacts=[]
    )
    result = run_plan(plan, config, artifacts)
    assert result.status == "missing-binary"
    assert result.exit_code is None
    assert result.error is not None


def test_run_plan_retries_until_success(tmp_path: Path) -> None:
    """Use a marker file the test toggles to simulate transient failure."""
    config = _config(tmp_path)
    artifacts = _artifacts(tmp_path)
    flag = tmp_path / "flag"
    # Bash: first invocation creates flag and exits 137; second sees flag and exits 0.
    cmd = [
        "/bin/sh",
        "-c",
        f'if [ -e {flag} ]; then exit 0; else touch {flag}; exit 137; fi',
    ]
    plan = CommandPlan(stage="x", label="flaky", command=cmd, artifacts=[])
    result = run_plan(plan, config, artifacts)
    assert result.status == "ok"
    assert result.attempts == 2


def test_redact_command_for_log_handles_h_flag_form() -> None:
    """v0.4.4 #2: -H argv pairs get their VALUE masked but the header NAME
    stays so logs still tell you which header was sent."""
    cmd = ["httpx", "-H", "Authorization: Bearer SECRET-TOKEN", "-H", "X-Trace: 1"]
    redacted = redact_command_for_log(cmd)
    assert redacted[0] == "httpx"
    assert redacted[1] == "-H"
    assert redacted[2] == f"Authorization: {REDACT_PLACEHOLDER}"
    # Non-credential header stays verbatim:
    assert redacted[4] == "X-Trace: 1"


def test_redact_command_for_log_handles_cookie_header() -> None:
    cmd = ["nuclei", "-H", "Cookie: session=PRIVATE"]
    redacted = redact_command_for_log(cmd)
    assert redacted[2] == f"Cookie: {REDACT_PLACEHOLDER}"


def test_redact_command_for_log_handles_arjun_newline_form() -> None:
    """v0.4.4 #2: arjun gets all headers in one --headers argv element,
    newline-joined. Each line redacted in place."""
    blob = "Accept: application/json\nAuthorization: Bearer arjun-secret\nCookie: sid=zzz"
    cmd = ["arjun", "-u", "https://x", "--headers", blob]
    redacted = redact_command_for_log(cmd)
    masked = redacted[4]
    assert "Accept: application/json" in masked
    assert f"Authorization: {REDACT_PLACEHOLDER}" in masked
    assert f"Cookie: {REDACT_PLACEHOLDER}" in masked
    assert "arjun-secret" not in masked
    assert "sid=zzz" not in masked


def test_redact_command_for_log_passthrough_when_no_credentials() -> None:
    cmd = ["httpx", "-l", "/tmp/in", "-o", "/tmp/out", "-silent"]
    assert redact_command_for_log(cmd) == cmd


def test_run_plan_dry_run_redacts_command_to_log_and_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """v0.4.4 #2 end-to-end: dry-run echo redacts before printing AND before
    writing the stdout_log on disk. Secret nowhere in either surface."""
    config = _config(tmp_path, dry_run=True)
    artifacts = _artifacts(tmp_path)
    plan = CommandPlan(
        stage="x", label="x",
        command=["httpx", "-H", "Authorization: Bearer SECRET-XYZ"],
        artifacts=[],
    )
    run_plan(plan, config, artifacts)
    out = capsys.readouterr().out
    log_text = (artifacts.logs / "x.stdout.log").read_text(encoding="utf-8")
    assert "SECRET-XYZ" not in out
    assert "SECRET-XYZ" not in log_text
    assert "Authorization: <redacted>" in out
    assert "Authorization: <redacted>" in log_text
