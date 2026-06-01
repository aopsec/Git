# AskMaps "Personalization" Evaluator Agent
<!-- [INIT-ASKMAPSEVAL-01] Codex/agent guidance for the AskMaps evaluator project. -->

## Project Purpose & Role

This project implements a Python evaluation agent that assists a human rater in
completing the Welocalize AskMaps "Personalization" Task. The agent automates data
collection, enforces rating constraints, validates feedback quality, and populates
the Feedback Sheet according to the official weekly guidelines.

**Source of truth**: `Vault/References/Ara Mu - Introduction to the AskMaps "Personalization" Task.md`

The agent evaluates Google Maps' "Full Personalization" feature by:

1. Running assigned and custom search queries on Google Maps (desktop, Chrome).
2. Capturing screenshots of the map results.
3. Rating the personalized results for helpfulness (scale 1–5).
4. Optionally comparing Personalized vs Non-Personalized results (Side-by-Side).
5. Flagging issues from the official issue list with written justifications.
6. Writing quality evaluation comments that meet project standards.
7. Submitting all data in the Feedback Sheet in the required shared format.

---

## Module Layout

```
Projects/askmaps-eval/
├── AGENTS.md              # This file — Codex guidance
├── models.py              # All dataclasses and enums
├── rating_engine.py       # suggest_helpfulness_rating() + detect_issues()
├── validator.py           # validate_helpfulness_comment()
├── workflow.py            # Step-by-step task runner; enforces AGENT_RULES
├── feedback_sheet.py      # Read/write Feedback Sheet (Google Sheets API or CSV)
├── agent.py               # Orchestrator entry point
└── tests/
    ├── test_models.py
    ├── test_rating_engine.py
    ├── test_validator.py
    └── test_workflow.py
```

---

## Data Model

All enums and dataclasses live in `models.py`. No magic strings anywhere — always
use the enums.

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import IntEnum, Enum


class HelpfulnessRating(IntEnum):
    NOT_HELPFUL       = 1  # Fails primary intent; significant issues; inappropriate
    SOMEWHAT_HELPFUL  = 2  # Partially addresses intent; lacks useful details
    MOSTLY_HELPFUL    = 3  # Addresses intent; may include minor inaccuracies
    VERY_HELPFUL      = 4  # Addresses intent well; leads with key info
    EXTREMELY_HELPFUL = 5  # Optimal structure; no unnecessary content; hard to improve


class SxSWinner(str, Enum):
    PERSONALIZATION     = "Personalization"
    NON_PERSONALIZATION = "Non-Personalization"
    ABOUT_THE_SAME      = "Both were about the same"


class IssueFlag(str, Enum):
    LATENCY                         = "Latency (> 20 sec)"
    BAD_INTRODUCTION                = "Bad Introduction"
    TOO_MUCH_FOCUS_ON_CUISINE       = "Too Much Focus on Cuisine"
    ROBOTIC_AWKWARD_PERSONALIZATION = "Robotic/Awkward Personalization"
    BAD_PLACE_SUGGESTIONS           = "Bad Place Suggestions"
    IGNORED_INSTRUCTIONS            = "Ignored Instructions or Query Content"
    MISSED_PERSONALIZATION          = "Missed Personalization Opportunity"
    WRONG_ASSUMPTION                = "Wrong Assumption"
    CREEPY_INTRUSIVE_TONE           = "Creepy or Intrusive Tone"
    IGNORED_PERSONAL_RELATIONSHIP   = "Ignored Personal Relationship to a Place"
    MISSING_INFORMATION             = "Missing Information"
    BAD_FORMATTING                  = "Bad Formatting & Other Usability Issues"


@dataclass
class FeedbackRow:
    query: str
    response_screenshots: list[str]       # one file path per slot; max 4 if 6 available
    helpfulness_rating: HelpfulnessRating
    helpfulness_comment: str              # must cite query, result, map elements, guideline
    issues: list[IssueFlag] = field(default_factory=list)
    issue_explanations: dict[IssueFlag, str] = field(default_factory=dict)  # required per flag
    other_issues: Optional[str] = None

    # Side-by-Side fields — populated only when task requires SxS
    response_non_personalized: Optional[list[str]] = None  # personalization OFF
    response_personalized: Optional[list[str]] = None      # personalization ON
    sxs_winner: Optional[SxSWinner] = None
    sxs_comment: Optional[str] = None    # best practice: always explain reasoning
    other_comments: Optional[str] = None
