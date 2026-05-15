from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from bbwebscan.config import config_to_dict
from bbwebscan.models import (
    SEVERITY_ORDER,
    CommandPlan,
    ExecutionResult,
    Finding,
    NormalizedTarget,
    RunArtifacts,
    RunConfig,
    ScopeDecision,
    ToolStatus,
)
from bbwebscan.preflight import collect_tool_inventory, validate_environment
from bbwebscan.reporting import build_summary_markdown, write_summary
from bbwebscan.runner import prepare_run_artifacts, run_plan, write_json, write_lines
from bbwebscan.stages import (
    amass_stage,
    discovery_stage,
    httpx_stage,
    jwt_tool_stage,
    katana_stage,
    kiterunner_stage,
    nuclei_stage,
    params_stage,
    scrapy_stage,
    sqlmap_stage,
)
from bbwebscan.targets import (
    collect_targets,
    filter_urls_in_scope,
    host_in_scope,
    normalize_target,
    resolve_host,
)


# [v0.5.5] Per-stage helpers operate on a single mutable state to avoid the
# 240-line if-chain that lived in execute_scan. State threading is explicit:
# every helper reads `state.config` / `state.active_urls` / `state.findings`
# and mutates the shared lists in place. No registry abstraction — call
# order in `execute_scan` is the authoritative pipeline order.
@dataclass
class _PipelineState:
    config: RunConfig
    artifacts: RunArtifacts
    targets: list[NormalizedTarget]
    allowed_hosts: list[str]
    scope_decisions: list[ScopeDecision]
    scoped_decision_values: set[str] = field(default_factory=set)
    allowed_url_cache: set[str] = field(default_factory=set)
    results: list[ExecutionResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    live_urls: list[str] = field(default_factory=list)
    discovered_urls: list[str] = field(default_factory=list)
    active_urls: list[str] = field(default_factory=list)
    dns_notes: list[str] = field(default_factory=list)


def execute_scan(config: RunConfig) -> int:
    artifacts = prepare_run_artifacts(config.output_dir)
    write_json(artifacts.root / "run_config.json", config_to_dict(config))
    targets, scope_decisions, allowed_hosts = collect_targets(config)
    write_lines(artifacts.root / "targets_normalized.txt", [t.seed_url for t in targets])
    statuses = collect_tool_inventory(config)
    write_json(
        artifacts.root / "tool_inventory.json",
        [status.model_dump(mode="json") for status in statuses],
    )
    errors = validate_environment(config, statuses)
    state = _PipelineState(
        config=config,
        artifacts=artifacts,
        targets=targets,
        allowed_hosts=allowed_hosts,
        scope_decisions=scope_decisions,
        scoped_decision_values={d.value for d in scope_decisions},
    )
    state.live_urls = [target.seed_url for target in state.targets]
    state.discovered_urls = list(state.live_urls)
    state.active_urls = _scope_active_urls(state, state.discovered_urls)
    if config.preflight_dns:
        # [v0.4.3 Item 8] Non-fatal note for unresolvable hosts so a typo'd target
        # doesn't silently waste a real scan but operators can still scan internal hosts.
        for target in state.targets:
            if resolve_host(target.host) is None:
                state.dns_notes.append(f"Note: {target.host} did not resolve via DNS")

    if not errors and not config.check_tools:
        # [v0.5.5] Pipeline order is amass → httpx → katana → scrapy →
        # discovery → kiterunner → arjun → jwt_tool → sqlmap → nuclei.
        _run_amass(state)
        _run_httpx(state)
        _run_katana(state)
        _run_scrapy(state)
        _run_discovery(state)
        _run_kiterunner(state)
        _run_arjun(state)
        _run_jwt_tool(state)
        _run_sqlmap(state)
        _run_nuclei(state)

    return _finalize_run(state, statuses, errors)


def _finalize_run(
    state: _PipelineState,
    statuses: list[ToolStatus],
    errors: list[str],
) -> int:
    config = state.config
    artifacts = state.artifacts
    # [v0.4.3 Item 5] Drop findings below the configured severity threshold so
    # findings.json + summary + exit code only reflect actionable signal.
    threshold_idx = SEVERITY_ORDER.index(config.min_severity)
    state.findings = [
        f for f in state.findings
        if f.severity in SEVERITY_ORDER
        and SEVERITY_ORDER.index(f.severity) >= threshold_idx
    ]
    # [FIX-BBW-10] Incomplete runtime stages are fatal even when parsers produce
    # no findings; otherwise CI can mark a timed-out scan as successful.
    fatal_errors = errors + _execution_errors(state.results)
    write_json(
        artifacts.root / "scope_decisions.json",
        [item.model_dump(mode="json") for item in state.scope_decisions],
    )
    write_json(
        artifacts.root / "findings.json",
        [finding.model_dump(mode="json") for finding in state.findings],
    )
    write_summary(
        artifacts.root / "summary.md",
        build_summary_markdown(
            config, state.findings, statuses, state.results, state.scope_decisions,
            fatal_errors + state.dns_notes,
        ),
    )
    if config.verbose:
        # [FIX-BBW-G] Close the loop so operators don't have to `cd runs/` to find output.
        allowed = sum(1 for d in state.scope_decisions if d.allowed)
        total = len(state.scope_decisions)
        severity_counts = Counter(f.severity for f in state.findings)
        if state.findings:
            severity_breakdown = " (" + ", ".join(
                f"{sev}={severity_counts[sev]}"
                for sev in SEVERITY_ORDER if severity_counts[sev]
            ) + ")"
        else:
            severity_breakdown = ""
        print(
            f"[bbwebscan] scan complete — {len(state.findings)} findings"
            f"{severity_breakdown}, {allowed}/{total} scope decisions allowed",
            flush=True,
        )
        print(f"[bbwebscan] artifacts: {artifacts.root}", flush=True)
    if fatal_errors:
        return 2
    if state.findings:
        # [v0.4.3 Item 5] Findings at or above min_severity → exit 3 for CI gating.
        return 3
    return 0


def _run_amass(state: _PipelineState) -> None:
    config = state.config
    # [v0.5.0] amass before httpx — discover subdomains, scope-filter,
    # extend the targets list with FQDNs that pass enforce_scope_gate.
    if not (config.enumerate_subdomains and "amass" in config.enabled_tools):
        return
    amass_plans = amass_stage.build_plan(config, state.artifacts, state.targets)
    state.results.extend(_run_stage_plans(amass_plans, config, state.artifacts))
    for plan in amass_plans:
        for artifact_path in plan.artifacts:
            amass_findings, fqdns = amass_stage.parse_results(artifact_path)
            state.findings.extend(amass_findings)
            state.targets = _extend_targets_with_fqdns(
                state.targets, fqdns, state.allowed_hosts, config.denied_hosts,
                state.scope_decisions, state.scoped_decision_values,
            )
    # Refresh the URL caches with the newly-added targets.
    state.live_urls = [t.seed_url for t in state.targets]
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + state.live_urls))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)


