# Story 7.6: Reorganize Tests into 3-Tier Structure

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer working on Sata,
I want the test suite organized into `tests/unit/`, `tests/integration/`, and `tests/e2e/` tiers,
So that I can run fast unit tests during development and slower integration/e2e tests in CI.

## Acceptance Criteria

1. **Given** the current `tests/` directory has 11 flat test files, **when** reorganization is applied, **then**:
   - `tests/unit/` contains: `test_state.py`, `test_env.py`, `test_spec_parser.py`, `test_spec_gap_detector.py`, `test_spec_fetcher.py`, `test_spec_review.py`, `test_conversational_spec_builder.py`, `test_pipeline_visualization.py`
   - `tests/integration/` contains: `test_pipeline.py`, `test_parse_spec_node.py`, `test_review_spec_node.py`
   - `tests/e2e/` contains: `__init__.py` and `.gitkeep`

2. **Given** the tests are reorganized, **when** `pytest tests/ --tb=short -q` is run, **then** all tests pass and the CI command is unchanged.

3. **Given** a developer wants fast feedback, **when** `pytest tests/unit/ --tb=short -q` is run, **then** only unit tests run (no integration or e2e tests execute).

4. **Given** the reorganization is complete, **when** the developer inspects test imports, **then** all imports in moved test files reference `src.*` modules (not `app.*`), honoring the canonical module paths established by Stories 7.1–7.5.

## Tasks / Subtasks

- [ ] Task 1: Create tier directory scaffolding (AC: 1)
  - [ ] Create `tests/integration/__init__.py` (empty — package marker)
  - [ ] Create `tests/e2e/__init__.py` (empty — package marker)
  - [ ] Create `tests/e2e/.gitkeep` (empty — preserves the directory in git without test files)
  - [ ] Note: `tests/unit/__init__.py` already exists from Story 7.1 — do NOT recreate it

- [ ] Task 2: Move and update 8 unit test files (AC: 1, 4)
  - [ ] For each file below: copy content to `tests/unit/`, update all imports from `app.*` to `src.*`, then delete the original from `tests/`
  - [ ] `tests/test_state.py` → `tests/unit/test_state.py` (import update required — see Import Update Map)
  - [ ] `tests/test_env.py` → `tests/unit/test_env.py` (import update required)
  - [ ] `tests/test_spec_parser.py` → `tests/unit/test_spec_parser.py` (import update required)
  - [ ] `tests/test_spec_gap_detector.py` → `tests/unit/test_spec_gap_detector.py` (import update required)
  - [ ] `tests/test_spec_fetcher.py` → `tests/unit/test_spec_fetcher.py` (import update required)
  - [ ] `tests/test_spec_review.py` → `tests/unit/test_spec_review.py` (import update required)
  - [ ] `tests/test_conversational_spec_builder.py` → `tests/unit/test_conversational_spec_builder.py` (import update required)
  - [ ] `tests/test_pipeline_visualization.py` → `tests/unit/test_pipeline_visualization.py` (import update required)

- [ ] Task 3: Move and update 3 integration test files (AC: 1, 4)
  - [ ] `tests/test_pipeline.py` → `tests/integration/test_pipeline.py` (import update required — see Import Update Map)
  - [ ] `tests/test_parse_spec_node.py` → `tests/integration/test_parse_spec_node.py` (import update required)
  - [ ] `tests/test_review_spec_node.py` → `tests/integration/test_review_spec_node.py` (import update required)

- [ ] Task 4: Verify no original flat test files remain (AC: 1)
  - [ ] Confirm `tests/test_*.py` glob returns zero results after all moves
  - [ ] Confirm `tests/__init__.py` still exists (do NOT remove it)

- [ ] Task 5: Verify tests pass at every tier (AC: 2, 3)
  - [ ] Run `pytest tests/unit/ --tb=short -q` — must be green
  - [ ] Run `pytest tests/integration/ --tb=short -q` — must be green
  - [ ] Run `pytest tests/ --tb=short -q` — must be fully green (all tiers combined, plus the pre-existing `tests/unit/test_core_*.py` tests from Story 7.1)

- [ ] Task 6: Verify monkeypatch targets in integration tests (AC: 4)
  - [ ] In `tests/integration/test_pipeline.py`, find all `monkeypatch.setattr("app.pipeline.*", ...)` calls and update the target path to `src.core.graph.*` or the appropriate `src.nodes.*` module (see Import Update Map for details)
  - [ ] Confirm no `app.*` strings remain in any test file under `tests/unit/` or `tests/integration/`

## Dev Notes

### Epic & Scope Context

Epic 7 restructures the flat `app/` layout into a layered `src/` architecture (see `docs/source-architecture.md`). Stories 7.1–7.5 migrate all source modules to `src/`. Story 7.6 is the final cleanup step: it reorganizes the test suite to match the 3-tier testing strategy defined in the architecture, and updates all test imports to reference the canonical `src.*` paths.

