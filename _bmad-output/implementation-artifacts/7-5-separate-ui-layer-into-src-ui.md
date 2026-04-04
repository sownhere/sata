# Story 7.5: Separate UI Layer into `src/ui/`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer working on Sata,
I want all Streamlit-specific presentation code separated into `src/ui/`,
So that UI formatting, visualization, and layout logic are isolated from business logic and pipeline orchestration.

## Acceptance Criteria

1. **Given** the current codebase has `app/utils/spec_review.py`, `app/utils/pipeline_visualization.py`, and inline Streamlit code in `app.py`, **when** the separation is applied, **then** `src/ui/spec_review.py` (migrated from `app/utils/spec_review.py`), `src/ui/visualization.py` (migrated from `app/utils/pipeline_visualization.py`), and `src/ui/components.py` (shared Streamlit helpers extracted from `app.py`) all exist **and** `src/ui/__init__.py` exists.

2. **Given** the UI modules are separated, **when** a developer inspects each `src/ui/` module, **then** UI modules may import from `src.core` but **never** from `src.nodes` or `src.tools`. Dependency rule: `ui → core` only.

3. **Given** the root `app.py` remains as the Streamlit entrypoint, **when** a developer inspects it after migration, **then** `app.py` is a thin entrypoint that imports from `src.ui`, `src.core.config`, and `src.core.graph` — it contains no business logic, only Streamlit layout orchestration and session state wiring.

4. **Given** all UI code has been migrated, **when** the developer runs `streamlit run app.py`, **then** the application starts and functions identically to before.

5. **Given** the migration is complete, **when** the developer runs `pytest tests/ --tb=short -q`, **then** all existing tests pass without modification (backward compatibility maintained via re-export shims in `app/utils/spec_review.py` and `app/utils/pipeline_visualization.py`).

## Tasks / Subtasks

- [ ] Task 1: Create `src/ui/spec_review.py` — migrate from `app/utils/spec_review.py` (AC: 1, 2, 5)
  - [ ] Copy the full module body from `app/utils/spec_review.py` verbatim into `src/ui/spec_review.py`
  - [ ] Update the module docstring to reflect the new canonical location: `"""Deterministic formatting helpers for the Spec Review checkpoint. Canonical location: src.ui.spec_review."""`
  - [ ] Verify the module has zero imports from `app/`, `src.nodes`, or `src.tools` (it currently has none — it is pure Python with `from typing import Any` only)
  - [ ] Replace the body of `app/utils/spec_review.py` with a backward-compatibility re-export shim:
    ```python
    # Backward-compatibility shim — canonical source is src.ui.spec_review
    from src.ui.spec_review import (  # noqa: F401
        build_endpoint_detail_view,
        build_endpoint_summary_rows,
        get_stage_display_label,
    )
    ```
  - [ ] Verify `from app.utils.spec_review import build_endpoint_summary_rows, build_endpoint_detail_view, get_stage_display_label` still works (existing `tests/test_spec_review.py` must pass unchanged)

- [ ] Task 2: Create `src/ui/visualization.py` — migrate from `app/utils/pipeline_visualization.py` (AC: 1, 2, 5)
  - [ ] Copy the full module body from `app/utils/pipeline_visualization.py` verbatim into `src/ui/visualization.py`
  - [ ] Update the module docstring: `"""Pipeline visualization helpers for the Sata pipeline diagram. Canonical location: src.ui.visualization."""`
  - [ ] Update the import at the top of `src/ui/visualization.py` — the current module imports from `app.pipeline`:
    ```python
    # BEFORE (in app/utils/pipeline_visualization.py):
    from app.pipeline import (
        CONDITIONAL_EDGE_LABELS,
        LINEAR_EDGE_LABELS,
        PIPELINE_NODE_METADATA,
        PIPELINE_NODE_ORDER,
        PIPELINE_STAGE_TO_NODE,
    )
    ```
    After Story 7.3 completes, this will become `from src.core.graph import ...`. For Story 7.5 (which depends only on 7.1), keep the import pointing at `app.pipeline` — this is the correct interim state since `src.core.graph` does not exist yet.
  - [ ] Replace the body of `app/utils/pipeline_visualization.py` with a backward-compatibility re-export shim:
    ```python
    # Backward-compatibility shim — canonical source is src.ui.visualization
    from src.ui.visualization import (  # noqa: F401
        build_pipeline_graph_dot,
        build_visualization_model,
        get_default_visual_node,
        get_node_detail,
    )
    ```
  - [ ] Verify `from app.utils.pipeline_visualization import build_pipeline_graph_dot, build_visualization_model, get_default_visual_node, get_node_detail` still works (existing `tests/test_pipeline_visualization.py` must pass unchanged)

