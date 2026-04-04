# Story 7.3: Extract Pipeline Nodes to `src/nodes/`

Status: ready-for-dev

## Story

As a developer working on Sata,
I want each pipeline node extracted from the monolith `app/pipeline.py` into its own file under `src/nodes/`,
So that each node can be developed, tested, and reviewed independently without scrolling through 600+ lines.

## Acceptance Criteria

1. **Given** the current `app/pipeline.py` contains 10 node handler functions, 6 routing functions, metadata dicts, instrumentation logic, and `build_pipeline()`, **when** the extraction is applied, **then** the following files exist under `src/nodes/`:
   - `src/nodes/ingest_spec.py`
   - `src/nodes/parse_spec.py`
   - `src/nodes/detect_gaps.py`
   - `src/nodes/fill_gaps.py`
   - `src/nodes/review_spec.py`
   - `src/nodes/generate_tests.py` (stub)
   - `src/nodes/review_test_plan.py` (stub)
   - `src/nodes/execute_tests.py` (stub)
   - `src/nodes/analyze_results.py` (stub)
   - `src/nodes/review_results.py` (stub)

   **And** `src/nodes/__init__.py` re-exports all 10 node handler functions by name.

2. **Given** nodes are extracted, **when** the developer inspects each node file, **then** each file contains exactly one public node handler function with signature `def <node_name>(state: SataState) -> SataState`. Each node imports `SataState` from `src.core.state` and any tools from `src.tools.*` — never from `app.*`, from other node files, or from `src.core.graph`. Private helpers (e.g., `_is_actionable_answer()`, `_apply_gap_answer()`) live in the same file as their owning node, prefixed with `_`.

3. **Given** routing logic and graph construction remain in the core layer, **when** the developer inspects `src/core/graph.py`, **then** it contains:
   - `PIPELINE_NODE_ORDER` list
   - `PIPELINE_NODE_METADATA` dict
   - `CONDITIONAL_EDGE_LABELS` dict
   - `LINEAR_EDGE_LABELS` dict
   - `PIPELINE_STAGE_TO_NODE` dict
   - `NODE_HANDLERS` dict
   - `ROUTE_HANDLERS` dict
   - `LINEAR_ROUTE_TARGETS` dict
   - All 6 `_route_*` routing functions
   - `reset_visualization_trace()` instrumentation helper
   - `run_pipeline_node()` instrumentation helper
   - `record_route_transition()` instrumentation helper
   - `_append_taken_edge()` private helper
   - `_resolve_route_target()` private helper
   - `_make_instrumented_node()` factory
   - `_make_recording_router()` factory
   - `build_pipeline()` graph builder

   **And** `src/core/graph.py` imports node handlers from `src.nodes` (not from `app.pipeline`).

4. **Given** all nodes are extracted, **when** `pytest tests/ --tb=short -q` is run, **then** all existing pipeline tests pass. Tests in `tests/test_pipeline.py`, `tests/test_parse_spec_node.py`, and `tests/test_review_spec_node.py` must pass with their import paths updated to point at `src.nodes.*` and `src.core.graph`.

## Tasks / Subtasks

- [ ] Task 1: Create `src/nodes/ingest_spec.py` (AC: 1, 2)
  - [ ] Copy the `ingest_spec()` node handler verbatim from `app/pipeline.py` (lines 114–118)
  - [ ] Add `from src.core.state import SataState` as the only import
  - [ ] No private helpers required for this node

- [ ] Task 2: Create `src/nodes/parse_spec.py` (AC: 1, 2)
  - [ ] Copy the `parse_spec()` node handler verbatim from `app/pipeline.py` (lines 120–146)
  - [ ] Add `from src.core.state import SataState` and `from src.tools.spec_parser import parse_openapi_spec` as imports
  - [ ] After Story 7.2 is done, `src.tools.spec_parser` is the canonical location; do NOT import from `app.utils.spec_parser`
  - [ ] No private helpers required for this node

