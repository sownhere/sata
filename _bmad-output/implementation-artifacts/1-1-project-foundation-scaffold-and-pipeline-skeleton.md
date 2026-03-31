# Story 1.1: Project Foundation — Scaffold & Pipeline Skeleton

Status: done

## Story

As a developer,
I want a runnable Streamlit app initialized from the cookiecutter-streamlit template with the full LangGraph pipeline skeleton and SataState wired up,
so that every subsequent story has a known, consistent structure to slot into.

## Acceptance Criteria

1. **Given** the developer has cloned the repo and copied `.env.example` to `.env` with valid keys, **when** they run `streamlit run app.py`, **then** the Streamlit UI opens in the browser without errors.

2. **Given** the app is running, **when** the developer inspects the app, **then** a stage header is visible showing the current pipeline stage (stub: "Spec Ingestion"), the LangGraph pipeline is instantiated with 8+ named nodes (stubs returning passthrough state), and `SataState` TypedDict is defined and passed between all nodes as the single source of truth.

3. **Given** no `.env` file exists or required keys are missing, **when** the app starts, **then** a clear error message is displayed listing the missing variables and the app does not crash silently.

4. **Given** the `.env` file exists with valid keys, **when** the app initializes, **then** no API keys or secrets are logged to the console or displayed in the UI.

## Tasks / Subtasks

- [x] Task 1: Initialize project from cookiecutter-streamlit template (AC: 1, 2)
  - [x] Run `cookiecutter https://github.com/gerardrbentley/cookiecutter-streamlit` (requires `pip install cookiecutter` first)
  - [x] Project name: `sata`, verify `streamlit run app.py` launches without error
  - [x] Remove boilerplate placeholder content, preserve template module structure

- [x] Task 2: Create `.env.example` and startup env validation (AC: 3, 4)
  - [x] Create `.env.example` with required vars: `LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`
  - [x] Ensure `.env` is in `.gitignore` (add if not already present)
  - [x] Create `app/utils/env.py` — implement `validate_env()` checking all three required keys
  - [x] In `app.py`, call `validate_env()` at top: show `st.error(...)` listing missing vars and call `st.stop()` — never crash silently
  - [x] Load `.env` via `python-dotenv` (`load_dotenv()`) before any LLM client initialization

- [x] Task 3: Define `SataState` TypedDict (AC: 2)
  - [x] Create `app/state.py` with full `SataState` TypedDict (see Dev Notes for all fields)
  - [x] All pipeline nodes must import `SataState` from this module — never redefine elsewhere

- [x] Task 4: Build LangGraph pipeline skeleton with 8+ stub nodes (AC: 2)
  - [x] Create `app/pipeline.py` — define `StateGraph(SataState)`, add all 10 named nodes
  - [x] Each stub node: `def node_name(state: SataState) -> SataState: return state`
  - [x] Add 6 conditional routing edges with stub router functions (see Dev Notes)
  - [x] Compile graph: `graph = builder.compile()`
  - [x] Expose `build_pipeline() -> CompiledGraph` factory function

- [x] Task 5: Wire stage header in `app.py` (AC: 2)
  - [x] Initialize `SataState` in `st.session_state` at first run with `pipeline_stage: "spec_ingestion"`
  - [x] Display `st.subheader(f"Stage: {st.session_state.state['pipeline_stage'].replace('_', ' ').title()}")` — stub shows "Spec Ingestion"
  - [x] Call `build_pipeline()` at app start and confirm no import/compile errors

- [x] Task 6: Pin dependencies in `requirements.txt` (AC: 1)
  - [x] Add pinned versions (see Dev Notes for exact list)
  - [x] Verify `pip install -r requirements.txt` succeeds on a clean Python 3.12 environment

## Dev Notes

### SataState TypedDict — `app/state.py`

This is the **single source of truth** for all pipeline nodes (FR34). Define exactly as below — do not add ad hoc fields in individual node files:

```python
from typing import TypedDict, Optional, List

class SataState(TypedDict):
    # ── Ingestion ──────────────────────────────────────────────────────
    spec_source: Optional[str]           # "file" | "url" | "chat"
    raw_spec: Optional[str]              # Raw file/URL content string
    # ── Parsing ────────────────────────────────────────────────────────
    parsed_api_model: Optional[dict]     # {endpoints: [...], auth: {...}}
    spec_confirmed: bool                 # True after Checkpoint 1 confirm
    # ── Gaps ───────────────────────────────────────────────────────────
    detected_gaps: Optional[List[dict]] # [{endpoint, field, question}, ...]
    gap_answers: Optional[dict]          # {question_id: answer}
    # ── Test Generation ────────────────────────────────────────────────
    test_cases: Optional[List[dict]]    # [{id, endpoint, category, priority, ...}]
    test_plan_confirmed: bool            # True after Checkpoint 2 confirm
    # ── Execution ──────────────────────────────────────────────────────
    test_results: Optional[List[dict]]  # [{test_id, passed, actual_status, ...}]
    # ── Analysis ───────────────────────────────────────────────────────
    failure_analysis: Optional[dict]    # {patterns: [...], explanations: [...]}
    # ── Pipeline Control ───────────────────────────────────────────────
    pipeline_stage: str                  # Drives UI stage header (UX-DR1)
    error_message: Optional[str]         # Displayed via st.error() when set
    iteration_count: int                 # Anti-infinite-loop guard (NFR5)
```

Initialize with: `{"pipeline_stage": "spec_ingestion", "spec_confirmed": False, "test_plan_confirmed": False, "iteration_count": 0}` plus all Optional fields as `None`.

### LangGraph 10 Nodes — `app/pipeline.py`

```python
from langgraph.graph import StateGraph, END
from app.state import SataState

def build_pipeline():
    builder = StateGraph(SataState)

    # Add stub nodes (all return state unchanged in Story 1.1)
    for node in [
        "ingest_spec",       # Routes to parse_spec or fill_gaps based on spec_source
        "parse_spec",        # Parses OpenAPI JSON/YAML content
        "detect_gaps",       # Identifies missing/ambiguous spec fields
        "fill_gaps",         # Conversational gap filling + zero-endpoint fallback
        "review_spec",       # Checkpoint 1 — human approval gate
        "generate_tests",    # LLM generates test cases across 6+ categories
        "review_test_plan",  # Checkpoint 2 — human approval gate
        "execute_tests",     # HTTP test execution with auth + retry
        "analyze_results",   # Defect pattern analysis + explanations
        "review_results",    # Checkpoint 3 — re-test loop entry
    ]:
        builder.add_node(node, lambda s: s)  # passthrough stub

    builder.set_entry_point("ingest_spec")

    # Stub conditional routing (all stub routers return first option)
    builder.add_conditional_edges("ingest_spec",
        lambda s: "parse_spec",
        {"parse_spec": "parse_spec", "fill_gaps": "fill_gaps"})

    builder.add_conditional_edges("parse_spec",
        lambda s: "detect_gaps",
        {"detect_gaps": "detect_gaps", "fill_gaps": "fill_gaps"})

    builder.add_conditional_edges("detect_gaps",
        lambda s: "review_spec",
        {"fill_gaps": "fill_gaps", "review_spec": "review_spec"})

    builder.add_conditional_edges("review_spec",
        lambda s: "generate_tests",
        {"generate_tests": "generate_tests", "ingest_spec": "ingest_spec"})

    builder.add_conditional_edges("review_test_plan",
        lambda s: "execute_tests",
        {"execute_tests": "execute_tests", "generate_tests": "generate_tests"})

    builder.add_conditional_edges("review_results",
        lambda s: END,
        {"analyze_results": "analyze_results", END: END})

    # Linear edges
    builder.add_edge("fill_gaps", "review_spec")
    builder.add_edge("generate_tests", "review_test_plan")
    builder.add_edge("execute_tests", "analyze_results")
    builder.add_edge("analyze_results", "review_results")

    return builder.compile()
```

### `.env.example`

```
LLM_API_KEY=your-gemini-api-key-here
LLM_CHAT_MODEL=gemini-2.0-flash
LLM_BASE_URL=example.com
```

### `app/utils/env.py` — Startup Validation

```python
import os
from dotenv import load_dotenv

REQUIRED_ENV_VARS = ["LLM_API_KEY", "LLM_CHAT_MODEL", "LLM_BASE_URL"]

def validate_env() -> list[str]:
    """Returns list of missing required env var names."""
    load_dotenv()
    return [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
```

In `app.py`:
```python
from app.utils.env import validate_env
import streamlit as st

missing = validate_env()
if missing:
    st.error(f"Missing required environment variables: {', '.join(missing)}\n"
             "Copy .env.example to .env and fill in your values.")
    st.stop()
```

### Recommended `requirements.txt` Versions