def _run_httpx(state: _PipelineState) -> None:
    config = state.config
    if "httpx" not in config.enabled_tools:
        return
    state.results.extend(
        _run_stage_plans(
            httpx_stage.build_plan(config, state.artifacts, state.targets),
            config, state.artifacts,
        )
    )
    new_findings, live_urls = httpx_stage.parse_results(
        state.artifacts.artifacts / "httpx.jsonl"
    )
    state.findings.extend(new_findings)
    state.live_urls = _scope_active_urls(state, live_urls)
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + state.live_urls))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)


def _run_katana(state: _PipelineState) -> None:
    config = state.config
    if "katana" not in config.enabled_tools:
        return
    state.results.extend(
        _run_stage_plans(
            katana_stage.build_plan(
                config, state.artifacts, state.live_urls or state.active_urls,
            ),
            config, state.artifacts,
        )
    )
    crawl_findings, crawled_urls = katana_stage.parse_results(
        state.artifacts.artifacts / "katana.jsonl"
    )
    state.findings.extend(crawl_findings)
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + crawled_urls))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)


def _run_scrapy(state: _PipelineState) -> None:
    config = state.config
    # [v0.5.3] Scrapy runs alongside katana — both feed discovered_urls.
    # Order is intentional: katana first so scrapy can also crawl the URLs
    # katana surfaced. cyberref: PENDING attestation (CyberPDF vault citation
    # outstanding; see CHANGELOG 0.5.5 Notes).
    if "scrapy" not in config.enabled_tools:
        return
    scrapy_input = state.live_urls or state.active_urls
    if not scrapy_input:
        return
    state.results.extend(
        _run_stage_plans(
            scrapy_stage.build_plan(config, state.artifacts, scrapy_input),
            config, state.artifacts,
        )
    )
    scrapy_findings, scrapy_urls = scrapy_stage.parse_results(
        state.artifacts.artifacts / "scrapy.jsonl"
    )
    state.findings.extend(scrapy_findings)
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + scrapy_urls))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)
    # [v0.5.3] Auto-suggest: if Scrapy ran without deep mode and found
    # no high/medium signals, hint that --scrapy-deep may surface
    # secrets/credentials.
    if not config.scrapy_deep and not any(
        f.stage == "scrapy" and f.severity in {"high", "medium"}
        for f in scrapy_findings
    ):
        state.dns_notes.append(
            "Hint: re-run with --scrapy-deep to enable credential/secret "
            "extraction (vendored ruleset; never echoes raw values)."
        )