**Story 7.6 scope is strictly:**
- Moving existing test files into the correct tier subdirectory
- Updating `app.*` import paths to `src.*` equivalents
- Creating the `tests/integration/` and `tests/e2e/` scaffolding
- No new test logic, no new fixtures, no new assertions

Do NOT write new tests in this story. Do NOT refactor test logic. Move-and-update-imports only.

### Hard Dependency: Must Run After 7.1–7.5

This story cannot begin until all of 7.1, 7.2, 7.3, 7.4, and 7.5 are merged to `develop`. The import paths in the updated test files must resolve to real modules:

| Dependency | Unlocks |
|------------|---------|
| Story 7.1 | `src.core.state`, `src.core.config` exist |
| Story 7.2 | `src.tools.spec_parser`, `src.tools.spec_fetcher`, `src.tools.gap_detector`, `src.tools.conversational_builder` exist |
| Story 7.3 | `src.nodes.*`, `src.core.graph` exist |
| Story 7.4 | `src.core.prompts` fully implemented (prompt-dependent nodes stable) |
| Story 7.5 | `src.ui.spec_review`, `src.ui.visualization` exist |

If any upstream story is incomplete, the import updates in this story will cause `ImportError` at collection time.

### Migration Map (which file moves where)

| Original flat file | Destination tier | Rationale |
|--------------------|-----------------|-----------|
| `tests/test_state.py` | `tests/unit/test_state.py` | Tests `SataState` TypedDict in isolation — no graph, no I/O |
| `tests/test_env.py` | `tests/unit/test_env.py` | Tests `validate_env()` with `monkeypatch` — pure function, no network |
| `tests/test_spec_parser.py` | `tests/unit/test_spec_parser.py` | Tests deterministic JSON/YAML parsing — pure function |
| `tests/test_spec_gap_detector.py` | `tests/unit/test_spec_gap_detector.py` | Tests deterministic gap heuristics — pure function |
| `tests/test_spec_fetcher.py` | `tests/unit/test_spec_fetcher.py` | Tests URL fetcher with all network calls mocked |
| `tests/test_spec_review.py` | `tests/unit/test_spec_review.py` | Tests formatting helpers — pure functions, no Streamlit runtime |
| `tests/test_conversational_spec_builder.py` | `tests/unit/test_conversational_spec_builder.py` | Tests LLM extraction with `FakeLLM` — no real LLM calls |
| `tests/test_pipeline_visualization.py` | `tests/unit/test_pipeline_visualization.py` | Tests visualization model builders — uses `initial_state()`, no LLM |
| `tests/test_pipeline.py` | `tests/integration/test_pipeline.py` | Tests compiled LangGraph graph structure and routing logic end-to-end |
| `tests/test_parse_spec_node.py` | `tests/integration/test_parse_spec_node.py` | Tests a LangGraph node handler with real state transitions |
| `tests/test_review_spec_node.py` | `tests/integration/test_review_spec_node.py` | Tests a LangGraph node handler with real state transitions |

### Import Update Map (old import → new import for each test file)

Each test file requires the following import substitutions. Apply these exactly — do not change any other code in the test files.

#### `tests/unit/test_state.py`
```python
# REMOVE:
from app.state import SataState, initial_state

# REPLACE WITH:
from src.core.state import SataState, initial_state
```

#### `tests/unit/test_env.py`
```python
# REMOVE:
from app.utils.env import validate_env, REQUIRED_ENV_VARS

# REPLACE WITH:
from src.core.config import validate_env, REQUIRED_ENV_VARS
```

#### `tests/unit/test_spec_parser.py`
```python
# REMOVE:
from app.utils.spec_parser import parse_openapi_spec

# REPLACE WITH:
from src.tools.spec_parser import parse_openapi_spec
```

#### `tests/unit/test_spec_gap_detector.py`
```python
# REMOVE:
from app.utils.spec_gap_detector import detect_spec_gaps
from app.utils.spec_parser import parse_openapi_spec

# REPLACE WITH:
from src.tools.gap_detector import detect_spec_gaps
from src.tools.spec_parser import parse_openapi_spec
```

#### `tests/unit/test_spec_fetcher.py`
```python
# REMOVE:
from app.utils.spec_fetcher import fetch_spec_from_url, _OPENER

# REPLACE WITH:
from src.tools.spec_fetcher import fetch_spec_from_url, _OPENER
```

#### `tests/unit/test_spec_review.py`
```python
# REMOVE:
from app.utils.spec_review import (
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    get_stage_display_label,
)

# REPLACE WITH:
from src.ui.spec_review import (
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    get_stage_display_label,
)
```

