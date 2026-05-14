from collections import Counter
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


def execute_scan(config: RunConfig) -> int:  # noqa: PLR0912, PLR0915 - orchestration is naturally wide
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
    dns_notes: list[str] = []
    if config.preflight_dns:
        # [v0.4.3 Item 8] Non-fatal note for unresolvable hosts so a typo'd target
        # doesn't silently waste a real scan but operators can still scan internal hosts.
        # Notes go in summary's Errors section but never trigger exit 2.
        for target in targets:
            if resolve_host(target.host) is None:
                dns_notes.append(f"Note: {target.host} did not resolve via DNS")
    results: list[ExecutionResult] = []
    findings: list[Finding] = []
    live_urls = [target.seed_url for target in targets]
    discovered_urls = list(live_urls)
    scoped_decision_values = {decision.value for decision in scope_decisions}
    allowed_url_cache: set[str] = set()
    active_urls = _scope_active_urls(
        discovered_urls,
        allowed_hosts,
        config.denied_hosts,
        scope_decisions,
        scoped_decision_values,
        allowed_url_cache,
    )

    if not errors and not config.check_tools:
        # [v0.5.0] amass before httpx — discover subdomains, scope-filter,
        # extend the targets list with FQDNs that pass enforce_scope_gate.
        if config.enumerate_subdomains and "amass" in config.enabled_tools:
            amass_plans = amass_stage.build_plan(config, artifacts, targets)
            results.extend(_run_stage_plans(amass_plans, config, artifacts))
            for plan in amass_plans:
                for artifact_path in plan.artifacts:
                    amass_findings, fqdns = amass_stage.parse_results(artifact_path)
                    findings.extend(amass_findings)
                    targets = _extend_targets_with_fqdns(
                        targets, fqdns, allowed_hosts, config.denied_hosts,
                        scope_decisions, scoped_decision_values,
                    )
            # Refresh the URL caches with the newly-added targets.
            live_urls = [t.seed_url for t in targets]
            discovered_urls = list(dict.fromkeys(discovered_urls + live_urls))
            active_urls = _scope_active_urls(
                discovered_urls, allowed_hosts, config.denied_hosts,
                scope_decisions, scoped_decision_values, allowed_url_cache,
            )

        if "httpx" in config.enabled_tools:
            results.extend(
                _run_stage_plans(
                    httpx_stage.build_plan(config, artifacts, targets), config, artifacts,
                )
            )
            new_findings, live_urls = httpx_stage.parse_results(
                artifacts.artifacts / "httpx.jsonl"
            )
            findings.extend(new_findings)
            live_urls = _scope_active_urls(
                live_urls, allowed_hosts, config.denied_hosts,
                scope_decisions, scoped_decision_values, allowed_url_cache,
            )
            discovered_urls = list(dict.fromkeys(discovered_urls + live_urls))
            active_urls = _scope_active_urls(
                discovered_urls,
                allowed_hosts,
                config.denied_hosts,
                scope_decisions,
                scoped_decision_values,
                allowed_url_cache,
            )

        if "katana" in config.enabled_tools:
            results.extend(
                _run_stage_plans(
                    katana_stage.build_plan(config, artifacts, live_urls or active_urls),
                    config,
                    artifacts,
                )
            )
            crawl_findings, crawled_urls = katana_stage.parse_results(
                artifacts.artifacts / "katana.jsonl"
            )
            findings.extend(crawl_findings)
            discovered_urls = list(dict.fromkeys(discovered_urls + crawled_urls))
            active_urls = _scope_active_urls(
                discovered_urls,
                allowed_hosts,
                config.denied_hosts,
                scope_decisions,
                scoped_decision_values,
                allowed_url_cache,
            )

        # [v0.5.3] Scrapy runs alongside katana — both feed discovered_urls.
        # Order is intentional: katana first so scrapy can also crawl the URLs
        # katana surfaced. cyberref: PENDING attestation.
        if "scrapy" in config.enabled_tools:
            scrapy_input = live_urls or active_urls
            if scrapy_input:
                results.extend(
                    _run_stage_plans(
                        scrapy_stage.build_plan(config, artifacts, scrapy_input),
                        config,
                        artifacts,
                    )
                )
                scrapy_findings, scrapy_urls = scrapy_stage.parse_results(
                    artifacts.artifacts / "scrapy.jsonl"
                )
                findings.extend(scrapy_findings)
                discovered_urls = list(dict.fromkeys(discovered_urls + scrapy_urls))
                active_urls = _scope_active_urls(
                    discovered_urls,
                    allowed_hosts,
                    config.denied_hosts,
                    scope_decisions,
                    scoped_decision_values,
                    allowed_url_cache,
                )
                # [v0.5.3] Auto-suggest: if Scrapy ran without deep mode and found
                # no high/medium signals, hint that --scrapy-deep may surface
                # secrets/credentials.
                if not config.scrapy_deep and not any(
                    f.stage == "scrapy" and f.severity in {"high", "medium"}
                    for f in scrapy_findings
                ):
                    dns_notes.append(
                        "Hint: re-run with --scrapy-deep to enable credential/secret "
                        "extraction (vendored ruleset; never echoes raw values)."
                    )

        if any(tool in config.enabled_tools for tool in discovery_stage.DISCOVERY_TOOLS):
            plans = discovery_stage.build_plans(config, artifacts, live_urls or active_urls)
            results.extend(_run_stage_plans(plans, config, artifacts))
            discovery_findings, extra_urls = discovery_stage.parse_results(
                _artifact_paths(plans), config
            )
            findings.extend(discovery_findings)
            discovered_urls = list(dict.fromkeys(discovered_urls + extra_urls))
            active_urls = _scope_active_urls(
                discovered_urls,
                allowed_hosts,
                config.denied_hosts,
                scope_decisions,
                scoped_decision_values,
                allowed_url_cache,
            )

        # [v0.5.0] kiterunner runs alongside discovery when --api-discovery is set.
        # Findings stay separate (kind='api-route') so reports distinguish them.
        if config.api_discovery and "kiterunner" in config.enabled_tools:
            kr_plans = kiterunner_stage.build_plans(
                config, artifacts, live_urls or active_urls,
            )
            results.extend(_run_stage_plans(kr_plans, config, artifacts))
            kr_findings, kr_routes = kiterunner_stage.parse_results(
                _artifact_paths(kr_plans)
            )
            findings.extend(kr_findings)
            discovered_urls = list(dict.fromkeys(discovered_urls + kr_routes))
            active_urls = _scope_active_urls(
                discovered_urls,
                allowed_hosts,
                config.denied_hosts,
                scope_decisions,
                scoped_decision_values,
                allowed_url_cache,
            )

        if "arjun" in config.enabled_tools:
            plans = params_stage.build_plans(config, artifacts, active_urls)
            results.extend(_run_stage_plans(plans, config, artifacts))
            params_findings, _ = params_stage.parse_results(_artifact_paths(plans))
            findings.extend(params_findings)

        if "nuclei" in config.enabled_tools:
            plans = nuclei_stage.build_plan(config, artifacts, active_urls or live_urls)
            results.extend(_run_stage_plans(plans, config, artifacts))
            nuclei_findings, _ = nuclei_stage.parse_results(artifacts.artifacts / "nuclei.jsonl")
            findings.extend(nuclei_findings)

    # [v0.4.3 Item 5] Drop findings below the configured severity threshold so
    # findings.json + summary + exit code only reflect actionable signal.
    threshold_idx = SEVERITY_ORDER.index(config.min_severity)
    findings = [
        f for f in findings
        if f.severity in SEVERITY_ORDER
        and SEVERITY_ORDER.index(f.severity) >= threshold_idx
    ]
    # [FIX-BBW-10] Incomplete runtime stages are fatal even when parsers produce
    # no findings; otherwise CI can mark a timed-out scan as successful.
    fatal_errors = errors + _execution_errors(results)
    write_json(
        artifacts.root / "scope_decisions.json",
        [item.model_dump(mode="json") for item in scope_decisions],
    )
    write_json(
        artifacts.root / "findings.json",
        [finding.model_dump(mode="json") for finding in findings],
    )
    write_summary(
        artifacts.root / "summary.md",
        build_summary_markdown(
            config, findings, statuses, results, scope_decisions,
            fatal_errors + dns_notes,
        ),
    )
    if config.verbose:
        # [FIX-BBW-G] Close the loop so operators don't have to `cd runs/` to find output.
        allowed = sum(1 for d in scope_decisions if d.allowed)
        total = len(scope_decisions)
        severity_counts = Counter(f.severity for f in findings)
        if findings:
            severity_breakdown = " (" + ", ".join(
                f"{sev}={severity_counts[sev]}"
                for sev in SEVERITY_ORDER if severity_counts[sev]
            ) + ")"
        else:
            severity_breakdown = ""
        print(
            f"[bbwebscan] scan complete — {len(findings)} findings"
            f"{severity_breakdown}, {allowed}/{total} scope decisions allowed",
            flush=True,
        )
        print(f"[bbwebscan] artifacts: {artifacts.root}", flush=True)
    if fatal_errors:
        return 2
    if findings:
        # [v0.4.3 Item 5] Findings at or above min_severity → exit 3 for CI gating.
        return 3
    return 0


def _run_stage_plans(
    plans: list[CommandPlan], config: RunConfig, artifacts: RunArtifacts
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


def _scope_active_urls(  # noqa: PLR0913 - threading scope state through the pipeline
    urls: list[str],
    allowed_hosts: list[str],
    denied_hosts: list[str],
    scope_decisions: list[ScopeDecision],
    scoped_decision_values: set[str],
    allowed_url_cache: set[str],
) -> list[str]:
    # [FIX-BBW-02] Filter crawler output before any active follow-up stage can probe it.
    # [FIX-BBW-07] Pass scoped_decision_values so the filter skips URLs already decided;
    # allowed_url_cache lets us still return previously-allowed URLs without re-deciding them.
    _, url_decisions = filter_urls_in_scope(
        urls, allowed_hosts, denied_hosts, already_decided=scoped_decision_values
    )
    for decision in url_decisions:
        scope_decisions.append(decision)
        scoped_decision_values.add(decision.value)
        if decision.allowed:
            allowed_url_cache.add(decision.value)
    return [url for url in urls if url in allowed_url_cache]


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