- [ ] Task 3: Create `src/nodes/detect_gaps.py` (AC: 1, 2)
  - [ ] Copy the `detect_gaps()` node handler verbatim from `app/pipeline.py` (lines 149–177)
  - [ ] Add `from src.core.state import SataState` and `from src.tools.gap_detector import detect_spec_gaps` as imports
  - [ ] After Story 7.2 is done, `src.tools.gap_detector` is the canonical location (renamed from `spec_gap_detector`); do NOT import from `app.utils.spec_gap_detector`
  - [ ] No private helpers required for this node

- [ ] Task 4: Create `src/nodes/fill_gaps.py` (AC: 1, 2)
  - [ ] Copy the `fill_gaps()` node handler verbatim from `app/pipeline.py` (lines 180–241)
  - [ ] Copy ALL private helpers that `fill_gaps()` depends on into the same file:
    - `_is_conversational_mode(state: SataState) -> bool` (lines 407–415)
    - `_is_actionable_answer(gap: dict, answer) -> bool` (lines 322–330)
    - `_apply_gap_answer(parsed_api_model: dict, gap: dict, answer) -> None` (lines 333–353)
    - `_find_endpoint(parsed_api_model: dict, gap: dict) -> Optional[dict]` (lines 355–362)
    - `_auth_state_from_answer(answer: str) -> dict` (lines 364–385)
    - `_apply_global_auth_if_unambiguous(parsed_api_model: dict, answer: str) -> None` (lines 388–404)
  - [ ] Add imports: `from typing import Optional`, `from src.core.state import SataState`, `from src.tools.conversational_builder import extract_api_model_from_conversation`
  - [ ] After Story 7.2 is done, `src.tools.conversational_builder` is the canonical location (renamed from `conversational_spec_builder`); do NOT import from `app.utils.conversational_spec_builder`

- [ ] Task 5: Create `src/nodes/review_spec.py` (AC: 1, 2)
  - [ ] Copy the `review_spec()` node handler verbatim from `app/pipeline.py` (lines 244–256)
  - [ ] Add `from src.core.state import SataState` as the only import
  - [ ] No private helpers required for this node

- [ ] Task 6: Create stub node files (AC: 1, 2)
  - [ ] Create `src/nodes/generate_tests.py` — stub node, docstring: `"Stub: LLM generates test cases across 6+ defect categories."`
  - [ ] Create `src/nodes/review_test_plan.py` — stub node, docstring: `"Stub: Checkpoint 2 — waits for human test plan approval."`
  - [ ] Create `src/nodes/execute_tests.py` — stub node, docstring: `"Stub: HTTP test execution with auth + basic retry logic."`
  - [ ] Create `src/nodes/analyze_results.py` — stub node, docstring: `"Stub: defect pattern analysis + developer-friendly explanations."`
  - [ ] Create `src/nodes/review_results.py` — stub node, docstring: `"Stub: Checkpoint 3 — re-test loop entry point."`
  - [ ] Each stub has signature `def <node_name>(state: SataState) -> SataState: return state` and imports `from src.core.state import SataState`

- [ ] Task 7: Create `src/nodes/__init__.py` with full re-exports (AC: 1)
  - [ ] Import and re-export all 10 node handlers so callers can do `from src.nodes import ingest_spec` or `from src.nodes import *`
  - [ ] Use explicit `__all__` list for clarity

- [ ] Task 8: Create `src/core/graph.py` (AC: 3)
  - [ ] Copy into `src/core/graph.py` from `app/pipeline.py`:
    - All metadata/constants: `PIPELINE_NODE_ORDER`, `PIPELINE_NODE_METADATA`, `CONDITIONAL_EDGE_LABELS`, `LINEAR_EDGE_LABELS`, `PIPELINE_STAGE_TO_NODE`, `NODE_HANDLERS`, `ROUTE_HANDLERS`, `LINEAR_ROUTE_TARGETS`
    - All routing functions: `_route_after_ingest()`, `_route_after_parse()`, `_route_gaps()`, `_route_spec_review()`, `_route_test_plan()`, `_route_results()`
    - All instrumentation functions: `reset_visualization_trace()`, `run_pipeline_node()`, `record_route_transition()`, `_append_taken_edge()`, `_resolve_route_target()`, `_make_instrumented_node()`, `_make_recording_router()`
    - `build_pipeline()` graph builder
  - [ ] Replace `from app.state import SataState` with `from src.core.state import SataState`
  - [ ] Replace all node handler references in `NODE_HANDLERS` dict and `build_pipeline()` with imports from `src.nodes`:
    ```python
    from src.nodes import (
        ingest_spec, parse_spec, detect_gaps, fill_gaps, review_spec,
        generate_tests, review_test_plan, execute_tests,
        analyze_results, review_results,
    )
    ```
  - [ ] Add `from langgraph.graph import END, StateGraph` and `from typing import Optional`
  - [ ] Do NOT import from `app.pipeline` anywhere in this file