```

---

## Core Logic Contracts

### `rating_engine.py`

```python
def suggest_helpfulness_rating(
    query: str,
    result_summary: str,
) -> HelpfulnessRating:
    """
    Proposes a helpfulness rating. Human rater always overrides.
    Always defer to the current Weekly Guidelines Table — criteria change weekly.
    Do NOT rely on memory from previous tasks.

    Rating 1 — NOT_HELPFUL: any of:
        - Fails to satisfy primary user intent
        - Contains significant errors or inappropriate content
        - Unnatural language/structure making it useless

    Rating 2 — SOMEWHAT_HELPFUL: any of:
        - Only partially addresses intent
        - Significant extra/irrelevant information
        - Lacks useful details; may be slightly inaccurate

    Rating 3 — MOSTLY_HELPFUL: all of:
        - Addresses primary intent
        - Structured for easy understanding
        - May include some unnecessary detail or minor inaccuracies

    Rating 4 — VERY_HELPFUL: all of:
        - Addresses primary intent well
        - Very easy to identify main points; leads with most important info
        - Comparable to a talented, well-informed human response

    Rating 5 — EXTREMELY_HELPFUL: all of:
        - Addresses primary intent exceptionally well
        - Optimal structure; no repetitive or unnecessary content
        - Hard to imagine a better response
    """
    ...


def detect_issues(
    query: str,
    result_summary: str,
    user_profile_summary: str,
) -> dict[IssueFlag, str]:
    """
    Scans a Maps result for each of the 12 official issue types.
    Returns {IssueFlag: explanation} for every issue found.
    Explanation must state WHY it qualifies, not just that it does.

    LATENCY                         → Response took > 20 seconds
    BAD_INTRODUCTION                → Intro text is awkward, verbose, or adds no value
    TOO_MUCH_FOCUS_ON_CUISINE       → Food-type personalization overrides env/service constraints
    ROBOTIC_AWKWARD_PERSONALIZATION → Preference mentions feel clunky / uncanny valley
    BAD_PLACE_SUGGESTIONS           → Places returned are not places this user would visit
    IGNORED_INSTRUCTIONS            → Explicit constraints (open now, under $X, distance) bypassed
    MISSED_PERSONALIZATION          → Generic result when user history could have improved it
    WRONG_ASSUMPTION                → Recommendation built on a weak single-signal inference
    CREEPY_INTRUSIVE_TONE           → Personal data referenced in a socially inappropriate way
    IGNORED_PERSONAL_RELATIONSHIP   → Frequented/saved place treated as if new to the user
    MISSING_INFORMATION             → Deal-breaker detail (dog-friendly, hours, accessibility) omitted
    BAD_FORMATTING                  → Text bunched together; non-functional links; usability failures

    Caller is responsible for merging other_issues into FeedbackRow for anything
    outside this list.
    """
    ...
```

### `validator.py`

```python
def validate_helpfulness_comment(comment: str, query: str) -> list[str]:
    """
    Returns a list of quality warnings. Empty list = comment passes.

    A valid comment must contain all four elements:
        1. RELATION_TO_QUERY   — how results addressed the specific search intent
        2. MAPS_RESULT         — actual content/businesses in the response
        3. SPECIFIC_ELEMENTS   — exact details: categories, distance, hours, reviews
        4. GUIDELINE_ALIGNMENT — reasoning explicitly linked to Weekly Helpfulness Table

    Reject patterns (generic "stock" answers):
        - "The suggestions were helpful."
        - "Results were mostly relevant."
        - Any comment without reference to a specific map element
    """
    warnings: list[str] = []
    ...
    return warnings