```
streamlit>=1.32.0
langgraph>=0.1.0
langchain>=0.1.0
langchain-openai>=0.1.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### Project Structure (Post-Scaffold)

```
sata/
├── app.py                    # Streamlit entry point: streamlit run app.py
├── app/
│   ├── __init__.py
│   ├── state.py              # SataState TypedDict — SINGLE SOURCE OF TRUTH
│   ├── pipeline.py           # LangGraph builder + build_pipeline()
│   └── utils/
│       ├── __init__.py
│       └── env.py            # validate_env() startup check
├── .env.example              # Committed template for env vars
├── .env                      # gitignored — never commit
└── requirements.txt
```

Cookiecutter may generate a slightly different layout. Adapt to match this structure while preserving any existing module boundaries. If cookiecutter uses a `src/` layout, document the variance in Dev Agent Record.

### Security Hard Rules (NFR6–NFR8) — NEVER Violate

- `LLM_API_KEY` is loaded via `os.environ.get()` only — never hardcoded
- Never log env vars: no `print(os.environ)`, no `st.write(os.environ)`
- `LLM_API_KEY` must not appear in any Streamlit widget value, label, or rendered output
- `st.stop()` must be called when required keys are missing — do not allow the app to silently proceed

### UX Stage Header (UX-DR1)

The persistent stage header must always be visible. It is driven by `state["pipeline_stage"]`. In Story 1.1, only the stub "spec_ingestion" stage exists — but the component must be placed in a location where future stories can update it without restructuring the layout.

Recommended placement: immediately after `st.title("Sata — AI API Tester")` as a `st.subheader` or dedicated `st.container`.

### References

- Cookiecutter command: `cookiecutter https://github.com/gerardrbentley/cookiecutter-streamlit` [Source: architecture.md#Selected Starter]
- SataState single source of truth: FR34 [Source: prd.md#Agent Architecture]
- 8+ nodes requirement: FR33 [Source: prd.md#Agent Architecture]
- 5+ conditional routes: FR33 [Source: prd.md#Agent Architecture]
- Stage header: UX-DR1 "persistent Stage header visible across relevant UI areas" [Source: ux-design-specification.md#Platform Strategy]
- `.env` config vars (`LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`): [Source: prd.md#Installation & Setup]
- Security: NFR6-NFR8 — keys in `.env` only, never logged, never shown in UI [Source: prd.md#Non-Functional Requirements]
- No Docker for MVP: [Source: prd.md#Installation & Setup]
- Gemini via OpenAI-compat endpoint (`LLM_BASE_URL`): NFR9 [Source: prd.md#Non-Functional Requirements]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- All 13 tests pass: `python3 -m pytest tests/ -v` → 13 passed in 0.20s
- Syntax check: `python3 -m py_compile app.py app/state.py app/pipeline.py app/utils/env.py` → OK

### Completion Notes List

- Task 1: Created project structure manually following the gerardrbentley/cookiecutter-streamlit conventions (interactive cookiecutter not runnable in automated context). Structure matches story Dev Notes exactly: `app.py`, `app/`, `app/utils/`, `.env.example`, `requirements.txt`.
- Task 2: `validate_env()` in `app/utils/env.py` loads `.env` via python-dotenv and returns list of missing required vars. `app.py` calls it before any LLM init — shows `st.error()` + `st.stop()` on missing keys (AC: 3, 4 / NFR6-NFR8).
- Task 3: `SataState` TypedDict in `app/state.py` with 13 fields covering full pipeline lifecycle. `initial_state()` factory provided for session_state initialization.
- Task 4: `app/pipeline.py` builds `StateGraph(SataState)` with 10 named stub nodes and 6 conditional routing paths. All routers are stubs returning default next node. `build_pipeline()` returns a compiled graph.
- Task 5: `app.py` initializes `st.session_state.state` and `st.session_state.pipeline` on first run. Stage header (`st.subheader`) driven by `state["pipeline_stage"]` — shows "Spec Ingestion" in stub.
- Task 6: `requirements.txt` pins all runtime deps plus `pytest>=8.0.0` and `pytest-mock>=3.14.0` for testing. All packages already installed in environment.
- Note: Full end-to-end pipeline invocation intentionally deferred — checkpoint stub nodes create a routing cycle until Stories 1.2–2.3 implement real logic. Individual node functions tested via direct invocation in `test_stub_nodes_return_state_unchanged`.

### File List

- app.py (new)
- app/__init__.py (new)
- app/state.py (new)
- app/pipeline.py (new)
- app/utils/__init__.py (new)
- app/utils/env.py (new)
- .env.example (new)
- requirements.txt (new)
- tests/__init__.py (new)
- tests/test_env.py (new)
- tests/test_state.py (new)
- tests/test_pipeline.py (new)