def _run_discovery(state: _PipelineState) -> None:
    config = state.config
    if not any(tool in config.enabled_tools for tool in discovery_stage.DISCOVERY_TOOLS):
        return
    plans = discovery_stage.build_plans(
        config, state.artifacts, state.live_urls or state.active_urls,
    )
    state.results.extend(_run_stage_plans(plans, config, state.artifacts))
    discovery_findings, extra_urls = discovery_stage.parse_results(
        _artifact_paths(plans), config
    )
    state.findings.extend(discovery_findings)
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + extra_urls))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)


def _run_kiterunner(state: _PipelineState) -> None:
    config = state.config
    # [v0.5.0] kiterunner runs alongside discovery when --api-discovery is set.
    # Findings stay separate (kind='api-route') so reports distinguish them.
    if not (config.api_discovery and "kiterunner" in config.enabled_tools):
        return
    kr_plans = kiterunner_stage.build_plans(
        config, state.artifacts, state.live_urls or state.active_urls,
    )
    state.results.extend(_run_stage_plans(kr_plans, config, state.artifacts))
    kr_findings, kr_routes = kiterunner_stage.parse_results(_artifact_paths(kr_plans))
    state.findings.extend(kr_findings)
    state.discovered_urls = list(dict.fromkeys(state.discovered_urls + kr_routes))
    state.active_urls = _scope_active_urls(state, state.discovered_urls)


def _run_arjun(state: _PipelineState) -> None:
    config = state.config
    if "arjun" not in config.enabled_tools:
        return
    plans = params_stage.build_plans(config, state.artifacts, state.active_urls)
    state.results.extend(_run_stage_plans(plans, config, state.artifacts))
    params_findings, _ = params_stage.parse_results(_artifact_paths(plans))
    state.findings.extend(params_findings)


def _run_jwt_tool(state: _PipelineState) -> None:
    config = state.config
    # [v0.5.5] jwt_tool consumes Bearer tokens from auth.headers Authorization.
    # Scrapy-harvested JWT candidates are deferred (see CHANGELOG 0.5.5 Notes).
    if not (config.jwt_analysis and "jwt_tool" in config.enabled_tools):
        return
    plan = jwt_tool_stage.build_plan(config, state.artifacts)
    if plan is None:
        # No Bearer token to analyse — surface as note, not an error.
        state.dns_notes.append(
            "Note: --jwt-analysis enabled but no Bearer token in --header Authorization"
        )
        return
    state.results.extend(_run_stage_plans([plan], config, state.artifacts))
    for artifact_path in plan.artifacts:
        state.findings.extend(jwt_tool_stage.parse_results(artifact_path))