- [ ] Task 3: Create `src/ui/components.py` — extract shared widget helpers from `app.py` (AC: 1, 2, 3)
  - [ ] Extract the following functions verbatim from `app.py` into `src/ui/components.py`:
    - `_render_gap_input(gap: dict, current_answer) -> Any` — renders a selectbox, multiselect, text_input, or text_area depending on `gap["input_type"]`
    - `_has_ui_answer(answer) -> bool` — returns True if the answer is a non-empty string, non-empty list, or non-None value
    - `_format_gap_answer(answer) -> str` — formats a list or scalar answer as a display string
    - `_render_pipeline_visualization(current_state: dict) -> None` — renders the entire pipeline visualization expander, graphviz chart, node selector selectbox, node detail, and most-recent-transition caption
  - [ ] Add module docstring: `"""Shared Streamlit widget helpers for Sata UI components. Canonical location: src.ui.components."""`
  - [ ] `src/ui/components.py` may import `streamlit as st` (it is a UI module — Streamlit is permitted)
  - [ ] `src/ui/components.py` imports `build_pipeline_graph_dot`, `get_default_visual_node`, `get_node_detail` from `src.ui.visualization` (not from `app.utils`)
  - [ ] `src/ui/components.py` imports `PIPELINE_NODE_ORDER` from `app.pipeline` in the interim (Story 7.3 will move this to `src.core.graph`)
  - [ ] Add the public function signatures with type hints:
    ```python
    import streamlit as st
    from typing import Any

    from app.pipeline import PIPELINE_NODE_ORDER
    from src.ui.visualization import (
        build_pipeline_graph_dot,
        get_default_visual_node,
        get_node_detail,
    )

    def render_gap_input(gap: dict, current_answer: Any) -> Any: ...
    def has_ui_answer(answer: Any) -> bool: ...
    def format_gap_answer(answer: Any) -> str: ...
    def render_pipeline_visualization(current_state: dict) -> None: ...
    ```
  - [ ] Remove the leading underscore from function names when placing them in `src/ui/components.py` — they are module-public functions now. The private `_` prefix was an `app.py`-local convention.
  - [ ] Do NOT extract `_conversation_mode_active`, `_append_assistant_message`, `_reset_conversation_ui`, `_prime_ingestion_trace`, `_start_conversation_flow`, or `_finalize_parsed_state_after_ingestion` — these are pipeline orchestration helpers that belong in `app.py` (see "Thin app.py" section below)

- [ ] Task 4: Create `src/ui/__init__.py` (AC: 1)
  - [ ] The `src/ui/__init__.py` stub was already created in Story 7.1 as an empty package marker
  - [ ] Verify it exists; if Story 7.1 has not run yet, create it now as an empty file
  - [ ] Do NOT add re-exports to `__init__.py` — callers import directly from `src.ui.components`, `src.ui.spec_review`, `src.ui.visualization`