- [ ] Task 9: Convert `app/pipeline.py` to a re-export shim (AC: 3, 4)
  - [ ] Replace the entire body of `app/pipeline.py` with backward-compatibility re-exports from `src.core.graph` and `src.nodes`
  - [ ] See exact shim pattern in Dev Notes below
  - [ ] Verify `from app.pipeline import build_pipeline, detect_gaps, fill_gaps, ...` still works

- [ ] Task 10: Update test imports (AC: 4)
  - [ ] Update `tests/test_pipeline.py` — change import block from `app.pipeline` to `src.core.graph` and `src.nodes` (see exact mapping in Dev Notes)
  - [ ] Update `tests/test_parse_spec_node.py` — change `from app.pipeline import parse_spec` to `from src.nodes.parse_spec import parse_spec`
  - [ ] Update `tests/test_review_spec_node.py` — change `from app.pipeline import review_spec` to `from src.nodes.review_spec import review_spec`
  - [ ] Update the `monkeypatch.setattr` target in `tests/test_pipeline.py` for `fill_gaps` tests — change `"app.pipeline.extract_api_model_from_conversation"` to `"src.nodes.fill_gaps.extract_api_model_from_conversation"`
  - [ ] Run `pytest tests/ --tb=short -q` and confirm fully green

- [ ] Task 11: Verify ruff compliance (AC: 4)
  - [ ] Run `ruff check src/nodes/ src/core/graph.py` — fix any lint errors
  - [ ] Run `ruff format --check src/nodes/ src/core/graph.py` — fix any formatting issues
  - [ ] Ensure max line length 88 chars throughout

## Dev Notes

### Epic & Scope Context

Epic 7 restructures the flat `app/` layout into a layered `src/` architecture. The dependency rule is: `nodes → tools → core`, `ui → core`. No reverse or lateral imports are permitted.

Story 7.3 is the third installment:
- Story 7.1 created `src/core/` (state, config, models, prompts stub) and shimmed `app/state.py`
- Story 7.2 moved tools to `src/tools/` (spec_parser, spec_fetcher, gap_detector, conversational_builder) and shimmed `app/utils/` files
- Story 7.3 (this story) extracts all node handlers into `src/nodes/` and moves graph/routing logic into `src/core/graph.py`, shimming `app/pipeline.py`

### Dependencies (7.1 + 7.2 Must Be Done First)

This story assumes:
- `src/core/state.py` exists and exports `SataState` (from Story 7.1)
- `src/nodes/__init__.py` exists as an empty stub (scaffolded in Story 7.1)
- `src/tools/spec_parser.py` exports `parse_openapi_spec` (from Story 7.2)
- `src/tools/gap_detector.py` exports `detect_spec_gaps` (from Story 7.2 — note rename from `spec_gap_detector`)
- `src/tools/conversational_builder.py` exports `extract_api_model_from_conversation` (from Story 7.2 — note rename from `conversational_spec_builder`)

Do NOT begin this story until Stories 7.1 and 7.2 are merged to `develop`.

### Pipeline Decomposition Map (Which Function Goes to Which File)

The following table maps every function in `app/pipeline.py` to its destination:

| Function | Current location | Destination |
|---|---|---|
| `ingest_spec()` | `app/pipeline.py:114` | `src/nodes/ingest_spec.py` |
| `parse_spec()` | `app/pipeline.py:120` | `src/nodes/parse_spec.py` |
| `detect_gaps()` | `app/pipeline.py:149` | `src/nodes/detect_gaps.py` |
| `fill_gaps()` | `app/pipeline.py:180` | `src/nodes/fill_gaps.py` |
| `review_spec()` | `app/pipeline.py:244` | `src/nodes/review_spec.py` |
| `generate_tests()` | `app/pipeline.py:259` | `src/nodes/generate_tests.py` |
| `review_test_plan()` | `app/pipeline.py:264` | `src/nodes/review_test_plan.py` |
| `execute_tests()` | `app/pipeline.py:269` | `src/nodes/execute_tests.py` |
| `analyze_results()` | `app/pipeline.py:274` | `src/nodes/analyze_results.py` |
| `review_results()` | `app/pipeline.py:279` | `src/nodes/review_results.py` |
| `_route_after_ingest()` | `app/pipeline.py:287` | `src/core/graph.py` |
| `_route_after_parse()` | `app/pipeline.py:293` | `src/core/graph.py` |
| `_route_gaps()` | `app/pipeline.py:302` | `src/core/graph.py` |
| `_route_spec_review()` | `app/pipeline.py:307` | `src/core/graph.py` |
| `_route_test_plan()` | `app/pipeline.py:312` | `src/core/graph.py` |
| `_route_results()` | `app/pipeline.py:317` | `src/core/graph.py` |
| `_is_actionable_answer()` | `app/pipeline.py:322` | `src/nodes/fill_gaps.py` (private helper) |
| `_apply_gap_answer()` | `app/pipeline.py:333` | `src/nodes/fill_gaps.py` (private helper) |
| `_find_endpoint()` | `app/pipeline.py:355` | `src/nodes/fill_gaps.py` (private helper) |
| `_auth_state_from_answer()` | `app/pipeline.py:364` | `src/nodes/fill_gaps.py` (private helper) |
| `_apply_global_auth_if_unambiguous()` | `app/pipeline.py:388` | `src/nodes/fill_gaps.py` (private helper) |
| `_is_conversational_mode()` | `app/pipeline.py:407` | `src/nodes/fill_gaps.py` (private helper) |
| `NODE_HANDLERS` dict | `app/pipeline.py:418` | `src/core/graph.py` |
| `ROUTE_HANDLERS` dict | `app/pipeline.py:431` | `src/core/graph.py` |
| `LINEAR_ROUTE_TARGETS` dict | `app/pipeline.py:440` | `src/core/graph.py` |
| `reset_visualization_trace()` | `app/pipeline.py:448` | `src/core/graph.py` |
| `run_pipeline_node()` | `app/pipeline.py:457` | `src/core/graph.py` |
| `record_route_transition()` | `app/pipeline.py:488` | `src/core/graph.py` |
| `_append_taken_edge()` | `app/pipeline.py:506` | `src/core/graph.py` |
| `_resolve_route_target()` | `app/pipeline.py:512` | `src/core/graph.py` |
| `_make_instrumented_node()` | `app/pipeline.py:518` | `src/core/graph.py` |
| `_make_recording_router()` | `app/pipeline.py:526` | `src/core/graph.py` |
| `build_pipeline()` | `app/pipeline.py:538` | `src/core/graph.py` |
| `PIPELINE_NODE_ORDER` | `app/pipeline.py:21` | `src/core/graph.py` |
| `PIPELINE_NODE_METADATA` | `app/pipeline.py:34` | `src/core/graph.py` |
| `CONDITIONAL_EDGE_LABELS` | `app/pipeline.py:77` | `src/core/graph.py` |
| `LINEAR_EDGE_LABELS` | `app/pipeline.py:91` | `src/core/graph.py` |
| `PIPELINE_STAGE_TO_NODE` | `app/pipeline.py:98` | `src/core/graph.py` |

### src/core/graph.py Contents

`src/core/graph.py` is the graph assembly layer. It owns everything that is NOT a node handler. Its full import block will be:

```python
from typing import Optional

from langgraph.graph import END, StateGraph

from src.core.state import SataState
from src.nodes import (
    analyze_results,
    detect_gaps,
    execute_tests,
    fill_gaps,
    generate_tests,
    ingest_spec,
    parse_spec,
    review_results,
    review_spec,
    review_test_plan,
)
```

The `NODE_HANDLERS` dict in `src/core/graph.py` will reference the imported node functions directly:

```python
NODE_HANDLERS = {
    "ingest_spec": ingest_spec,
    "parse_spec": parse_spec,
    "detect_gaps": detect_gaps,
    "fill_gaps": fill_gaps,
    "review_spec": review_spec,
    "generate_tests": generate_tests,
    "review_test_plan": review_test_plan,
    "execute_tests": execute_tests,
    "analyze_results": analyze_results,
    "review_results": review_results,
}
```

Note: `src/core/graph.py` imports FROM `src.nodes`, which means `src/core/graph.py` is architecturally "above" nodes in the import chain even though it lives in `core/`. This is intentional — `graph.py` is the wiring layer that assembles nodes, not a pure foundation module like `state.py` or `models.py`. The dependency rule `nodes → core` applies to `state.py`, `models.py`, and `config.py`. `graph.py` is a special case that forms the top of the dependency chain.

### Private Helper Assignment (Which Helpers Go With Which Node)

All private helpers (`_` prefix) are collocated with the node that exclusively uses them.

**`src/nodes/fill_gaps.py`** contains all 6 private helpers:
- `_is_conversational_mode(state: SataState) -> bool` — used by `fill_gaps()` to branch execution path
- `_is_actionable_answer(gap: dict, answer) -> bool` — used by `fill_gaps()` to filter gaps
- `_apply_gap_answer(parsed_api_model: dict, gap: dict, answer) -> None` — used by `fill_gaps()` to mutate model
- `_find_endpoint(parsed_api_model: dict, gap: dict) -> Optional[dict]` — used by `_apply_gap_answer()`
- `_auth_state_from_answer(answer: str) -> dict` — used by `_apply_global_auth_if_unambiguous()`
- `_apply_global_auth_if_unambiguous(parsed_api_model: dict, answer: str) -> None` — used by `_apply_gap_answer()`

No other node file has private helpers. The five stub nodes (`generate_tests`, `review_test_plan`, `execute_tests`, `analyze_results`, `review_results`) are single-function files with no helpers.

### app/pipeline.py Shim Pattern

After extraction, `app/pipeline.py` becomes a pure backward-compatibility shim. Replace its entire content with:

```python
"""Backward-compatibility shim for app.pipeline.

Canonical implementations:
- Node handlers → src.nodes.*
- Graph/routing → src.core.graph
"""

# Node handlers — canonical source is src.nodes
from src.nodes import (  # noqa: F401
    analyze_results,
    detect_gaps,
    execute_tests,
    fill_gaps,
    generate_tests,
    ingest_spec,
    parse_spec,
    review_results,
    review_spec,
    review_test_plan,
)

# Graph construction and routing — canonical source is src.core.graph
from src.core.graph import (  # noqa: F401
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    LINEAR_ROUTE_TARGETS,
    NODE_HANDLERS,
    PIPELINE_NODE_METADATA,
    PIPELINE_NODE_ORDER,
    PIPELINE_STAGE_TO_NODE,
    ROUTE_HANDLERS,
    _route_after_ingest,
    _route_after_parse,
    _route_gaps,
    _route_results,
    _route_spec_review,
    _route_test_plan,
    build_pipeline,
    record_route_transition,
    reset_visualization_trace,
    run_pipeline_node,
)
```

This shim ensures every existing import of the form `from app.pipeline import <anything>` continues to work without modification.

### File Structure Requirements

Files to create:
```
src/nodes/__init__.py          (replace empty stub with full re-exports)
src/nodes/ingest_spec.py
src/nodes/parse_spec.py
src/nodes/detect_gaps.py
src/nodes/fill_gaps.py
src/nodes/review_spec.py
src/nodes/generate_tests.py
src/nodes/review_test_plan.py
src/nodes/execute_tests.py
src/nodes/analyze_results.py
src/nodes/review_results.py
src/core/graph.py
```

