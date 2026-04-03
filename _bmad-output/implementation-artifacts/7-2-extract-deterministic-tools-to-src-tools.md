# Story 7.2: Extract Deterministic Tools to `src/tools/`

Status: ready-for-dev

## Story

As a developer working on Sata,
I want all deterministic business logic tools separated into `src/tools/`,
So that tools can be tested independently without the LangGraph framework and reused across multiple pipeline nodes.

## Acceptance Criteria

1. **Given** the current codebase has `app/utils/spec_parser.py`, `app/utils/spec_fetcher.py`, `app/utils/spec_gap_detector.py`, and `app/utils/conversational_spec_builder.py`, **when** the migration is applied, **then** the following files exist under `src/tools/`: `spec_parser.py`, `spec_fetcher.py`, `gap_detector.py` (renamed from `spec_gap_detector`), `conversational_builder.py` (renamed from `conversational_spec_builder`), and `src/tools/__init__.py` exports the public API of all four tools.

2. **Given** the tools are migrated to `src/tools/`, **when** the developer inspects each tool module, **then** no tool imports from `app/`, `streamlit`, or `langgraph` — only from `src/core/`, stdlib, and third-party parsing libraries (`json`, `yaml`, `openapi_spec_validator`, `langchain_openai`). The dependency direction `tools → core` is strictly enforced.

3. **Given** all tools are migrated, **when** the developer runs `pytest tests/ --tb=short -q`, **then** all existing tool-related tests pass without any modification to their test logic — only import paths in the test files are updated to reflect the new source locations.

4. **Given** the `app/utils/` shim pattern established by Story 7.1, **when** existing consumers (`app.py`, `app/pipeline.py`) import from `app.utils.spec_parser`, `app.utils.spec_fetcher`, `app.utils.spec_gap_detector`, or `app.utils.conversational_spec_builder`, **then** those imports continue to resolve correctly via backward-compatibility re-export shims, and no changes are needed in `app.py` or `app/pipeline.py`.

5. **Given** future tools will be added in Epics 3–5, **when** a developer creates `src/tools/api_client.py`, **then** the `src/tools/__init__.py` re-export convention and the `app/utils/` shim pattern are established and clearly documented as the model to follow.

## Tasks / Subtasks

- [ ] Task 1: Copy tool logic into `src/tools/` (AC: 1, 2)
  - [ ] Copy `app/utils/spec_parser.py` → `src/tools/spec_parser.py` verbatim; update module docstring to reflect new canonical location
  - [ ] Copy `app/utils/spec_fetcher.py` → `src/tools/spec_fetcher.py` verbatim; update module docstring to reflect new canonical location
  - [ ] Copy `app/utils/spec_gap_detector.py` → `src/tools/gap_detector.py` verbatim; update module docstring to reflect new canonical location
  - [ ] Copy `app/utils/conversational_spec_builder.py` → `src/tools/conversational_builder.py` verbatim; update module docstring to reflect new canonical location
  - [ ] Verify none of the four new files contain any import from `app.*`, `streamlit`, or `langgraph`
  - [ ] Confirm `src/tools/__init__.py` already exists (created as an empty stub in Story 7.1) — it will be populated in Task 2

- [ ] Task 2: Populate `src/tools/__init__.py` with public API re-exports (AC: 1, 5)
  - [ ] Add re-exports for all four tools' public symbols:
    ```python
    # src/tools/__init__.py
    from src.tools.spec_parser import parse_openapi_spec  # noqa: F401
    from src.tools.spec_fetcher import fetch_spec_from_url  # noqa: F401
    from src.tools.gap_detector import detect_spec_gaps  # noqa: F401
    from src.tools.conversational_builder import extract_api_model_from_conversation  # noqa: F401
    ```
  - [ ] Do NOT re-export private helpers (prefixed with `_`); only the public-facing functions listed above

