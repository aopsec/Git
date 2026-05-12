# bbWebScan

Scope-aware bug bounty web recon orchestrator. Successor to `~/bbscan/` with hardened
parsing, split timeout semantics, per-stage retry/backoff, and a stricter scope gate.

## Status

`v0.5.2` — menu hardening patch. Main-menu handlers now catch user-facing
errors (`FileNotFoundError`, `FileExistsError`, `ValueError`, `OSError`),
print `[bbwebscan menu] <error>`, and return to the menu instead of crashing.
Save Profile no longer persists raw-request file paths; those remain one-off
run inputs only. `bbwebscan` with no args and
`bbwebscan menu` now open a Rich-backed numbered menu for scan setup,
doctor/auto-fix, install, profile init/save, history, show, and compare.
Existing direct CLI commands remain valid. The Scan Wizard previews the
equivalent command, can dry-run before execution, and preserves the existing
`--ack-authorized` gates for aggressive scans and active/intel amass modes.
Saved profile auth uses env-var references only; one-off header/cookie/raw
request inputs are not written as plaintext profile secrets.

`v0.5.0` — vault-attested web tools added under cyberref discipline:
**`amass`** subdomain enumeration runs before httpx when
`--enumerate-subdomains` is set (modes: passive default; active/intel
require `--ack-authorized`). **`kiterunner`** API route discovery runs
alongside `ffuf` in the discovery stage when `--api-discovery` is set.
Each amass FQDN passes through `enforce_scope_gate` before reaching
downstream stages, so wide-net subdomain enumeration stays inside the
operator-declared scope. Vault citations recorded per tool in CHANGELOG.

`v0.4.4` — security fixes from the v0.4.3 `/cyberref` review: `runs/<UTC>/run_config.json`
no longer persists resolved `auth.headers` / `auth.cookies` values (keys preserved,
values become `<redacted>`); dry-run argv echo masks `Authorization:` / `Cookie:`
header values before print + write. Both fixes ship without backward-incompatible
changes; existing tests still pass.

`v0.4.3` — engineering polish + operator QoL: `bbwebscan --version`;
`CHANGELOG.md` (Keep-a-Changelog format, backfilled to 0.0.1); new
subcommands `bbwebscan history` (list past runs), `bbwebscan show <run>`
(reprint a past summary.md), `bbwebscan compare <A> <B>` (diff findings
between runs); `bbwebscan scan --severity {info,low,medium,high,critical}`
filters findings + introduces exit code `3` for CI gating, with severity
breakdown in the closing summary; `bbwebscan scan --check-dns` non-fatally
notes unresolvable hosts; profile YAMLs support `${ENV_VAR}` interpolation
in `auth.headers` / `auth.cookies` only (missing var → actionable error);
new `[cov]` extra plus an 85% coverage gate enforced via
`[tool.coverage.report] fail_under`. Aggressive mode still requires
`--ack-authorized`. Run only on in-scope targets you are authorized to test.

## Quick start

```bash
cd Projects/bbWebScan
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,cov]'               # installs rich menu + dev/test tooling
pytest -q --cov                            # ≥ 85% line coverage required (gate enforced)
bbwebscan                                 # interactive menu console
bbwebscan menu                            # same menu, explicit subcommand
bbwebscan doctor                          # what's missing? exit 2 if anything is
bbwebscan install --dry-run               # preview installer commands
bbwebscan install                         # actually install (uses ~/bbScan_Installer.sh)
bbwebscan example.com --dry-run           # smart-default scan against one host
bbwebscan init bbp-acme --target app.acme.com  # scaffold profiles/bbp-acme.yaml
bbwebscan scan --profile profiles/bbp-acme.yaml
```

### Install for system-wide use (optional)

```bash
pipx install -e .
```

`pipx` puts a `bbwebscan` shim in `~/.local/bin/` (already on `$PATH` after
`bbwebscan install`) so the command works from any shell without activating
the venv. Update with `pipx upgrade bbwebscan`. Without pipx, `bbwebscan` is
only available inside the activated `.venv` — that's expected.

## Subcommands

