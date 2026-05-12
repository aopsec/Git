import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from bbwebscan.models import CommandPlan, ExecutionResult, RunArtifacts, RunConfig
from bbwebscan.retry import with_retry

# [v0.4.4] Match argv elements that carry header values: the leading "<name>: "
# is preserved so the audit trail records WHICH header was set; the value is
# replaced with the redacted placeholder.
_REDACT_HEADER_RE: re.Pattern[str] = re.compile(
    r"^(authorization|cookie):\s*", re.IGNORECASE,
)
REDACT_PLACEHOLDER: str = "<redacted>"


def redact_command_for_log(command: list[str]) -> list[str]:
    """[v0.4.4] Mask Authorization/Cookie header VALUES before logging argv.

    Two argv shapes are handled:

    1. ``["-H", "Authorization: Bearer secret"]`` — typical for httpx, katana,
       nuclei, ffuf, feroxbuster, dirsearch.
    2. arjun's single-arg form: ``["--headers", "Accept: x\\nAuthorization: y\\n..."]``
       — a multi-line string passed as one element. Each line redacted in place.
    """
    return [_redact_argv_element(arg) for arg in command]


def _redact_argv_element(arg: str) -> str:
    if "\n" in arg:
        # arjun-style multi-header argv element
        return "\n".join(_redact_header_line(line) for line in arg.split("\n"))
    return _redact_header_line(arg)


def _redact_header_line(line: str) -> str:
    match = _REDACT_HEADER_RE.match(line)
    if match is None:
        return line
    return f"{match.group(0).rstrip()} {REDACT_PLACEHOLDER}"


def prepare_run_artifacts(output_dir: Path) -> RunArtifacts:
    root = Path(output_dir)
    logs = root / "logs"
    artifacts = root / "artifacts"
    logs.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    return RunArtifacts(root=root, logs=logs, artifacts=artifacts)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_lines(path: Path, values: list[str]) -> None:
    path.write_text("\n".join(values) + ("\n" if values else ""), encoding="utf-8")


def _execute_once(
    plan: CommandPlan,
    config: RunConfig,
    stdout_log: Path,
    stderr_log: Path,
) -> tuple[str, int | None, str | None]:
    try:
        with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open(
            "w", encoding="utf-8"
        ) as err:
            completed = subprocess.run(
                plan.command,
                check=False,
                stdout=out,
                stderr=err,
                timeout=config.command_wall_clock_s,
            )
    except subprocess.TimeoutExpired:
        stderr_log.write_text(
            f"timeout after {config.command_wall_clock_s}s\n", encoding="utf-8"
        )
        return ("timeout", 124, f"timeout after {config.command_wall_clock_s}s")
    except FileNotFoundError as exc:
        stderr_log.write_text(f"executable not found: {exc}\n", encoding="utf-8")
        return ("missing-binary", None, str(exc))
    except OSError as exc:
        stderr_log.write_text(f"os error: {exc}\n", encoding="utf-8")
        return ("os-error", None, str(exc))
    status = "ok" if completed.returncode == 0 else "failed"
    return (status, completed.returncode, None)


def run_plan(plan: CommandPlan, config: RunConfig, artifacts: RunArtifacts) -> ExecutionResult:
    stdout_log = artifacts.logs / f"{plan.label}.stdout.log"
    stderr_log = artifacts.logs / f"{plan.label}.stderr.log"
    if config.dry_run:
        # [FIX-BBW-06] Match the documented dry-run behavior by printing planned commands.
        # [v0.4.4] Redact Authorization/Cookie header VALUES before echo so secrets
        # don't land in stdout_log on disk or in console output.
        command_line = shlex.join(redact_command_for_log(plan.command))
        print(command_line)
        stdout_log.write_text(command_line + "\n", encoding="utf-8")
        stderr_log.write_text("", encoding="utf-8")
        return ExecutionResult(
            stage=plan.stage,
            label=plan.label,
            command=plan.command,
            status="dry-run",
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            artifacts=plan.artifacts,
        )

    if config.verbose:
        # [FIX-BBW-09] Per-stage progress so long real runs aren't silent.
        print(f"[{plan.stage}] {plan.label} starting", flush=True)

    def attempt() -> tuple[str, int | None, str | None]:
        return _execute_once(plan, config, stdout_log, stderr_log)

    def is_transient(result: tuple[str, int | None, str | None]) -> bool:
        status, exit_code, _ = result
        if status == "ok":
            return False
        if status == "timeout":
            return True
        return exit_code is not None and exit_code in config.retry.transient_exit_codes

    (status, exit_code, error), attempts = with_retry(
        attempt, policy=config.retry, is_transient=is_transient
    )
    if config.verbose:
        print(
            f"[{plan.stage}] {plan.label} → {status} "
            f"(exit={exit_code}, attempts={attempts})",
            flush=True,
        )
    return ExecutionResult(
        stage=plan.stage,
        label=plan.label,
        command=plan.command,
        status=status,
        exit_code=exit_code,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        artifacts=plan.artifacts,
        attempts=attempts,
        error=error,
    )