Files to modify (shims only — logic moves out, not deleted):
```
app/pipeline.py               → re-export shim (see shim pattern above)
tests/test_pipeline.py        → update imports (see testing section below)
tests/test_parse_spec_node.py → update imports
tests/test_review_spec_node.py → update imports
```

Files to NOT touch:
- `app/state.py` (already a shim from Story 7.1)
- `app/utils/*.py` (already shims from Story 7.2)
- `app/__init__.py`
- `app.py`
- Any `tests/` file not listed above
- `requirements.txt`
- `src/core/state.py`, `src/core/config.py`, `src/core/models.py`, `src/core/prompts.py`
- `src/tools/*.py`

### src/nodes/__init__.py Pattern

```python
"""Public API for src.nodes — re-exports all 10 node handler functions."""

from src.nodes.analyze_results import analyze_results
from src.nodes.detect_gaps import detect_gaps
from src.nodes.execute_tests import execute_tests
from src.nodes.fill_gaps import fill_gaps
from src.nodes.generate_tests import generate_tests
from src.nodes.ingest_spec import ingest_spec
from src.nodes.parse_spec import parse_spec
from src.nodes.review_results import review_results
from src.nodes.review_spec import review_spec
from src.nodes.review_test_plan import review_test_plan

__all__ = [
    "analyze_results",
    "detect_gaps",
    "execute_tests",
    "fill_gaps",
    "generate_tests",
    "ingest_spec",
    "parse_spec",
    "review_results",
    "review_spec",
    "review_test_plan",
]
```

### Testing Requirements

**tests/test_pipeline.py** — update the import block (lines 3–14) from:

```python
from app.pipeline import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    _route_after_ingest,
    _route_after_parse,
    build_pipeline,
    detect_gaps,
    fill_gaps,
    record_route_transition,
    review_spec,
    run_pipeline_node,
)
from app.state import initial_state
```

To:

```python
from src.core.graph import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    _route_after_ingest,
    _route_after_parse,
    build_pipeline,
    record_route_transition,
    run_pipeline_node,
)
from src.nodes.detect_gaps import detect_gaps
from src.nodes.fill_gaps import fill_gaps
from src.nodes.review_spec import review_spec
from src.core.state import initial_state
```

**Monkeypatch targets in tests/test_pipeline.py** — the two `monkeypatch.setattr` calls in `test_fill_gaps_extracts_api_model_for_manual_conversation` and `test_fill_gaps_records_follow_up_question_for_manual_conversation` must change their target string from:

```python
"app.pipeline.extract_api_model_from_conversation"
```

To:

```python
"src.nodes.fill_gaps.extract_api_model_from_conversation"
```

**tests/test_parse_spec_node.py** — update line 9 from:

```python
from app.pipeline import parse_spec
```

To:

```python
from src.nodes.parse_spec import parse_spec
```

Also update line 10 from:

```python
from app.state import initial_state
```

To:

```python
from src.core.state import initial_state
```

**tests/test_review_spec_node.py** — update lines 3–4 from:

```python
from app.pipeline import review_spec
from app.state import initial_state
```

To:

```python
from src.nodes.review_spec import review_spec
from src.core.state import initial_state
```

After all import updates, `pytest tests/ --tb=short -q` must be fully green. Do not modify any test logic — only import paths change.

### Architecture Compliance

The following import rules must hold after this story:

| Module | May import from | Must NOT import from |
|---|---|---|
| `src/nodes/*.py` | `src.core.state`, `src.tools.*`, stdlib, third-party | `app.*`, other `src.nodes.*`, `src.core.graph`, `src.ui.*` |
| `src/core/graph.py` | `src.core.state`, `src.nodes.*`, `langgraph`, stdlib | `app.*`, `src.tools.*`, `src.ui.*` |
| `app/pipeline.py` (shim) | `src.nodes`, `src.core.graph` | Everything else |

Verify compliance by inspecting each file's import block after creation. No circular imports are possible given this topology.