#### `tests/unit/test_conversational_spec_builder.py`
```python
# REMOVE:
from app.utils.conversational_spec_builder import (
    extract_api_model_from_conversation,
)

# REPLACE WITH:
from src.tools.conversational_builder import (
    extract_api_model_from_conversation,
)
```

#### `tests/unit/test_pipeline_visualization.py`
```python
# REMOVE:
from app.pipeline import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    record_route_transition,
    run_pipeline_node,
)
from app.state import initial_state
from app.utils.pipeline_visualization import (
    build_pipeline_graph_dot,
    build_visualization_model,
    get_default_visual_node,
    get_node_detail,
)

# REPLACE WITH:
from src.core.graph import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    record_route_transition,
    run_pipeline_node,
)
from src.core.state import initial_state
from src.ui.visualization import (
    build_pipeline_graph_dot,
    build_visualization_model,
    get_default_visual_node,
    get_node_detail,
)
```

#### `tests/integration/test_pipeline.py`
```python
# REMOVE:
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

# REPLACE WITH:
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

Additionally, update the `monkeypatch.setattr` target string inside the test body:
```python
# REMOVE:
monkeypatch.setattr(
    "app.pipeline.extract_api_model_from_conversation",
    ...
)

# REPLACE WITH:
monkeypatch.setattr(
    "src.nodes.fill_gaps.extract_api_model_from_conversation",
    ...
)
```
(This `monkeypatch.setattr` appears in two tests: `test_fill_gaps_extracts_api_model_for_manual_conversation` and `test_fill_gaps_records_follow_up_question_for_manual_conversation`. Update both.)

#### `tests/integration/test_parse_spec_node.py`
```python
# REMOVE:
from app.pipeline import parse_spec
from app.state import initial_state

# REPLACE WITH:
from src.nodes.parse_spec import parse_spec
from src.core.state import initial_state
```

#### `tests/integration/test_review_spec_node.py`
```python
# REMOVE:
from app.pipeline import review_spec
from app.state import initial_state

