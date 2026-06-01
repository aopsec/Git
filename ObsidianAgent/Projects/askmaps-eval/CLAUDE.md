# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project State

This project is **spec-only** — `AGENTS.md` contains the full architecture contract and function stubs, but no implementation files exist yet. When starting work, implement the 6 modules defined there in order: `models.py` → `rating_engine.py` → `validator.py` → `workflow.py` → `feedback_sheet.py` → `agent.py`.

**Source of truth for domain rules**: `Vault/References/Ara Mu - Introduction to the AskMaps "Personalization" Task.md` (relative to `ObsidianAgent/` root). All rating criteria, issue definitions, and workflow steps derive from that document.

## Commands

Run from `Projects/askmaps-eval/`.

```bash
pip install -e '.[dev]'     # first-time setup

ruff check .                # lint
mypy --strict .             # type check
pytest -q                   # full suite

pytest tests/test_rating_engine.py::TestClass::test_name -v   # single test
```

## Architecture

The agent is a **human-in-the-loop tool**, not autonomous. It proposes ratings and surfaces warnings; the human rater always has final say. This shapes every design decision:

- `rating_engine.suggest_helpfulness_rating()` — proposes only, never commits
- `validator.validate_helpfulness_comment()` — returns warnings, never raises or blocks
- `workflow.py` — step runner that pauses for human confirmation at each of the 10 steps

**Data flow**: `agent.py` (orchestrator) → loads weekly guidelines at runtime → drives `workflow.py` steps → calls `rating_engine` + `validator` → writes results to `feedback_sheet.py`.

The weekly guidelines URL is embedded in the Feedback Sheet column headers and **must be fetched at runtime**. Never hardcode rating criteria — they change per project week.

## Key Domain Rules

- `IssueFlag` and `HelpfulnessRating` are the only valid values for their columns — no raw strings.
- Every `IssueFlag` set on a `FeedbackRow` requires a corresponding entry in `issue_explanations`.
- Screenshots embed directly into cells (not floating); if more images exist than slots, keep the most relevant ones.
- Bracketed placeholders like `[city]` in queries must be replaced with real personal values before execution.
- `FeedbackRow.response_screenshots` max 4 entries when only 4 slots exist in the sheet.
- Never add rows or columns to the Feedback Sheet.

## Gotchas

- `suggest_helpfulness_rating()` signature takes `query` + `result_summary` only — **not** a `FeedbackRow`. It must be stateless and fast (no I/O).
- `detect_issues()` takes a third arg `user_profile_summary` because several issue types (e.g. `MISSED_PERSONALIZATION`, `IGNORED_PERSONAL_RELATIONSHIP`, `WRONG_ASSUMPTION`) require knowing the user's history to evaluate correctly.
- `SxS` fields on `FeedbackRow` are `Optional` and only populated when the task week requires side-by-side comparison. Do not default-fill them.
- The `REQUIRED_SHARE_CONTACTS` list (8 addresses) lives in `feedback_sheet.py` and must be granted **Editor** access before Step 3 of the workflow — failure to do so means the submission is not considered.

## Commit Prefix

`projects/askmaps-eval:` — e.g. `projects/askmaps-eval: implement models`