```text
bbwebscan {menu,scan,install,doctor,init,history,show,compare} [...]
   menu      Open the Python terminal menu (also the no-args default)
   scan      Run a recon scan
   install   Install missing recon tools via ~/bbScan_Installer.sh
   doctor    Inspect toolchain readiness, print install hints
   init      Scaffold a program profile YAML
   history   List past runs newest-first
   show      Print a past run's summary.md
   compare   Diff findings between two past runs
```

`bbwebscan scan` flags:

```text
--profile FILE              YAML program profile
--target HOST               Repeatable; appended to profile.seed_urls
--input FILE                Newline-delimited target file
--mode {safe,aggressive}    Aggressive needs --ack-authorized
--ack-authorized            Required for aggressive mode
--header H, --cookie C      Auth: -H/--cookie, repeatable
--raw-request FILE          ffuf/dirsearch raw request body
--output-dir DIR            Default: runs/<UTC>
--enable-tool, --disable-tool   Toggle individual stages
--threads N, --rate N
--tool-timeout SECONDS      Per-tool flag (httpx -timeout, etc). Default 15.
--cmd-timeout SECONDS       Wall-clock subprocess timeout. Default 900.
--max-attempts N            Retry attempts on transient failure. Default 1.
--backoff-s SECONDS         Backoff base for retry. Default 2.0.
--check-tools               Inventory only, no scans
--dry-run                   Print commands; write logs but skip exec
--quiet, -q                 Suppress per-stage progress output
--strict-identity           Fail validate_environment if any tool fingerprint is suspect
```

## Auth credentials in profiles

Profile YAMLs sometimes live in dotfiles or shared repos. Keep secrets out of
the file by referencing environment variables in `auth.headers` and
`auth.cookies`:

```yaml
auth:
  headers:
    Authorization: "Bearer ${BBP_TOKEN}"
  cookies:
    session: "${BBP_SESSION}"
```

Export the env vars before running: `export BBP_TOKEN=... BBP_SESSION=...`.
Missing vars raise an actionable error naming the variable; bbwebscan never
silently substitutes empty. Interpolation is scoped to `auth.headers` and
`auth.cookies` only — `${HOME}`-style references in path fields like
`wordlist:` pass through verbatim.

The menu follows the same rule. Temporary wizard headers/cookies/raw requests
can be used for one-off runs, but the Save Profile action writes only auth
values that contain env-var references such as `${BBW_TOKEN}`.

## Menu console

`bbwebscan` and `bbwebscan menu` open the v0.5.2 menu:

- Scan Wizard: prompts for targets/input file, profile, mode, authorization,
  tool toggles, amass/API discovery, one-off auth, wordlist, tuning, severity,
  DNS precheck, output directory, and dry-run preference.
- Scan Action Menu: preview equivalent command, dry-run, run scan, save
  profile, edit settings, or return to the main menu.
- Doctor / Auto Fix Tools: inventories tools first, shows a table, then asks
  once before calling existing `doctor --fix-path` and `install` helpers.
- History, Show Run, and Compare Runs call the existing run-inspection code.

## Scope gate

`bbwebscan` refuses to run when:

- `mode=aggressive` without `--ack-authorized`
- `allowed_hosts` is empty AND target inputs span more than one host
- a target normalises to a bare public-suffix TLD (e.g. `com`, `co.uk`)

Profile `denied_hosts` always wins over `allowed_hosts`.

## Stages

`httpx` → `katana` → `discovery` (ffuf, feroxbuster, dirsearch) → `params` (arjun) →
`nuclei`. Each stage builds `CommandPlan`s; `runner.run_plan` streams stdout/stderr to
log files, applies wall-clock timeout, retries on transient exit codes per
`RetryPolicy`. Parsers are JSONL-tolerant: malformed/empty lines are skipped, never
fatal.

## Layout

- `bbwebscan/` — package modules.
- `bbwebscan/stages/` — one file per recon tool group.
- `profiles/example.yaml` — template program profile.
- `tests/fixtures/` — realistic JSONL/JSON outputs used by parser tests.
- `vault/` — Obsidian generated catalog (managed by `obsidian_agent_cli.py`).