- [ ] Task 5: Update `app.py` to import from `src.ui` (AC: 3, 4)
  - [ ] Replace the three old import lines in `app.py`:
    ```python
    # BEFORE:
    from app.utils.pipeline_visualization import (
        build_pipeline_graph_dot,
        get_default_visual_node,
        get_node_detail,
    )
    ```
    with:
    ```python
    # AFTER:
    from src.ui.visualization import (
        build_pipeline_graph_dot,
        get_default_visual_node,
        get_node_detail,
    )
    ```
  - [ ] Add import of the extracted helpers from `src.ui.components`:
    ```python
    from src.ui.components import (
        format_gap_answer,
        has_ui_answer,
        render_gap_input,
        render_pipeline_visualization,
    )
    ```
  - [ ] Remove the inline definitions of `_render_gap_input`, `_has_ui_answer`, `_format_gap_answer`, and `_render_pipeline_visualization` from `app.py` (they now live in `src/ui/components.py`)
  - [ ] Update all call sites in `app.py` to use the new unprefixed names:
    - `_render_gap_input(...)` → `render_gap_input(...)`
    - `_has_ui_answer(...)` → `has_ui_answer(...)`
    - `_format_gap_answer(...)` → `format_gap_answer(...)`
    - `_render_pipeline_visualization(...)` → `render_pipeline_visualization(...)`
  - [ ] Keep the `app/utils/spec_review.py` import in `app.py` unchanged for now (it is not used directly in the current `app.py` — `spec_review` helpers are called from within the inline `review_spec` stage block; if they are not currently imported in `app.py`, do not add the import)
  - [ ] Verify `app.py` still imports `from app.utils.spec_fetcher import fetch_spec_from_url` and `from app.utils.env import load_env, validate_env` (these are not moved by Story 7.5)

- [ ] Task 6: Add unit tests for `src/ui/` modules (AC: 5)
  - [ ] Create `tests/unit/test_ui_spec_review.py`:
    - Import `build_endpoint_summary_rows`, `build_endpoint_detail_view`, `get_stage_display_label` from `src.ui.spec_review`
    - Include at least one test mirroring each of the three existing `tests/test_spec_review.py` tests to confirm the canonical module works at its new path
    - Tests must be offline and deterministic (no Streamlit, no LLM)
  - [ ] Create `tests/unit/test_ui_visualization.py`:
    - Import `build_visualization_model`, `build_pipeline_graph_dot`, `get_default_visual_node`, `get_node_detail` from `src.ui.visualization`
    - Include at least one test confirming `build_pipeline_graph_dot` returns a DOT string containing expected node labels
    - Include one test confirming `build_visualization_model` returns correct node statuses given a fixture state
    - Tests must be offline and deterministic (no Streamlit)
  - [ ] Do NOT create tests for `src/ui/components.py` — Streamlit widget functions require a Streamlit runtime and are not unit-testable in isolation; they are covered by the `streamlit run app.py` smoke test (AC: 4)
  - [ ] Do NOT modify any existing `tests/*.py` files

## Dev Notes

### Epic & Scope Context

Epic 7 restructures the flat `app/` layout into a layered `src/` architecture. The dependency rule is `nodes → tools → core` and `ui → core`. Story 7.5 is the UI separation story.

Stories completed before 7.5:
- **7.1** — `src/core/` exists (`state.py`, `config.py`, `models.py`, `prompts.py` stub) and `src/ui/__init__.py` stub exists
- **7.2** — `src/tools/` exists (tools migrated from `app/utils/`)
- **7.3** — `src/nodes/` and `src/core/graph.py` exist (pipeline migrated from `app/pipeline.py`)
- **7.4** — `src/prompts/` exists (prompt strings externalized)

Story 7.5 depends **only on 7.1**. It does not depend on 7.2, 7.3, or 7.4. The `src/ui/` modules may import from `app.pipeline` as an interim measure; once 7.3 lands, those imports will be updated to `src.core.graph`.

### Dependency on Story 7.1

Story 7.1 creates `src/ui/__init__.py` as an empty stub. Before running any Task in Story 7.5, confirm this file exists:

```
src/
├── __init__.py           ← created by 7.1
├── core/                 ← created by 7.1
│   ├── __init__.py
│   ├── state.py
│   ├── config.py
│   ├── models.py
│   └── prompts.py
├── nodes/
│   └── __init__.py       ← stub created by 7.1
├── tools/
│   └── __init__.py       ← stub created by 7.1
├── ui/
│   └── __init__.py       ← stub created by 7.1 ← REQUIRED before Story 7.5
└── utils/
    └── __init__.py       ← stub created by 7.1
```

If `src/ui/__init__.py` does not exist (e.g. 7.1 has not run), create it as an empty file before proceeding.

### UI Module Migration Map

| Current location | New canonical location | Story 7.5 action |
|---|---|---|
| `app/utils/spec_review.py` | `src/ui/spec_review.py` | Copy content; shimify source |
| `app/utils/pipeline_visualization.py` | `src/ui/visualization.py` | Copy content; shimify source |
| Inline in `app.py` (4 functions) | `src/ui/components.py` | Extract; update call sites in `app.py` |