# REPLACE WITH:
from src.nodes.review_spec import review_spec
from src.core.state import initial_state
```

### What to do with tests/unit/ files created in Story 7.1

Story 7.1 already created the following files in `tests/unit/`:
- `tests/unit/__init__.py`
- `tests/unit/test_core_state.py`
- `tests/unit/test_core_config.py`
- `tests/unit/test_core_models.py`

**Do NOT recreate, modify, or delete these files.** Story 7.6 moves the original 11 flat tests alongside them. After Story 7.6, `tests/unit/` will contain 12 files total (3 from Story 7.1 + 8 moved from the flat layout + `__init__.py`).

There is no naming conflict: `test_core_state.py` and `test_state.py` are different files. `test_core_state.py` tests the `src.core.state` module directly. `test_state.py` (moved from the flat layout) tests the same module via the original fixture set — both are valid and complementary.

### conftest.py considerations

There is no `tests/conftest.py` in the current codebase. Story 7.6 does NOT require creating one. If a `conftest.py` is needed for shared fixtures across tiers in a future story, that is out of scope here.

If `pytest` fails to discover tests in `tests/integration/` or `tests/e2e/` due to missing `__init__.py` files, adding those files (as done in Task 1) is the correct fix — not a `conftest.py`.

### File Structure Requirements

**Create:**
- `tests/integration/__init__.py` — empty package marker
- `tests/integration/test_pipeline.py` — moved + import-updated from `tests/test_pipeline.py`
- `tests/integration/test_parse_spec_node.py` — moved + import-updated from `tests/test_parse_spec_node.py`
- `tests/integration/test_review_spec_node.py` — moved + import-updated from `tests/test_review_spec_node.py`
- `tests/unit/test_state.py` — moved + import-updated from `tests/test_state.py`
- `tests/unit/test_env.py` — moved + import-updated from `tests/test_env.py`
- `tests/unit/test_spec_parser.py` — moved + import-updated from `tests/test_spec_parser.py`
- `tests/unit/test_spec_gap_detector.py` — moved + import-updated from `tests/test_spec_gap_detector.py`
- `tests/unit/test_spec_fetcher.py` — moved + import-updated from `tests/test_spec_fetcher.py`
- `tests/unit/test_spec_review.py` — moved + import-updated from `tests/test_spec_review.py`
- `tests/unit/test_conversational_spec_builder.py` — moved + import-updated from `tests/test_conversational_spec_builder.py`
- `tests/unit/test_pipeline_visualization.py` — moved + import-updated from `tests/test_pipeline_visualization.py`
- `tests/e2e/__init__.py` — empty package marker
- `tests/e2e/.gitkeep` — preserves directory in git

**Delete (after creating the corresponding moved file):**
- `tests/test_state.py`
- `tests/test_env.py`
- `tests/test_spec_parser.py`
- `tests/test_spec_gap_detector.py`
- `tests/test_spec_fetcher.py`
- `tests/test_spec_review.py`
- `tests/test_conversational_spec_builder.py`
- `tests/test_pipeline_visualization.py`
- `tests/test_pipeline.py`
- `tests/test_parse_spec_node.py`
- `tests/test_review_spec_node.py`

**Do NOT touch:**
- `tests/__init__.py` — keep as-is
- `tests/unit/__init__.py` — already exists from Story 7.1
- `tests/unit/test_core_state.py` — already exists from Story 7.1
- `tests/unit/test_core_config.py` — already exists from Story 7.1
- `tests/unit/test_core_models.py` — already exists from Story 7.1
- Any `src/` files
- Any `app/` files
- `app.py`
- `requirements.txt`
- `CLAUDE.md`

### Testing Requirements

- `pytest tests/ --tb=short -q` must be fully green after all changes — this is the canonical CI command and must remain unchanged
- `pytest tests/unit/ --tb=short -q` must run only the 12 unit test files (8 moved + 4 from Story 7.1 including `__init__.py`)
- `pytest tests/integration/ --tb=short -q` must run only the 3 integration test files
- `pytest tests/e2e/ --tb=short -q` must collect zero tests (only `__init__.py` and `.gitkeep` present) and exit 0
- No Streamlit imports, no live LLM calls, no live network requests in any test — all external dependencies must remain mocked as they were in the original flat tests
- Test counts must be identical before and after reorganization (no tests added or removed, only moved)

### Architecture Compliance

- `tests/unit/` maps to: isolated tests for `src/core/`, `src/tools/`, and `src/ui/` modules (deterministic, mocked dependencies)
- `tests/integration/` maps to: graph flow tests that compile the full LangGraph graph and execute routing logic (`src/core/graph.py`, `src/nodes/*.py`)
- `tests/e2e/` maps to: full pipeline runs with recorded LLM responses (VCR cassettes) — reserved for future stories
- Dependency direction: test files may only import from `src.*`, never from `app.*` after this story
- The `app/` re-export shims installed in Stories 7.1–7.5 remain in place for `app.py` backward compatibility — they are not used by the new test imports

### Risks And Guardrails

- **Import resolution risk:** If any upstream story (7.1–7.5) is incomplete or its re-exports are incorrect, the `src.*` import paths will raise `ImportError` at collection time. Validate each upstream story is merged before starting this story.
- **monkeypatch target string risk:** `monkeypatch.setattr("app.pipeline.extract_api_model_from_conversation", ...)` patches the name in the `app.pipeline` namespace. After migration to `src.nodes.fill_gaps`, the patch target must change to `"src.nodes.fill_gaps.extract_api_model_from_conversation"` — patching the old namespace will silently fail to intercept the call, causing test failures that appear as logic bugs. Update both occurrences in `test_pipeline.py`.
- **`_OPENER` private symbol risk:** `test_spec_fetcher.py` imports the private `_OPENER` symbol from the fetcher module. Confirm that Story 7.2 preserved this symbol in `src.tools.spec_fetcher` with the same name before finalizing the import update.
- **Naming collision risk:** `tests/unit/` will have both `test_state.py` (moved from flat) and `test_core_state.py` (from Story 7.1). These are intentionally different files. Do not merge them.
- **Scope creep risk:** Do NOT refactor test logic, add parametrize decorators, or improve test coverage in this story. Move-and-update-imports only. Any test improvements belong in a separate story.
- **Git history risk:** Prefer `git mv` followed by in-place edits over copy-then-delete, so that `git log --follow` can trace the file history through the move.

### References

- Target test structure: [`docs/source-architecture.md`] — "Testing Strategy" and "Target Directory Structure" sections
- Story 7.1 artifact (unit scaffold, `tests/unit/__init__.py` origin): [`_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md`]
- Canonical tools migration map (7.2 → `src.tools.*`): [`docs/source-architecture.md`] — "Migration Path from Current Structure" table
- Canonical nodes migration map (7.3 → `src.nodes.*`, `src.core.graph`): [`docs/source-architecture.md`]
- Canonical UI migration map (7.5 → `src.ui.*`): [`docs/source-architecture.md`]
- Current flat test files (pre-migration): [`tests/test_*.py`]
- Epic 7 story list and objectives: [`_bmad-output/planning-artifacts/epics.md`]

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

- [ ] [Review][Patch] `test_pipeline_visualization.py` exercises graph routing + UI layer — belongs in `tests/integration/`, not `tests/unit/` [`tests/unit/test_pipeline_visualization.py`]
- [ ] [Review][Patch] Stale docstring references `app.utils.spec_parser` instead of `src.tools.spec_parser` [`tests/unit/test_spec_parser.py:1`]
- [x] [Review][Defer] `app/utils/env.py` shim has no test exercising the shim re-export path — deferred, pre-existing