- [ ] Task 3: Convert `app/utils/` originals to backward-compatibility re-export shims (AC: 3, 4)
  - [ ] Replace the body of `app/utils/spec_parser.py` with:
    ```python
    # Backward-compatibility shim — canonical source is src.tools.spec_parser
    from src.tools.spec_parser import parse_openapi_spec  # noqa: F401
    ```
  - [ ] Replace the body of `app/utils/spec_fetcher.py` with:
    ```python
    # Backward-compatibility shim — canonical source is src.tools.spec_fetcher
    from src.tools.spec_fetcher import (  # noqa: F401
        fetch_spec_from_url,
        _OPENER,
        DEFAULT_TIMEOUT_SECONDS,
        MAX_RESPONSE_BYTES,
    )
    ```
    Note: `_OPENER` must be re-exported because `tests/test_spec_fetcher.py` patches it via `monkeypatch.setattr(_OPENER, "open", ...)`. If `_OPENER` is not re-exported, the monkeypatch will target the wrong object and all mock-based tests will break.
  - [ ] Replace the body of `app/utils/spec_gap_detector.py` with:
    ```python
    # Backward-compatibility shim — canonical source is src.tools.gap_detector
    from src.tools.gap_detector import detect_spec_gaps  # noqa: F401
    ```
  - [ ] Replace the body of `app/utils/conversational_spec_builder.py` with:
    ```python
    # Backward-compatibility shim — canonical source is src.tools.conversational_builder
    from src.tools.conversational_builder import (  # noqa: F401
        extract_api_model_from_conversation,
    )
    ```

- [ ] Task 4: Update test import paths to point directly to `src.tools.*` (AC: 3)
  - [ ] In `tests/test_spec_parser.py` line 10: change
    `from app.utils.spec_parser import parse_openapi_spec`
    to
    `from src.tools.spec_parser import parse_openapi_spec`
  - [ ] In `tests/test_spec_fetcher.py` line 6: change
    `from app.utils.spec_fetcher import fetch_spec_from_url, _OPENER`
    to
    `from src.tools.spec_fetcher import fetch_spec_from_url, _OPENER`
  - [ ] In `tests/test_spec_gap_detector.py` lines 5–6: change
    ```python
    from app.utils.spec_gap_detector import detect_spec_gaps
    from app.utils.spec_parser import parse_openapi_spec
    ```
    to
    ```python
    from src.tools.gap_detector import detect_spec_gaps
    from src.tools.spec_parser import parse_openapi_spec
    ```
  - [ ] In `tests/test_conversational_spec_builder.py` lines 7–9: change
    ```python
    from app.utils.conversational_spec_builder import (
        extract_api_model_from_conversation,
    )
    ```
    to
    ```python
    from src.tools.conversational_builder import (
        extract_api_model_from_conversation,
    )
    ```
  - [ ] Do NOT modify any other test files — tests that import from `app.utils.*` elsewhere still pass via the shims

- [ ] Task 5: Create new unit tests under `tests/unit/` mirroring the target test structure (AC: 3, 5)
  - [ ] Create `tests/unit/test_spec_parser.py` — copy of `tests/test_spec_parser.py` with imports updated to `from src.tools.spec_parser import ...`
  - [ ] Create `tests/unit/test_spec_fetcher.py` — copy of `tests/test_spec_fetcher.py` with imports updated to `from src.tools.spec_fetcher import ...`
  - [ ] Create `tests/unit/test_gap_detector.py` — copy of `tests/test_spec_gap_detector.py` with imports updated to `from src.tools.gap_detector import ...` and `from src.tools.spec_parser import ...`
  - [ ] Create `tests/unit/test_conversational_builder.py` — copy of `tests/test_conversational_spec_builder.py` with imports updated to `from src.tools.conversational_builder import ...`
  - [ ] These new `tests/unit/` files are the canonical tests going forward; the old `tests/test_*.py` files are kept during this story as transitional coverage (they will be removed in Story 7.6)

- [ ] Task 6: Verify full test suite passes (AC: 3)
  - [ ] Run `pytest tests/ --tb=short -q` — all tests must be green
  - [ ] Run `ruff check src/tools/ app/utils/ tests/` — no lint errors introduced
  - [ ] Confirm `app.py` and `app/pipeline.py` still import successfully without modification (shims transparent to callers)

## Dev Notes

### Epic & Scope Context

- Epic 7 restructures the flat `app/` layout into a layered `src/` architecture.
- Story 7.2 scope: migrate only the four tool files from `app/utils/` to `src/tools/`. Do NOT touch `app/pipeline.py`, `app.py`, or any node logic — that belongs to Story 7.3.
- The `src/tools/__init__.py` stub was created as an empty package marker in Story 7.1. This story populates it with real content.
- **Dependency rule enforced here:** `src/tools/` imports from `src/core/`, stdlib, and third-party libs only — never from `app/`, `src/nodes/`, `src/ui/`, or other tools.

### Dependency on Story 7.1

