#!/usr/bin/env bash
# ObsidianAgent smoke driver — run from ObsidianAgent/ root.
# Usage: bash .claude/skills/run-obsidian-agent/smoke.sh [check|sync|test|cyber-dry|all]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CLI="${AOPS_OBSIDIAN_AGENT_CLI:-$HOME/plugins/aops-agent/obsidian-agent/obsidian_agent_cli.py}"
CMD="${1:-all}"

run_check() {
    echo "=== obsidian-agent --check ==="
    python3 "$CLI" --check --repo "$REPO_ROOT" && echo "[ok] vault up-to-date" || true
}

run_sync() {
    echo "=== obsidian-agent --sync ==="
    python3 "$CLI" --sync --repo "$REPO_ROOT" && echo "[ok] sync complete" \
        || echo "[warn] sync refused — orphan files detected (see --check output)"
}

run_tests() {
    echo "=== pytest (CyberPDF extractor) ==="
    pytest -q "$REPO_ROOT/tests/test_cyber_pdf_ref.py"
}

run_cyber_dry() {
    echo "=== CyberPDF extractor --dry-run ==="
    python3 "$REPO_ROOT/tools/extract_cyber_pdf_reference.py" \
        --pdf-list "$REPO_ROOT/tools/cyber_pdf_ref/b00ks_sources.txt" \
        --repo "$REPO_ROOT" --dry-run
}

run_collab_stack() {
    echo "=== validate-collab-stack.sh ==="
    bash "$REPO_ROOT/tests/validate-collab-stack.sh" || true
}

case "$CMD" in
    check)      run_check ;;
    sync)       run_check; run_sync ;;
    test)       run_tests ;;
    cyber-dry)  run_cyber_dry ;;
    stack)      run_collab_stack ;;
    all)
        run_check
        run_tests
        run_cyber_dry
        echo ""
        echo "=== done — run 'sync' to regenerate vault notes ==="
        ;;
    *)
        echo "Usage: $0 [check|sync|test|cyber-dry|stack|all]" >&2
        exit 1
        ;;
esac
