# Changelog

All notable changes to bbWebScan are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [SemVer](https://semver.org/).

## [0.5.5] — 2026-05-14

### Security
- jwt_tool dry-run argv echo now masks the Bearer token slot.
  `bbwebscan/stages/jwt_tool_stage.py` marks the `-t <token>` position via
  the new `CommandPlan.redact_indices` field;
  `bbwebscan/runner.py::redact_command_for_log` masks the indexed slot
  before its existing header-flag walk. Previously the JWT was written
  verbatim to stdout AND `runs/<UTC>/logs/jwt_tool.stdout.log` when
  `--dry-run --jwt-analysis` was combined, regressing the documented
  invariant *"Dry-run argv echo masks `Authorization:` and `Cookie:`
  header values"*. Internal review finding (Medium severity, confidence 8/10).
  Future stages that pass secrets via non-header argv slots (e.g.
  `sqlmap --auth-cred user:pass`, `sqlmap --cookie`) opt in by setting
  `redact_indices` on the plan they return.

### Added
- `jwt_tool` stage for JWT analysis (`bbwebscan/stages/jwt_tool_stage.py`).
  Opt-in via `--jwt-analysis`. Consumes Bearer tokens from
  `config.auth.headers["Authorization"]`. Emits `kind="jwt-issue"` findings
  (alg=none → high, weak-secret cracked → critical, kid/header injection →
  high). Scrapy-harvested JWT candidates from response bodies / `Set-Cookie`
  are deferred to a later release.
- `sqlmap` stage with two modes (`bbwebscan/stages/sqlmap_stage.py`):
  `--sqlmap-mode {off,smooth,aggressive}` (default `off`). `smooth` uses
  `--batch --random-agent --level=1 --risk=1` with per-URL timeout cap;
  `aggressive` uses `--level=5 --risk=3 --tamper=between,space2comment`
  and requires `--ack-authorized` (mirrors amass active/intel gate).
  Consumes parameterised URLs (any `state.active_url` containing `?`)
  surfaced by upstream crawl/discovery stages. Emits `kind="sql-injection"`
  findings.
- `--sqlmap-timeout` CLI flag (default `600`). Per-request `--timeout` is
  derived as `budget/10` (smooth) or `budget/5` (aggressive).
- `jwt_tool` and `sqlmap` registered in `OPTIONAL_TOOLS`, `INSTALL_HINTS`,
  and surfaced by `bbwebscan doctor`.
- Menu prompts for `jwt-analysis`, `sqlmap-mode`, and `sqlmap-timeout` in
  `menu_scan.py`. Selecting `aggressive` re-prompts for the authorisation
  acknowledgement, matching the amass active/intel flow.

### Changed
- Vendored secrets-patterns ruleset (`bbwebscan/data/secrets_patterns.yml`)
  refreshed from upstream `mazen160/secrets-patterns-db`. AGPL- /
  trufflehog-derived rules continue to be excluded. See `NOTICE` for the
  pinned upstream commit.
- `bbwebscan/pipeline.py` refactored: per-stage helpers `_run_amass`,
  `_run_httpx`, `_run_katana`, `_run_scrapy`, `_run_discovery`,
  `_run_kiterunner`, `_run_arjun`, `_run_jwt_tool`, `_run_sqlmap`,
  `_run_nuclei`, threading a single `_PipelineState` dataclass.
  `execute_scan` is now a flat sequence of gated helper calls instead of a
  single 240-line if-chain. No registry abstraction — ordering remains
  explicit and grep-able.

### Notes
- 0.5.4 deliberately skipped (no shipped 0.5.4 release exists). Version
  jumps from 0.5.3 → 0.5.5.
- Pipeline stage order is now: amass → httpx → katana → scrapy →
  discovery → kiterunner → arjun → jwt_tool → sqlmap → nuclei.
- Scrapy stage cyberref attestation **remains `PENDING`**: the CyberPDF
  vault has no Scrapy reference yet. Promotion to "certified" is gated on
  vault citation, not on shipping the stage. Marker is intentionally
  preserved at `bbwebscan/stages/scrapy_stage.py` and `pipeline.py::_run_scrapy`.
- jwt_tool stage carries the same `cyberref: PENDING` marker for the same
  reason; promote when JWT/RFC 7519 reference lands in the CyberPDF vault.
- Scrapy community plugin/recon-tool review captured in this release
  notes only; no plugins vendored in 0.5.5.

## [0.5.3] — 2026-05-14

### Fixed
- `[FIX-BBW-10]` Opt-in tools `--enumerate-subdomains` and `--api-discovery`
  now flow through `add_opt_in_tools()` in `bbwebscan/config.py`, so they
  appear in the same effective tool set used by inventory and preflight.
  Conflict with `--disable-tool {amass,kiterunner}` is now an explicit
  `ValueError` instead of a silent no-op.
- `[FIX-BBW-10]` Pipeline stages now gate on `"<tool>" in config.enabled_tools`,
  matching the contract `add_opt_in_tools` produces. Disabling httpx/katana via
  `--disable-tool` no longer leaves dangling references downstream.
- `[FIX-BBW-10]` Runtime stage failures (non-zero exit, timeout) are now
  promoted to fatal in `bbwebscan/pipeline.py::_execution_errors`. Previously
  a timed-out scan with no parser-emitted findings could exit `0`; it now
  exits `2`.

### Security
- `[FIX-BBW-10]` Broader header-value redaction in
  `bbwebscan.runner.redact_command_for_log`. Any value following `-H`,
  `--header`, or `--headers` is masked, plus inline `--header=Name: value`
  forms. Catches `X-API-Key`, `X-Auth-Token`, and custom auth header names
  that the previous Authorization/Cookie-only regex missed.

### Added
- **Scrapy crawler stage** (cyberref: PENDING attestation). New
  `bbwebscan/stages/scrapy_stage.py` and bundled spider
  `bbwebscan/stages/scrapy/bbspider.py`. Runs alongside katana in safe
  mode and harvests information-disclosure signals: documents (PDF/DOC/
  XLS/backup archives), emails, exposed paths (`.git`, `.env`,
  `wp-admin`), and — when `--scrapy-deep` is set — credential/secret
  patterns via a vendored ruleset.
- CLI flags `--scrapy-deep` (off by default) and `--scrapy-max-depth`
  (1–5, default 2). Scan Wizard menu now prompts for both.
- Vendored secret-pattern ruleset at
  `bbwebscan/data/secrets_patterns.yml` (curated subset of
  [mazen160/secrets-patterns-db](https://github.com/mazen160/secrets-patterns-db),
  CC-BY-4.0; AGPL/trufflehog-derived rules excluded). See `NOTICE`.
- Optional `[js]` extra pulls
  [`scrapy-playwright`](https://github.com/scrapy-plugins/scrapy-playwright)
  (1.4k★, BSD-3-Clause) for JS rendering when `--scrapy-js-render` is set.
  Off by default — `pip install bbwebscan[js]` + `playwright install chromium`
  required.
- Auto-suggest hint in `summary.md`: if Scrapy ran without deep mode and
  surfaced no high/medium findings, the summary recommends re-running with
  `--scrapy-deep`.
- `scripts/verify.sh` aggregated gate (`ruff` → `mypy` → `pytest --cov`).

### Notes
- **cyberref: PENDING attestation** — Scrapy itself is not yet attested in the
  CyberPDF vault. This stage ships with that explicit marker; promote to
  "certified" once vault citation lands. Tracked in meta-vault `CLAUDE.md`.
- Secret findings record only a SHA-256 prefix (16 chars) + rule name +
  source URL as evidence. The matched string is never persisted.

## [0.5.2] — 2026-05-11

### Fixed
- Main menu dispatch now catches user-facing exceptions from menu routes:
  `FileNotFoundError`, `FileExistsError`, `ValueError`, and `OSError`.
  The menu prints `[bbwebscan menu] <error>` and returns to the main menu
  instead of crashing with a traceback.
- Save Profile no longer persists `settings.raw_request` into profile YAML.
  Raw request paths are now treated strictly as one-off run inputs, aligned
  with existing one-off header/cookie handling.

### Security
- Profile persistence hardening: raw request file paths are excluded from
  saved profiles to prevent accidental carryover of temporary request files.

## [0.5.1] — 2026-05-11

### Added
- `bbwebscan menu` subcommand and no-args `bbwebscan` menu default. The menu
  is Rich-backed when `rich>=13` is installed and falls back to plain terminal
  output in unbootstrapped development environments.
- Scan Wizard for existing scan arguments: targets/input file, profile, mode,
  authorization acknowledgement, tool toggles, amass mode, API discovery,
  one-off auth, wordlist, rate/thread/timeouts, severity, DNS check, output
  directory, dry-run preference, quiet mode, and strict identity.
- Scan Action Menu: preview equivalent command, dry-run, run scan, save profile,
  edit settings, or return to main menu.
- Doctor / Auto Fix Tools menu flow. It inventories first, displays a table,
  shows planned `doctor --fix-path` / `install` actions, and requires one
  confirmation before invoking the existing helpers.
- Menu-driven profile saving that writes only env-var auth references such as
  `${BBW_TOKEN}`; one-off plaintext header/cookie inputs are never persisted to
  profile YAML.
- Runtime dependency: `rich>=13`.

### Changed
- Existing direct CLI usage remains valid, including smart defaults such as
  `bbwebscan example.com --dry-run`. Only the no-args behavior changed from the
  static welcome panel to the interactive menu.

## [0.5.0] — 2026-05-09

### Added
- **`amass` subdomain enumeration stage** (vault: hacking-apis p. 123,
  `Tool Index.md` + `Command Cheat Index.md`). Runs before httpx when
  `--enumerate-subdomains` is set; FQDNs pass through `enforce_scope_gate`
  before reaching downstream stages. Modes: `passive` (default), `active`,
  `intel`. `active` and `intel` make detectable DNS queries and require
  `--ack-authorized`.
- **`kiterunner` API route discovery** (vault: hacking-apis p. 124,
  `Command Cheat Index.md`). Runs alongside `discovery` stage when
  `--api-discovery` is set. Findings carry `kind="api-route"`; status
  200/3xx → `info`, 401/403 → `low`.
- CLI flags on `bbwebscan scan`: `--enumerate-subdomains`,
  `--amass-mode {passive,active,intel}`, `--api-discovery`.
- `RunConfig.enumerate_subdomains`, `RunConfig.api_discovery`,
  `RunConfig.amass_mode` (Pydantic Literal type).
- `bbwebscan/stages/amass_stage.py` and
  `bbwebscan/stages/kiterunner_stage.py`.
- Fingerprint regexes for `amass` and `kiterunner` in
  `preflight.TOOL_IDENTITY` derived from observed v4.2.0 / v1.0.2 banners.
  Adversarial test asserts a fake binary just printing the tool name does
  NOT pass.
- `INSTALL_HINTS["amass"]` and `INSTALL_HINTS["kiterunner"]` with verified
  upstream paths (curl -sI returned 200 during install).

### Deferred (vault-attested but not v0.5.0 scope)
- `sqlmap` (vault: blackhat-graphql p. 125-126) — exploitation surface;
  separate release with explicit auth gating + redaction stack.
- `jwt_tool` (vault: hacking-apis p. 225) — narrow scope; v0.5.1 candidate.
- `wappalyzer` (vault: blackhat-graphql p. 67) — overlaps existing
  httpx `--tech-detect`.

### Notes
- `amass enum -version` outputs only the version number (no banner). The
  fingerprint relies on `detect_identity`'s `--help` fallback which probes
  `amass --help` whose banner contains `OWASP Amass Project`.
- kiterunner binary name is `kiterunner`, not `kr` (despite some upstream
  docs using `kr`). Plan's `cmd/kr` install URL was wrong; verified
  package layout is `cmd/kiterunner`.
- amass v4 deprecated `-passive` (passive is default) and
  `-max-dns-queries` (replaced by `-dns-qps`). bbWebScan does NOT inject
  rate-limit flags silently — operators set them via profile-supplied
  amass args in a future release.

## [0.4.4] — 2026-05-09

### Fixed
- **HIGH (security)** — Credential leak to disk via
  `runs/<UTC>/run_config.json`. `auth.headers` and `auth.cookies` values are
  now replaced with `<redacted>` before serialisation; header/cookie KEYS
  are preserved so the audit trail still records which credentials were
  configured for the run. Reported by `/cyberref` review of v0.4.3.
- **HIGH (security)** — Credential leak via dry-run argv echo
  (`runner.py`). `Authorization:` and `Cookie:` header values in
  `plan.command` are now masked by `redact_command_for_log()` before being
  printed to stdout or written to `runs/<UTC>/logs/<stage>.stdout.log`.
  Handles both the `-H` per-element form (httpx, katana, nuclei, ffuf,
  feroxbuster, dirsearch) and the arjun `--headers` newline-joined form.
  Reported by `/cyberref` review of v0.4.3.

### Added
- `REDACTED_PLACEHOLDER` constant in `bbwebscan.config` and
  `REDACT_PLACEHOLDER` in `bbwebscan.runner` (`<redacted>` in both).
- `redact_command_for_log(command: list[str]) -> list[str]` helper in
  `bbwebscan.runner` for argv masking.

## [0.4.3] — 2026-05-09

### Added
- `bbwebscan --version` flag at the root parser; prints `bbwebscan X.Y.Z` and
  exits 0. `__version__` is now read from `importlib.metadata` so pyproject is
  the single source of truth.
- `bbwebscan history` subcommand listing past runs newest-first with a fixed-
  column table; supports `--limit` and `--runs-dir`.
- `bbwebscan show <run>` prints a past run's `summary.md`; raises a clean error
  when the path lacks a summary.
- `bbwebscan compare <run-A> <run-B>` diffs `findings.json` between two runs;
  identity is the tuple `(stage, kind, target, title)`. Output sections:
  added, removed, unchanged, plus per-severity counts.
- `bbwebscan scan --severity {info,low,medium,high,critical}` filters findings
  below the threshold before write. Summary line gains a per-severity
  breakdown. New exit code `3` when threshold-meeting findings exist (CI gate).
- `bbwebscan scan --check-dns` resolves each target host via
  `socket.gethostbyname` before scanning; unresolvable hosts emit a non-fatal
  `Note: <host> did not resolve via DNS` in the summary.
- Profile auth env-var interpolation: `auth.headers` and `auth.cookies` may
  reference `${ENV_VAR}` placeholders; missing vars raise an actionable
  `ValueError` naming the variable. Scoped to auth only — `${HOME}` in
  `wordlist:` is left literal.
- `[project.optional-dependencies] cov = ["pytest-cov>=5.0"]` and a `fail_under
  = 85` coverage gate.
- New `RunSummary` Pydantic model and `bbwebscan/history.py` module.
- `CHANGELOG.md` (this file).

### Changed
- `bbwebscan/__init__.py` now resolves `__version__` dynamically from
  `importlib.metadata.version("bbwebscan")`; falls back to `"0.0.0+local"`
  when called before `pip install -e .`.
- `pipeline.execute_scan` filters findings against `min_severity` before
  writing `findings.json` and the summary; closing summary now includes the
  severity breakdown when findings exist.

## [0.4.2] — 2026-05-09

### Added
- `bbwebscan install --quiet` filters cargo/pip compile spam; keeps `[*]`,
  `[!]`, `[+]`, `[dry-run]`, warning, and error lines.
- Closing summary on every scan: `[bbwebscan] scan complete — N findings,
  A/T scope decisions allowed` plus `[bbwebscan] artifacts: <path>`.
- Init profiles include a guidance comment block hinting at how to enable
  aggressive recon (`enabled_tools: [ffuf, feroxbuster, arjun, nuclei]` +
  `--mode aggressive --ack-authorized`).
- README "Install for system-wide use" section with `pipx install -e .`
  recipe so `bbwebscan` is discoverable outside the venv.

### Changed
- `--ack-authorized` is silently accepted on every subcommand
  (`install`/`doctor`/`init`) as a documented no-op, so muscle-memory across
  subcommands no longer hits a confusing argparse error.

### Fixed
- `persist_path_in_shell_rc` now recognises the bash installer's
  `# [FIX-BBR-02] bug bounty web recon tool PATH` marker as equivalent to its
  own `# [bbwebscan]`. A user running both `bbwebscan install` and
  `bbwebscan doctor --fix-path` no longer ends up with duplicate PATH-export
  blocks in `~/.zshrc`.
- Scans no longer end silently — operator no longer needs to `cd runs/` to
  find artifacts.

## [0.4.1] — 2026-05-08

### Added
- Path-gap detection in `preflight.inventory_tools`: scans `~/go/bin`,
  `~/.cargo/bin`, `~/.local/bin` so binaries installed via `go install` /
  `cargo install` aren't reported missing just because they're not on PATH
  yet — they show up as `⚠ on-disk` with a remediation hint.
- `ToolStatus.path_gap` and `ToolStatus.shadowed_by` fields.
- `bbwebscan doctor --fix-path` idempotently *prepends* the recon bin dirs
  to the user's shell rc (zsh/bash, marker-guarded) so PD's `httpx` wins
  over `/usr/bin/httpx` Python shims.
- `[FIX-BBW-D]` constants and helpers: `_WELL_KNOWN_BIN_DIRS`,
  `_resolve_tool_path`, `WELL_KNOWN_BIN_DIRS`, `PERSIST_MARKER`,
  `persist_path_in_shell_rc()`.

### Changed
- `bbwebscan install` now passes `--persist-path` to the bash installer by
  default (use `--no-persist-path` to opt out).
- Doctor classifier returns `("⚠", "on-disk")` and `("⚠", "shadowed")` in
  addition to `✓ found`, `✗ missing`, `? suspect`.

## [0.4.0] — 2026-05-08

### Added
- CLI subcommand structure: `bbwebscan {scan,install,doctor,init}` (default
  `scan` for back-compat).
- `bbwebscan install` wraps `~/bbScan_Installer.sh`; `bbwebscan doctor`
  reports per-tool readiness with install hints; `bbwebscan init <name>`
  scaffolds a profile YAML.
- Smart-default positional: `bbwebscan example.com` derives
  `allowed_hosts=[example.com]` and runs a safe scan profile-less.
- No-args `bbwebscan` shows a welcome panel with live toolchain summary.
- `--quiet/-q` suppresses per-stage progress output (verbose default).
- Profile-supplied tool fingerprints via `ProgramProfile.tool_identity`.
- `--strict-identity` flag promotes suspect tools to a hard error.
- Optional `[psl]` extra integrating `publicsuffix2` for full TLD coverage.

## [0.3.0] — 2026-05-08

### Added
- Tool identity fingerprinting (`TOOL_IDENTITY` regex map, `ToolStatus.identity`,
  `[SUSPECT]` markers in summary). Adversarial test ensures fake binaries
  sharing a tool name don't pass.
- Dirsearch `--help` drift guard (test skips if dirsearch missing).
- `[FIX-BBW-07]` short-circuit in `filter_urls_in_scope` via `already_decided`.
- "Allowed/Rejected scope decisions" wording in summary (was "targets").

### Fixed
- Cumulative-URL bug in `discovery_stage.parse_results` — findings now match
  the artifact they came from.
- JSONL parsers (`httpx`/`katana`/`nuclei`) tolerate malformed and empty lines.
- Subprocess `TimeoutExpired` and `OSError` no longer crash the pipeline;
  return a failed `ExecutionResult` for retry.
- Split `tool_timeout_s` from `command_wall_clock_s` (was one value used
  ambiguously).
- httpx stage now passes `build_header_args` so authenticated endpoints work.
- `wfuzz`/`gobuster` removed from default toolset (broken syntax / non-JSON
  output); kept as opt-ins.
- `feroxbuster` JSONL parsed via `load_json_or_jsonl`.

## [0.0.1] — 2026-05-08

### Added
- Initial release. Pipeline `httpx → katana → discovery (ffuf/feroxbuster/
  dirsearch) → params (arjun) → nuclei`. Pydantic v2 strict models, retry
  policy, scope-aware target filtering, JSONL-tolerant parsing.
- CLI with profile YAML, `--mode {safe,aggressive}` (aggressive requires
  `--ack-authorized`), `--dry-run`, `--check-tools`.
- Public-suffix denylist guard against bare-TLD targets.