Story 7.1 must be merged before starting 7.2. The following must already exist:
- `src/__init__.py`
- `src/tools/__init__.py` (empty stub)
- `src/core/state.py`, `src/core/config.py`, `src/core/models.py`
- `app/state.py` converted to a re-export shim
- `app/utils/env.py` converted to a re-export shim

### Current Tool File Imports (what needs updating)

**`app/utils/spec_parser.py`** (→ `src/tools/spec_parser.py`)
- Current imports: `import json`, `from typing import Optional`, `import yaml`, `from openapi_spec_validator import validate as _validate_openapi`
- No `app.*` imports — copy verbatim. No import changes needed in the tool file itself.

**`app/utils/spec_fetcher.py`** (→ `src/tools/spec_fetcher.py`)
- Current imports: `import ipaddress`, `import socket`, `from urllib import error, parse, request as _urllib_request`
- No `app.*` imports — copy verbatim. No import changes needed in the tool file itself.

**`app/utils/spec_gap_detector.py`** (→ `src/tools/gap_detector.py`)
- Current imports: `import json`, `import re`, `from typing import Optional`, `import yaml`
- No `app.*` imports — copy verbatim. No import changes needed in the tool file itself.

**`app/utils/conversational_spec_builder.py`** (→ `src/tools/conversational_builder.py`)
- Current imports: `import json`, `import os`
- Lazy import inside `_build_llm()`: `from langchain_openai import ChatOpenAI`
- The `langchain_openai` import is intentionally lazy (inside a function body) to avoid a hard dependency at import time. This is acceptable in `src/tools/` — do NOT hoist it to the top level.
- No `app.*` imports — copy verbatim. No import changes needed in the tool file itself.

### File Structure Requirements

**Create:**
- `src/tools/spec_parser.py`
- `src/tools/spec_fetcher.py`
- `src/tools/gap_detector.py`
- `src/tools/conversational_builder.py`
- `tests/unit/test_spec_parser.py`
- `tests/unit/test_spec_fetcher.py`
- `tests/unit/test_gap_detector.py`
- `tests/unit/test_conversational_builder.py`

**Modify (shims + test import updates — no logic removal):**
- `src/tools/__init__.py` → add public re-exports
- `app/utils/spec_parser.py` → replace body with re-export shim
- `app/utils/spec_fetcher.py` → replace body with re-export shim (include `_OPENER`)
- `app/utils/spec_gap_detector.py` → replace body with re-export shim
- `app/utils/conversational_spec_builder.py` → replace body with re-export shim
- `tests/test_spec_parser.py` → update import line 10
- `tests/test_spec_fetcher.py` → update import line 6
- `tests/test_spec_gap_detector.py` → update import lines 5–6
- `tests/test_conversational_spec_builder.py` → update import lines 7–9

**Do NOT touch:**
- `app.py`
- `app/pipeline.py`
- `app/state.py`
- `app/utils/env.py`
- `app/utils/spec_review.py`
- `app/utils/pipeline_visualization.py`
- `src/core/` (any file)
- Any test file not listed above

### Backward Compatibility — Re-export Shims in `app/utils/`

The following callers currently import from `app.utils.*` and must continue to work without modification:

| Caller | Import | Resolved via shim |
|--------|--------|-------------------|
| `app.py:30` | `from app.utils.spec_fetcher import fetch_spec_from_url` | `app/utils/spec_fetcher.py` shim |
| `app/pipeline.py:17` | `from app.utils.conversational_spec_builder import extract_api_model_from_conversation` | `app/utils/conversational_spec_builder.py` shim |
| `app/pipeline.py:18` | `from app.utils.spec_gap_detector import detect_spec_gaps` | `app/utils/spec_gap_detector.py` shim |
| `app/pipeline.py:19` | `from app.utils.spec_parser import parse_openapi_spec` | `app/utils/spec_parser.py` shim |

All four shims must remain in place for the duration of Epic 7. They will be cleaned up when `app/pipeline.py` is migrated in Story 7.3.

**Critical detail for `spec_fetcher` shim:** `tests/test_spec_fetcher.py` patches `_OPENER` directly using `monkeypatch.setattr(_OPENER, "open", ...)`. After converting to a shim, if the test imports `_OPENER` from `app.utils.spec_fetcher`, it will get a reference to the same object as `src.tools.spec_fetcher._OPENER` only if the re-export is done correctly. The shim must include `_OPENER` in its re-exports:
```python
from src.tools.spec_fetcher import (  # noqa: F401
    fetch_spec_from_url,
    _OPENER,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
)
```
After Task 4 updates the test to import directly from `src.tools.spec_fetcher`, this shim detail only matters for `app.py` (which only imports `fetch_spec_from_url`) — but it is safest to be complete.