### What Goes into `src/ui/components.py`

The following four functions are **shared widget helpers** — they contain Streamlit widget calls that are reusable across stages or stages-to-come, and they have no pipeline orchestration side-effects:

| Function (in `app.py`) | Extracted name in `components.py` | Reason |
|---|---|---|
| `_render_gap_input(gap, current_answer)` | `render_gap_input` | Pure widget renderer — takes a gap dict and returns the Streamlit widget value. Used in both the `fill_gaps` form loop and could be reused in future review panels. |
| `_has_ui_answer(answer)` | `has_ui_answer` | Pure predicate — determines if a widget answer has a meaningful value. No Streamlit calls, but logically belongs with its callers in the UI layer. |
| `_format_gap_answer(answer)` | `format_gap_answer` | Pure formatter — converts a widget answer to a display string. No Streamlit calls. Used in the `review_spec` stage to render captured answers. |
| `_render_pipeline_visualization(current_state)` | `render_pipeline_visualization` | Self-contained Streamlit expander block — renders the graphviz chart, node selector, node detail, and transition caption. Fully encapsulated; `app.py` calls it once with no surrounding logic. |

### What Stays in `app.py` as Orchestration

The following functions are **pipeline orchestration helpers** that wire session state, run pipeline nodes, and coordinate stage transitions. They belong in `app.py` because they couple Streamlit session state (`st.session_state`) to LangGraph node execution:

| Function | Reason it stays in `app.py` |
|---|---|
| `_conversation_mode_active(current_state)` | Reads `current_state` to decide which Streamlit branch to render. It is a routing predicate tied directly to the stage-driven rendering logic immediately below it. |
| `_append_assistant_message(message)` | Mutates `st.session_state.conversation_messages`. Pure session state wiring. |
| `_reset_conversation_ui()` | Mutates `st.session_state.conversation_messages`, `conversation_banner`, and pipeline state keys. Direct session state management. |
| `_prime_ingestion_trace(current_state, spec_source)` | Calls `reset_visualization_trace` and `run_pipeline_node` — pipeline execution, not UI. |
| `_start_conversation_flow(current_state, banner)` | Sets `pipeline_stage`, `active_node`, and conversation keys — pipeline state mutation. |
| `_finalize_parsed_state_after_ingestion(updated_state)` | Calls `record_route_transition` and `run_pipeline_node` — multi-step pipeline routing logic. |

The top-level stage-driven `if/elif` blocks (`if current_stage in ("spec_ingestion", "spec_parsed"):`, `elif current_stage == "fill_gaps":`, `elif current_stage == "review_spec":`) also stay in `app.py` — they are the layout orchestration that the AC requires.

### Thin `app.py` — What Stays vs What Moves

After Story 7.5, `app.py` will have this structure:

```
app.py (after Story 7.5)
├── Page config (st.set_page_config)               ← stays
├── Environment validation (load_env, validate_env) ← stays (imports from app.utils.env or src.core.config)
├── Session state initialisation                    ← stays
├── Stage header (st.title, st.subheader)           ← stays
├── CONVERSATION_PROMPT constant                     ← stays
├── ZERO_ENDPOINT_FALLBACK_MESSAGE constant          ← stays
├── _conversation_mode_active()                      ← stays (orchestration)
├── _append_assistant_message()                      ← stays (session state)
├── _reset_conversation_ui()                         ← stays (session state)
├── _prime_ingestion_trace()                         ← stays (pipeline execution)
├── _start_conversation_flow()                       ← stays (pipeline state)
├── _finalize_parsed_state_after_ingestion()         ← stays (pipeline routing)
├── Stage-driven rendering blocks (if/elif)          ← stays (layout orchestration)
│   ├── spec_ingestion / spec_parsed block           ← stays
│   ├── fill_gaps block                              ← stays
│   └── review_spec block                            ← stays
└── render_pipeline_visualization() call             ← stays (call site only; function moves to src/ui/components.py)
```

Imports in `app.py` after migration:

```python
# Framework
import streamlit as st
from collections import defaultdict

# Pipeline (interim — will move to src.core.graph in Story 7.3)
from app.pipeline import (
    PIPELINE_NODE_ORDER,
    build_pipeline,
    record_route_transition,
    reset_visualization_trace,
    run_pipeline_node,
)

# State (shim — canonical is src.core.state, shimmed via app.state since Story 7.1)
from app.state import initial_state

# Config (shim — canonical is src.core.config, shimmed via app.utils.env since Story 7.1)
from app.utils.env import load_env, validate_env

# Tools (shim — canonical is src.tools.spec_fetcher, shimmed via app.utils.spec_fetcher since Story 7.2)
from app.utils.spec_fetcher import fetch_spec_from_url

# UI components (NEW in Story 7.5)
from src.ui.components import (
    format_gap_answer,
    has_ui_answer,
    render_gap_input,
    render_pipeline_visualization,
)

# Visualization (NEW in Story 7.5 — replaces the app.utils.pipeline_visualization import)
from src.ui.visualization import (
    build_pipeline_graph_dot,
    get_default_visual_node,
    get_node_detail,
)
```

Note: `build_pipeline_graph_dot`, `get_default_visual_node`, and `get_node_detail` are used directly in `app.py` at the call site of `_render_pipeline_visualization` / `render_pipeline_visualization`. After Task 3 extracts `_render_pipeline_visualization` into `src/ui/components.py`, those three names are no longer called directly from `app.py`. The `from src.ui.visualization import ...` block in `app.py` can be removed once `render_pipeline_visualization` is extracted — `src/ui/components.py` owns those imports internally.

### Backward Compatibility Shims in `app/utils/`

Both shimified files follow the same pattern established in Story 7.1:

**`app/utils/spec_review.py` (after Story 7.5):**
```python
# Backward-compatibility shim — canonical source is src.ui.spec_review
from src.ui.spec_review import (  # noqa: F401
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    get_stage_display_label,
)
```

**`app/utils/pipeline_visualization.py` (after Story 7.5):**
```python
# Backward-compatibility shim — canonical source is src.ui.visualization
from src.ui.visualization import (  # noqa: F401
    build_pipeline_graph_dot,
    build_visualization_model,
    get_default_visual_node,
    get_node_detail,
)
```

These shims ensure `tests/test_spec_review.py` and `tests/test_pipeline_visualization.py` continue to pass without any modification — both test files import from the old `app.utils.*` paths.

### File Structure Requirements

Files to **create**:
- `src/ui/spec_review.py` — migrated from `app/utils/spec_review.py`
- `src/ui/visualization.py` — migrated from `app/utils/pipeline_visualization.py`
- `src/ui/components.py` — extracted from `app.py`
- `tests/unit/test_ui_spec_review.py`
- `tests/unit/test_ui_visualization.py`

Files to **modify**:
- `app/utils/spec_review.py` → replace body with re-export shim
- `app/utils/pipeline_visualization.py` → replace body with re-export shim
- `app.py` → update imports; replace inline function definitions with calls to `src.ui.components`

Files to **verify exist (from Story 7.1) but not modify**:
- `src/__init__.py`
- `src/ui/__init__.py`
- `src/core/__init__.py`

Files to **not touch**:
- Any other `app/utils/*.py` file
- `app/pipeline.py`
- `app/state.py`
- Any existing `tests/*.py` file

### Testing Requirements

- `pytest tests/ --tb=short -q` must be fully green after all tasks complete
- `tests/test_spec_review.py` and `tests/test_pipeline_visualization.py` must pass without any modification (they import via the old `app.utils.*` shim paths)
- New `tests/unit/test_ui_spec_review.py` and `tests/unit/test_ui_visualization.py` import directly from `src.ui.*` canonical paths
- No Streamlit runtime required for any test — `src/ui/spec_review.py` and `src/ui/visualization.py` do not import `streamlit`; only `src/ui/components.py` does
- No LLM calls, no live network in any test
- `streamlit run app.py` smoke test: start the app and confirm the pipeline visualization and gap input form render correctly

### Architecture Compliance