### Risks And Guardrails

- **Monkeypatch target drift**: The two `monkeypatch.setattr` tests in `test_pipeline.py` patch the name `extract_api_model_from_conversation` as it is imported into the module under test. After moving `fill_gaps` to `src.nodes.fill_gaps`, the patch target must be `"src.nodes.fill_gaps.extract_api_model_from_conversation"` — not `"src.tools.conversational_builder.extract_api_model_from_conversation"`. Patching the wrong module will cause the mock to be silently ignored and tests will fail with unexpected behavior.

- **Circular import risk**: `src/core/graph.py` imports from `src.nodes`, and `src/nodes/*.py` imports from `src.core.state`. This is safe because `graph.py` is NOT imported by `state.py`. Never add an import of `src.core.graph` into any `src/nodes/*.py` file.

- **Shim completeness**: The `app/pipeline.py` shim must re-export every name that existing tests import. If any name is missing from the shim, tests that have not yet been updated will fail with `ImportError`. Cross-check the shim's re-export list against every `from app.pipeline import ...` statement across all test files before declaring the task done.

- **Tool import names**: Story 7.2 renames `app/utils/spec_gap_detector.py` to `src/tools/gap_detector.py` and `app/utils/conversational_spec_builder.py` to `src/tools/conversational_builder.py`. The function names (`detect_spec_gaps`, `extract_api_model_from_conversation`) remain unchanged. Import from the new `src.tools.*` names, not the old `app.utils.*` names.

- **Scope creep**: Do NOT migrate any `app/utils/` files, `app.py`, or Streamlit UI code in this story. Do NOT create test files beyond the import updates listed above. Story 7.6 owns test reorganization.

- **Private helper leakage**: The helpers in `fill_gaps.py` (`_is_actionable_answer`, `_apply_gap_answer`, etc.) must NOT be imported by any other node file. They are intentionally private to `fill_gaps`. If another future node needs similar logic, copy or refactor into a shared tool — do not import across node files.

### References

- `app/pipeline.py` — source of all functions being migrated (current monolith, 592 lines)
- `tests/test_pipeline.py` — primary pipeline test suite; imports must be updated
- `tests/test_parse_spec_node.py` — node-level test for `parse_spec`; imports must be updated
- `tests/test_review_spec_node.py` — node-level test for `review_spec`; imports must be updated
- `_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md` — Story 7.1 spec (establishes `src/core/` and stub `src/nodes/__init__.py`)
- `_bmad-output/planning-artifacts/epics.md` — Epic 7 story list and acceptance criteria
- `docs/source-architecture.md` — target architecture and dependency rules
- `GIT_CONVENTION.md` — commit format; PRs must have exactly 1 squashed commit

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

- [ ] [Review][Patch] `_route_results()` hardcoded to `"analyze_results"` — pipeline can never reach END, creates infinite loop [`src/core/graph.py:187`]
- [ ] [Review][Patch] `_route_spec_review()` hardcoded to `"generate_tests"` — spec rejection path dead, `spec_confirmed` never checked [`src/core/graph.py:177`]
- [ ] [Review][Patch] `_route_test_plan()` hardcoded to `"execute_tests"` — test plan revision path dead, `test_plan_confirmed` never checked [`src/core/graph.py:182`]
- [ ] [Review][Patch] `CONDITIONAL_EDGE_LABELS` missing `("review_results", END)` entry [`src/core/graph.py:89–101`]
- [ ] [Review][Patch] Test `test_pipeline_route_labels_cover_every_conditional_edge` silently excludes `END` edge via `__` filter [`tests/integration/test_pipeline.py:65`]
- [x] [Review][Defer] `iteration_count` (NFR5) never read/incremented — pre-existing in original `app/pipeline.py` — deferred, pre-existing
- [x] [Review][Defer] Private `_*` re-exports in `app/pipeline.py` shim serve no current consumer — deferred, pre-existing
- [x] [Review][Defer] `_auth_state_from_answer("none")` handled via default fallthrough — works correctly, opaque intent — deferred, pre-existing