### Testing Requirements

- `pytest tests/ --tb=short -q` must be fully green after all tasks are complete
- No test logic changes — only import paths change
- All tool tests are offline and deterministic; no live network, no real LLM calls
- The `FakeLLM` fixture in `test_conversational_spec_builder.py` / `test_conversational_builder.py` injects a mock LLM — the `_build_llm()` function inside `conversational_builder.py` is never invoked in tests
- Monkeypatching in `test_spec_fetcher.py` patches `_OPENER` directly on the module-level object, not the urllib opener — this technique is preserved unchanged when moving to `src.tools.spec_fetcher`

### Architecture Compliance

- `src/tools/spec_parser.py`: imports `json`, `typing`, `yaml`, `openapi_spec_validator` — all allowed
- `src/tools/spec_fetcher.py`: imports `ipaddress`, `socket`, `urllib` — all stdlib, all allowed
- `src/tools/gap_detector.py`: imports `json`, `re`, `typing`, `yaml` — all allowed
- `src/tools/conversational_builder.py`: imports `json`, `os`, lazy `langchain_openai` — allowed (third-party, not LangGraph framework)
- None of the four tools import from `app.*`, `streamlit`, or `langgraph` — verified above
- The `src/tools/` layer does NOT yet use `src/core/models.py` Pydantic models for validation — that is deferred to a future story. Tools continue to operate with plain dicts as their input/output contracts.

### Risks And Guardrails

- **`_OPENER` monkeypatch risk:** `test_spec_fetcher.py` patches `_OPENER.open` in-place. If the test file imports `_OPENER` from one module but the production code uses a different module-level object, all mock-based tests will pass the wrong code path and silently produce false positives. After Task 4, both the test and the production code import `_OPENER` from `src.tools.spec_fetcher` — this ensures the monkeypatch targets the correct object.
- **Shim body replacement risk:** When converting `app/utils/*.py` files to shims, the entire existing module body must be replaced — not just the import line. Leaving any original function definitions alongside the re-export will create duplicate symbols and confuse static analysis.
- **Scope creep risk:** Do NOT migrate `app/pipeline.py`, `app/utils/spec_review.py`, `app/utils/pipeline_visualization.py`, or any LangGraph node logic. Those belong to Stories 7.3 and 7.5.
- **Import cycle risk:** If `src/tools/` imports from `app/`, a circular import will crash at startup (since `app/utils/*.py` shims now import from `src/tools/`). Verify each new tool file has zero `app.*` imports before committing.
- **`conversational_builder.py` lazy import:** The `from langchain_openai import ChatOpenAI` inside `_build_llm()` is a deliberate lazy import. Do NOT hoist it to the top level — doing so would make `src/tools/conversational_builder.py` import LangChain unconditionally, which contradicts the "no framework deps in tools" principle (LangChain is allowed as a third-party AI lib but should remain opt-in at call time for testability).

### References

- Target architecture and migration table: `docs/source-architecture.md`
- Tool naming conventions: `docs/source-architecture.md` (Naming Conventions section)
- Story 7.1 shim pattern (model to follow): `_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md` (Tasks 2 and 3)
- Existing tool sources (canonical logic to copy): `app/utils/spec_parser.py`, `app/utils/spec_fetcher.py`, `app/utils/spec_gap_detector.py`, `app/utils/conversational_spec_builder.py`
- Existing tool tests (import paths to update): `tests/test_spec_parser.py`, `tests/test_spec_fetcher.py`, `tests/test_spec_gap_detector.py`, `tests/test_conversational_spec_builder.py`
- Callers that depend on shims: `app.py` (line 30), `app/pipeline.py` (lines 17–19)
- Epic 7 story list and objectives: `_bmad-output/planning-artifacts/epics.md`

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

- [ ] [Review][Patch] `_OPENER` listed in `src/tools/__init__.__all__` — private symbol must not be in public package API [`src/tools/__init__.py:13`]
- [ ] [Review][Patch] `DEFAULT_TIMEOUT_SECONDS` and `MAX_RESPONSE_BYTES` missing from `app/utils/spec_fetcher.py` shim — spec-required re-exports absent [`app/utils/spec_fetcher.py`]