- `src/ui/spec_review.py` must import only from stdlib (`typing`) — no `app.*`, no `src.nodes.*`, no `src.tools.*`
- `src/ui/visualization.py` must import only from `app.pipeline` (interim) and stdlib — no `src.nodes.*`, no `src.tools.*`; after Story 7.3 this will be updated to `src.core.graph`
- `src/ui/components.py` may import `streamlit` and `src.ui.visualization` and `app.pipeline` (interim) — it must not import from `src.nodes.*` or `src.tools.*`
- `app.py` after migration: imports from `src.ui.*`, `app.pipeline` (interim), `app.state` (shim), `app.utils.env` (shim), `app.utils.spec_fetcher` (shim) — this is the correct layered state mid-Epic 7

### Risks And Guardrails

- **Name unprefixing risk:** The functions in `app.py` are named with a leading underscore (`_render_gap_input`, etc.) as module-private helpers. When moving to `src/ui/components.py`, the underscore must be removed since they become the module's public API. All four call sites in `app.py` must also be updated. Leaving any call site using the old `_render_gap_input` name will cause a `NameError` at runtime.
- **Import loop risk:** `src/ui/visualization.py` imports from `app.pipeline`. This is safe because `app.pipeline` does not import from `src.ui`. Confirm there is no cycle before committing.
- **`build_pipeline_graph_dot` double-import risk:** After Task 3, `render_pipeline_visualization` in `src/ui/components.py` calls `build_pipeline_graph_dot` from `src.ui.visualization`. If `app.py` still has `from src.ui.visualization import build_pipeline_graph_dot` at the top, it is a harmless redundancy — but it should be removed in Task 5 to keep `app.py` clean.
- **Streamlit import in tests risk:** `tests/unit/test_ui_spec_review.py` and `tests/unit/test_ui_visualization.py` must not import `src.ui.components` — that module imports `streamlit` which requires a running Streamlit context. Import only `src.ui.spec_review` and `src.ui.visualization` in the new unit tests.
- **Scope creep risk:** Do NOT migrate `app/utils/spec_fetcher.py`, `app/utils/spec_parser.py`, `app/utils/spec_gap_detector.py`, or `app/utils/conversational_spec_builder.py` — those are `src/tools/` modules owned by Story 7.2.
- **Shim omission risk:** Forgetting to convert `app/utils/spec_review.py` or `app/utils/pipeline_visualization.py` to shims will cause `tests/test_spec_review.py` and `tests/test_pipeline_visualization.py` to fail with `ImportError` since they import from the old paths.

### References

- Target `src/ui/` structure and module responsibilities: [`docs/source-architecture.md`]
- Story 7.1 (dependency) — `src/ui/__init__.py` stub and shim pattern: [`_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md`]
- Source of `spec_review.py` functions: [`app/utils/spec_review.py`]
- Source of `pipeline_visualization.py` functions: [`app/utils/pipeline_visualization.py`]
- Source of components to extract (lines 79–237): [`app.py`]
- Existing spec review tests (must keep passing via shim): [`tests/test_spec_review.py`]
- Existing visualization tests (must keep passing via shim): [`tests/test_pipeline_visualization.py`]
- Epic 7 story list and objectives: [`_bmad-output/planning-artifacts/epics.md`]
- Migration table (current → target): [`docs/source-architecture.md`, "Migration Path from Current Structure"]

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

_TBD_

### Completion Notes List

_TBD_

### File List

_TBD_

### Change Log

_TBD_

### Review Findings

- [ ] [Review][Patch] Three unused imports from `app.utils.pipeline_visualization` will fail CI lint (Ruff F401) [`app.py:25–29`]
- [ ] [Review][Patch] `from src.core.prompts import load_prompt` placed mid-file after `st.title()` — will fail CI lint (Ruff E402) [`app.py:76`]
- [ ] [Review][Patch] `src/ui/components.py` imports `PIPELINE_NODE_ORDER` from `app.pipeline` shim — violates `ui → core` rule; use `src.core.graph` directly [`src/ui/components.py:14`]
- [x] [Review][Defer] Six orchestration helpers (`_conversation_mode_active`, `_append_assistant_message`, `_reset_conversation_ui`, `_prime_ingestion_trace`, `_start_conversation_flow`, `_finalize_parsed_state_after_ingestion`) remain in `app.py` — deferred, extraction to future story
