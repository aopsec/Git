#!/usr/bin/env bash
# [VALIDATE] End-to-end sanity check for the Codex+Claude+Obsidian stack.
# Non-destructive. Exits 0 on all-green, 1 on any failed assertion.
set -euo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'

PASS=0
FAIL=0
ok()   { printf '  [ok]   %s\n' "$1"; PASS=$((PASS+1)); }
nok()  { printf '  [FAIL] %s\n' "$1" >&2; FAIL=$((FAIL+1)); }
warn() { printf '  [warn] %s\n' "$1"; }

check_true() {
    local msg=$1; shift
    if "$@"; then ok "$msg"; else nok "$msg"; fi
}

assert_file() {
    if [[ -f "$1" ]]; then ok "file: $1"; else nok "missing file: $1"; fi
}

assert_dir() {
    if [[ -d "$1" ]]; then ok "dir: $1"; else nok "missing dir: $1"; fi
}

assert_exec() {
    if [[ -x "$1" ]]; then ok "exec: $1"; else nok "not executable: $1"; fi
}

assert_dir_mode() {
    local p=$1 want=$2
    if [[ ! -d "$p" ]]; then nok "missing dir: $p"; return; fi
    local got; got=$(stat -c %a "$p")
    if [[ "$got" == "$want" ]]; then ok "dir $p mode=$got"; else nok "dir $p mode=$got (want $want)"; fi
}

has_cmd() { command -v "$1" >/dev/null 2>&1; }

section() { printf '\n== %s ==\n' "$1"; }

section "1. CPR skills installed"
for cmd in preserve compress resume collab; do
    assert_file "$HOME/.claude/commands/$cmd.md"
done

section "2. Claude settings: autoCompact=false, PreCompact hook wired"
if has_cmd jq; then
    ac=$(jq -r '.autoCompact' "$HOME/.claude/settings.json")
    if [[ "$ac" == "false" ]]; then ok "autoCompact=false"; else nok "autoCompact not false (got: ${ac:-unset})"; fi
    pc=$(jq -r '.hooks.PreCompact[0].hooks[0].command // empty' "$HOME/.claude/settings.json")
    if [[ "$pc" == *"pre_compact_guard.py" ]]; then ok "PreCompact hook wired"; else nok "PreCompact hook missing (got: ${pc:-unset})"; fi
else
    warn "jq missing — skipping settings inspection"
fi

section "3. Redactor present, executable, and scrubs"
assert_exec "$HOME/plugins/aops-agent/cpr/redact.py"
probe_out=$(printf 'ghp_0123456789abcdefghijklmnopqrstuvwxAB\n' \
    | python3 "$HOME/plugins/aops-agent/cpr/redact.py" 2>/dev/null)
if [[ "$probe_out" == *"[REDACTED:GH_TOKEN]"* ]]; then
    ok "redactor scrubs gh token"
else
    nok "redactor did not scrub gh token"
fi

section "4. PreCompact hook script"
assert_exec "$HOME/plugins/aops-agent/cpr/hooks/pre_compact_guard.py"

section "5. Codex bridge + gates"
assert_exec "$HOME/plugins/aops-agent/cpr/bin/codex-bridge.sh"
assert_exec "$HOME/plugins/aops-agent/gates/preflight.sh"
assert_exec "$HOME/plugins/aops-agent/gates/postrun.sh"
if has_cmd codex;    then ok "codex on PATH";    else nok "codex missing"; fi
if has_cmd gitleaks; then ok "gitleaks on PATH"; else warn "gitleaks missing (optional)"; fi
if has_cmd semgrep;  then ok "semgrep on PATH";  else warn "semgrep missing (optional)"; fi

section "6. Obsidian layout + vault contract"
assert_dir_mode "$HOME/ObsidianAgent/SessionLogs" "700"
assert_dir     "$HOME/ObsidianAgent/Vault/Journal/Daily"
if [[ -f "$HOME/ObsidianAgent/Vault/Journal/Daily/$(date +%F).md" ]]; then
    ok "today daily note present"
else
    # [FIX-AUDIT-COLLAB] Daily notes are manual, so missing today's file is informational.
    warn "today daily note absent (manual note)"
fi
assert_file    "$HOME/ObsidianAgent/.aops-vault.toml"
if grep -q 'title_mode = "session-log"' "$HOME/ObsidianAgent/.aops-vault.toml"; then
    ok "vault contract has session-log catalog"
else
    nok "vault contract missing session-log catalog"
fi
if grep -q 'title_mode = "daily"' "$HOME/ObsidianAgent/.aops-vault.toml"; then
    ok "vault contract has daily catalog"
else
    nok "vault contract missing daily catalog"
fi

section "7. Obsidian client sanity (FS fallback path)"
assert_exec "$HOME/plugins/aops-agent/obsidian-api/client.py"

section "8. Systemd --user units present"
for u in obsidian-agent-sync.service obsidian-agent-sync.timer \
         sessionlogs-gitleaks.service sessionlogs-gitleaks.timer; do
    assert_file "$HOME/plugins/aops-agent/automation/systemd/$u"
done

section "summary"
printf 'pass=%d  fail=%d\n' "$PASS" "$FAIL"
(( FAIL == 0 ))