```

---

## 10-Step Task Workflow

Defined in `workflow.py`. The agent guides the rater through this exact sequence:

```python
WORKFLOW_STEPS: list[tuple[int, str, str]] = [
    (1,  "Review Project Instructions",
         "Check email for this week's project instructions and updated guidelines PDF."),
    (2,  "Share Feedback Sheet",
         "Create a copy and grant EDITOR access to all required Welocalize/Google contacts."),
    (3,  "Register Sheet Link",
         "Paste the sheet link into the Google Form provided in the instructions email."),
    (4,  "Execute Personalized Queries",
         "Run all queries. Replace [city], [neighborhood], etc. with real personal values."),
    (5,  "Embed Compliant Screenshots",
         "Insert screenshots directly into cells (no floating). "
         "If 6 images exist but only 4 slots: keep the 4 most relevant. "
         "NEVER add new rows or columns."),
    (6,  "Evaluate Helpfulness",
         "Assign rating 1-5 and write a 4-element comment per the Weekly Guidelines Table."),
    (7,  "Perform SxS Rating (when prompted)",
         "Compare Personalized vs Non-Personalized results and select: "
         "Personalization | Non-Personalization | Both were about the same."),
    (8,  "Identify and Log Issues",
         "Flag all detected issues from the official 12-flag list with written explanations."),
    (9,  "Identify Unlisted Issues",
         "Document any relevant problems not covered by the official issue dropdown."),
    (10, "Final Submission",
         "Submit on time in the original shared format. "
         "Pro tip: maintain a steady pace — do not wait for the deadline."),
]
```

---

## Agent Constraints & Rules

Defined in `workflow.py` as `AGENT_RULES`. Enforced at every step.

```python
AGENT_RULES: list[str] = [
    # Guidelines are versioned weekly — never hardcode criteria
    "Always follow the link in each column header to load the current week's rating criteria.",
    "Never rely on memory from a previous project week — criteria may have been updated.",

    # Screenshot rules
    "Each screenshot must be in its own column — never stack multiple results in one cell.",
    "If more images exist than slots, select the most relevant ones to fill available slots.",
    "Screenshots must be embedded directly into cells, not floating over them.",

    # Query personalisation
    "Replace all bracketed placeholders (e.g. [city]) with real personal values before executing.",
    "If a query doesn't apply personally, modify it slightly to be relevant — always answer every query.",

    # Comment quality
    "Never submit generic stock comments — every comment must cite specific map elements.",
    "For every IssueFlag set, a written explanation is mandatory.",

    # Submission integrity
    "Never add new rows or columns to the Feedback Sheet.",
    "Submit the sheet in its original shared format with editing permissions intact.",
]
```

---

## Required Contacts

Defined in `feedback_sheet.py`. Grant **Editor** access to all before Step 3.

```python
REQUIRED_SHARE_CONTACTS: list[str] = [
    "askmaps-eval-submissions@google.com",
    "manuelalejandro.flor@welocalize.com",
    "brenden.clawson@welocalize.com",
    "mirshabber.alikhan@welocalize.com",
    "saba.fatima@welocalize.com",
    "ioanna.kyrmanidou@welocalize.com",
    "brandon.winter@welocalize.com",
    "audrey.tung@welocalize.com",
]
SHARE_PERMISSION = "Editor"
```

---

## Build, Test & Development Commands

Run from `Projects/askmaps-eval/`.

```bash
# Install dependencies
pip install -e '.[dev]'

# Lint + type check
ruff check .
mypy --strict .

# Full test suite
pytest -q

# Single test
pytest tests/test_rating_engine.py::TestSuggestHelpfulness::test_name -v
```

Stack: **Python 3.12+**, **Pydantic v2** for model validation, **pytest** for tests.

---

## Coding Style & Conventions

- Every public function must have a complete type signature.
- No magic strings — always use `HelpfulnessRating`, `SxSWinner`, `IssueFlag` enums.
- `suggest_helpfulness_rating()` must never block — it proposes; the human decides.
- `validate_helpfulness_comment()` returns a list of warnings, never raises.
- Weekly guidelines are fetched at runtime from the column header link; never hardcoded.

---

## Commit Guidelines

Use the scoped prefix `projects/askmaps-eval:` for all commits in this folder.

```
projects/askmaps-eval: add models — HelpfulnessRating, IssueFlag, FeedbackRow
projects/askmaps-eval: implement rating_engine stubs with docstring contracts
projects/askmaps-eval: add validator — 4-element comment quality check
```