def _run_sqlmap(state: _PipelineState) -> None:
    config = state.config
    # [v0.5.5] sqlmap consumes parameterised URLs (those carrying a query
    # string) discovered by upstream stages. arjun output names parameters
    # but does not synthesise URLs; sqlmap inspects the query string itself,
    # so we feed every active URL with a `?` component.
    if config.sqlmap_mode == "off" or "sqlmap" not in config.enabled_tools:
        return
    parameterised = [url for url in state.active_urls if "?" in url]
    if not parameterised:
        state.dns_notes.append(
            f"Note: --sqlmap-mode {config.sqlmap_mode} enabled but no parameterised "
            "URLs surfaced by upstream stages"
        )
        return
    plans = sqlmap_stage.build_plans(config, state.artifacts, parameterised)
    state.results.extend(_run_stage_plans(plans, config, state.artifacts))
    sqlmap_findings, _ = sqlmap_stage.parse_results(_artifact_paths(plans))
    state.findings.extend(sqlmap_findings)


def _run_nuclei(state: _PipelineState) -> None:
    config = state.config
    if "nuclei" not in config.enabled_tools:
        return
    plans = nuclei_stage.build_plan(
        config, state.artifacts, state.active_urls or state.live_urls,
    )
    state.results.extend(_run_stage_plans(plans, config, state.artifacts))
    nuclei_findings, _ = nuclei_stage.parse_results(
        state.artifacts.artifacts / "nuclei.jsonl"
    )
    state.findings.extend(nuclei_findings)


def _run_stage_plans(
    plans: list[CommandPlan], config: RunConfig, artifacts: RunArtifacts,
) -> list[ExecutionResult]:
    return [run_plan(plan, config, artifacts) for plan in plans]


def _artifact_paths(plans: list[CommandPlan]) -> list[Path]:
    return [artifact for plan in plans for artifact in plan.artifacts]


def _execution_errors(results: list[ExecutionResult]) -> list[str]:
    errors: list[str] = []
    for result in results:
        if result.status in {"ok", "dry-run"}:
            continue
        message = (
            f"Execution failed: {result.stage}/{result.label} "
            f"status={result.status}"
        )
        if result.exit_code is not None:
            message = f"{message} exit={result.exit_code}"
        if result.error:
            message = f"{message} error={result.error}"
        elif result.stderr_log is not None:
            message = f"{message} stderr={result.stderr_log}"
        errors.append(message)
    return errors


def _scope_active_urls(state: _PipelineState, urls: list[str]) -> list[str]:
    # [FIX-BBW-02] Filter crawler output before any active follow-up stage can probe it.
    # [FIX-BBW-07] Pass scoped_decision_values so the filter skips URLs already decided;
    # allowed_url_cache lets us still return previously-allowed URLs without re-deciding them.
    _, url_decisions = filter_urls_in_scope(
        urls, state.allowed_hosts, state.config.denied_hosts,
        already_decided=state.scoped_decision_values,
    )
    for decision in url_decisions:
        state.scope_decisions.append(decision)
        state.scoped_decision_values.add(decision.value)
        if decision.allowed:
            state.allowed_url_cache.add(decision.value)
    return [url for url in urls if url in state.allowed_url_cache]


def _extend_targets_with_fqdns(  # noqa: PLR0913 - threading scope state through helper
    targets: list[NormalizedTarget],
    fqdns: list[str],
    allowed_hosts: list[str],
    denied_hosts: list[str],
    scope_decisions: list[ScopeDecision],
    scoped_decision_values: set[str],
) -> list[NormalizedTarget]:
    """[v0.5.0] amass-discovered FQDNs become NormalizedTargets if in scope.

    Each FQDN passes through `enforce_scope_gate` (via host_in_scope). Out-of-scope
    FQDNs are recorded in scope_decisions but never become scan targets. Already-known
    target hosts are skipped to keep the targets list de-duplicated.
    """
    known_hosts = {t.host for t in targets}
    extended = list(targets)
    for fqdn in fqdns:
        if fqdn in scoped_decision_values:
            continue
        try:
            normalized = normalize_target(fqdn)
        except ValueError:
            scope_decisions.append(
                ScopeDecision(value=fqdn, allowed=False, reason="invalid-target")
            )
            scoped_decision_values.add(fqdn)
            continue
        decision = host_in_scope(normalized.host, allowed_hosts, denied_hosts)
        scope_decisions.append(decision)
        scoped_decision_values.add(fqdn)
        if not decision.allowed:
            continue
        if normalized.host in known_hosts:
            continue
        extended.append(normalized)
        known_hosts.add(normalized.host)
    return extended
