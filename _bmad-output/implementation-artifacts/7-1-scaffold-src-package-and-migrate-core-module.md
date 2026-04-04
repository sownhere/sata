# Story 7.1: Scaffold `src/` Package & Migrate Core Module

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer working on Sata,
I want the core state, data models, and configuration consolidated in `src/core/`,
So that all pipeline nodes and tools import from a single, well-typed foundation layer.

## Acceptance Criteria

1. **Given** the current codebase has `app/state.py` and env validation in `app/utils/env.py`, **when** the migration is applied, **then** `src/core/__init__.py`, `src/core/state.py`, and `src/core/config.py` exist **and** `SataState` is importable from `src.core.state` with identical TypedDict fields and `initial_state()` function **and** `src/core/config.py` consolidates `load_env()` and `validate_env()` from the former `env.py`.

2. **Given** the new `src/core/` module exists, **when** the developer inspects `src/core/models.py`, **then** Pydantic models are defined for: `EndpointModel`, `AuthModel`, `ApiModel` (matching the canonical API model dict schema), and `GapRecord` (matching the gap record dict schema) **and** each model includes field-level docstrings and correct `Optional` typing **and** the models validate correctly against existing test fixtures from `test_spec_parser.py` and `test_spec_gap_detector.py`.

3. **Given** the new `src/` package structure exists, **when** the developer runs `pytest tests/ --tb=short -q`, **then** all existing tests pass without modification (backward compatibility maintained via re-exports in `app/state.py` and `app/utils/env.py`).

4. **Given** `src/core/` is established, **when** the developer inspects `src/__init__.py`, **then** it exists and the `src` package is importable.

## Tasks / Subtasks

- [ ] Task 1: Scaffold `src/` package and `src/core/` layer (AC: 1, 4)
  - [ ] Create `src/__init__.py` (empty — package marker only)
  - [ ] Create `src/core/__init__.py` (empty — package marker only)
  - [ ] Create `src/nodes/__init__.py`, `src/tools/__init__.py`, `src/ui/__init__.py`, `src/utils/__init__.py` as empty stubs — these are sibling packages; scaffold now so future stories don't break imports, but add NO logic yet
  - [ ] Do NOT create `src/nodes/*.py`, `src/tools/*.py`, or `src/ui/*.py` content — those belong to Stories 7.2–7.5

- [ ] Task 2: Create `src/core/state.py` — exact copy of `app/state.py` logic (AC: 1, 3)
  - [ ] Copy `SataState` TypedDict and `initial_state()` verbatim from `app/state.py` into `src/core/state.py`
  - [ ] Update the module docstring to reflect the new canonical location
  - [ ] Keep imports identical (`from typing import Optional`, `from typing_extensions import TypedDict`)
  - [ ] Update `app/state.py` to become a **re-export shim** — replace its body with:
    ```python
    # Backward-compatibility shim — canonical source is src.core.state
    from src.core.state import SataState, initial_state  # noqa: F401
    ```
  - [ ] Verify `from app.state import SataState, initial_state` still works (all existing tests pass)

- [ ] Task 3: Create `src/core/config.py` — migrated from `app/utils/env.py` (AC: 1, 3)
  - [ ] Copy `REQUIRED_ENV_VARS`, `load_env()`, and `validate_env()` verbatim from `app/utils/env.py` into `src/core/config.py`
  - [ ] Update the module docstring to reflect the new canonical location
  - [ ] Update `app/utils/env.py` to become a **re-export shim**:
    ```python
    # Backward-compatibility shim — canonical source is src.core.config
    from src.core.config import REQUIRED_ENV_VARS, load_env, validate_env  # noqa: F401
    ```
  - [ ] Verify `from app.utils.env import validate_env, REQUIRED_ENV_VARS` still works

- [ ] Task 4: Create `src/core/models.py` — Pydantic v2 models for canonical data contracts (AC: 2)
  - [ ] Define `AuthModel` matching the canonical auth dict from Story 1.2:
    ```python
    class AuthModel(BaseModel):
        type: Optional[str] = None      # "bearer" | "apiKey" | None
        scheme: Optional[str] = None
        location: Optional[str] = Field(None, alias="in")  # "header" | "query"
        name: Optional[str] = None
    ```
  - [ ] Define `EndpointModel` matching the canonical endpoint dict from Story 1.2:
    ```python
    class EndpointModel(BaseModel):
        path: str
        method: str
        operation_id: str = ""
        summary: str = ""
        parameters: list[dict] = []
        request_body: Optional[dict] = None
        response_schemas: dict = {}
        auth_required: bool = False
        tags: list[str] = []
    ```
  - [ ] Define `ApiModel` as the top-level container:
    ```python
    class ApiModel(BaseModel):
        title: str = ""
        version: str = ""
        endpoints: list[EndpointModel] = []
        auth: Optional[AuthModel] = None
    ```
  - [ ] Define `GapRecord` matching the gap dict shape from `app/utils/spec_gap_detector.py`:
    ```python
    class GapRecord(BaseModel):
        endpoint: str         # e.g. "GET /users"
        field: str            # e.g. "response_schema"
        question: str         # human-readable question to resolve the gap
    ```
  - [ ] All models use Pydantic v2 syntax (`model_config = ConfigDict(...)` not `class Config`)
  - [ ] Use `model_config = ConfigDict(populate_by_name=True)` on `AuthModel` to support both `"in"` and `"location"` field names
  - [ ] Do NOT use `model_validate` or `model_dump` in this story — models are data contracts only, not runtime validators yet

- [ ] Task 5: Add `src/core/prompts.py` stub (AC: 4)
  - [ ] Create `src/core/prompts.py` with a stub `load_prompt(name: str) -> str` that raises `NotImplementedError("load_prompt will be implemented in Story 7.4")`
  - [ ] This exists to make `src/core/` importable and complete per the architecture spec — do NOT implement the full logic here

- [ ] Task 6: Add unit tests for new `src/core/` modules (AC: 2, 3)
  - [ ] Create `tests/unit/__init__.py` (empty)
  - [ ] Create `tests/unit/test_core_state.py`:
    - `SataState` importable from `src.core.state`
    - `initial_state()` returns same default values as the existing `test_state.py` fixtures
    - All 19 required keys present in `SataState.__annotations__`
  - [ ] Create `tests/unit/test_core_config.py`:
    - `validate_env`, `load_env`, `REQUIRED_ENV_VARS` importable from `src.core.config`
    - `validate_env()` returns missing vars (mirror of existing `test_env.py` logic)
  - [ ] Create `tests/unit/test_core_models.py`:
    - `EndpointModel` validates a well-formed endpoint fixture (use the Story 1.2 canonical shape)
    - `ApiModel` validates the full canonical `parsed_api_model` fixture
    - `GapRecord` validates a gap dict with `endpoint`, `field`, `question` keys
    - `AuthModel` accepts the canonical auth dict (including `"in"` key via alias)
  - [ ] Keep all tests offline and deterministic
  - [ ] Do NOT modify any existing test files in `tests/` — the existing flat tests must keep working

## Dev Notes

### Epic Context

- Epic 7 restructures the flat `app/` layout into a layered `src/` architecture.
- **Dependency rule:** `nodes → tools → core`, `ui → core`. `core` imports from nothing within `src/`.
- **Story 7.1 scope:** scaffold `src/` package + create `src/core/` only. Stories 7.2–7.7 handle tools, nodes, prompts, UI, tests reorganization, and config layer.
- Do NOT move any logic beyond `app/state.py` and `app/utils/env.py` in this story. Story 7.2 owns tools migration.

### Backward Compatibility — Critical Constraint

All existing tests import from the old paths:
- `from app.state import SataState, initial_state` — used in `tests/test_state.py`, `tests/test_pipeline.py`, `tests/test_review_spec_node.py`, and others
- `from app.utils.env import validate_env, REQUIRED_ENV_VARS` — used in `tests/test_env.py`

These imports **must not break**. The re-export shim pattern keeps old paths working:
```python
# app/state.py (shim)
from src.core.state import SataState, initial_state  # noqa: F401
```
`pytest tests/ --tb=short -q` must be fully green after this story.

### Canonical Model Shapes (from Story 1.2 contract)

`EndpointModel` must match exactly:
```python
{
    "path": "/users",
    "method": "GET",
    "operation_id": "listUsers",
    "summary": "List users",
    "parameters": [{"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}, "description": None}],
    "request_body": None,
    "response_schemas": {"200": {"type": "array", "items": {}}},
    "auth_required": True,
    "tags": ["users"],
}
```

`AuthModel` must match exactly:
```python
{"type": "bearer", "scheme": "Bearer", "in": "header", "name": "Authorization"}
```

Note: the `"in"` key is a Python reserved word as a dict key — use `Field(alias="in")` + `populate_by_name=True` in Pydantic v2.

### GapRecord Shape (from `app/utils/spec_gap_detector.py`)

Gap dicts produced by `spec_gap_detector` look like:
```python
{"endpoint": "GET /users", "field": "response_schema", "question": "What does 200 return?"}
```
`GapRecord` must validate this shape.

### Pydantic v2 Usage Notes

- `pydantic>=2.0.0` is already in `requirements.txt` — no version change needed.
- Use `from pydantic import BaseModel, Field, ConfigDict` (v2 imports).
- `class Config:` is deprecated in v2 — use `model_config = ConfigDict(...)`.
- `Optional[str]` in v2 means `str | None` (no implicit default — set `= None` explicitly).
- `list[dict]` and `dict` field defaults must use `default_factory` or a direct value:
  ```python
  parameters: list[dict] = Field(default_factory=list)
  ```

### File Structure Requirements

- Create:
  - `src/__init__.py`
  - `src/core/__init__.py`
  - `src/core/state.py`
  - `src/core/config.py`
  - `src/core/models.py`
  - `src/core/prompts.py` (stub)
  - `src/nodes/__init__.py`
  - `src/tools/__init__.py`
  - `src/ui/__init__.py`
  - `src/utils/__init__.py`
  - `tests/unit/__init__.py`
  - `tests/unit/test_core_state.py`
  - `tests/unit/test_core_config.py`
  - `tests/unit/test_core_models.py`
- Modify (shims only — no logic removal):
  - `app/state.py` → re-export shim
  - `app/utils/env.py` → re-export shim
- Do NOT touch:
  - Any other `app/` files
  - Any existing `tests/*.py` files
  - `app.py`
  - `requirements.txt`

### Testing Requirements

- `pytest tests/ --tb=short -q` must be fully green (all existing + new tests pass)
- New unit tests live in `tests/unit/` — mirrors the target test structure from `docs/source-architecture.md`
- No Streamlit imports, no LLM calls, no live network in any test
- Pydantic model tests use hardcoded fixtures matching the canonical shapes above

### Architecture Compliance

- `src/core/` imports ONLY from stdlib and third-party packages (pydantic, typing, dotenv) — never from `app/`, `src/nodes/`, `src/tools/`, or `src/ui/`
- The shim files (`app/state.py`, `app/utils/env.py`) import FROM `src.core.*` — not the reverse
- `src/core/models.py` is a **data contract** layer — no business logic, no I/O, no Streamlit

### Risks And Guardrails

- **Import cycle risk:** If any `src/core/` module imports from `app/`, a circular import will crash at startup. Keep `src/core/` dependency-free within the project.
- **Pydantic v1 syntax risk:** Using `class Config:` instead of `ConfigDict` will raise deprecation warnings in v2 and errors in v3. Use v2 syntax exclusively.
- **Shim omission risk:** Forgetting to convert `app/state.py` or `app/utils/env.py` to re-export shims will cause test failures across many test files. Do both shims in the same commit.
- **Scope creep risk:** Do NOT migrate `app/utils/spec_parser.py`, `app/pipeline.py`, or any other file. Story 7.2 owns tools, 7.3 owns nodes.

### References

- Target architecture and migration table: [Source: `docs/source-architecture.md`]
- Canonical parsed model contract: [Source: `_bmad-output/implementation-artifacts/1-2-openapi-swagger-file-upload-and-parsing.md`]
- `SataState` definition and fields: [Source: `app/state.py`]
- `load_env` / `validate_env` / `REQUIRED_ENV_VARS`: [Source: `app/utils/env.py`]
- Existing state tests (all must keep passing): [Source: `tests/test_state.py`]
- Existing env tests (all must keep passing): [Source: `tests/test_env.py`]
- Epic 7 story list and objectives: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Pydantic v2 docs — BaseModel, Field, ConfigDict: [Source: `https://docs.pydantic.dev/latest/concepts/models/`]

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

- [ ] [Review][Patch] GapRecord comment: add note linking to `_gap_record()` as schema source of truth [`src/core/models.py`]
- [ ] [Review][Patch] `get_settings()` bare `except Exception` swallows `PermissionError`/`OSError` — narrow to `yaml.YAMLError` [`src/core/config.py:95`]
- [x] [Review][Defer] `AuthModel.model_dump()` emits `location` not `"in"` without `by_alias=True` — no current consumer calls `model_dump()` [`src/core/models.py`] — deferred, pre-existing
- [x] [Review][Defer] `Settings` post-construction mutation undocumented dependency on `frozen=False` [`src/core/config.py:100–111`] — deferred, pre-existing
- [x] [Review][Defer] Story spec not updated to document multi-story scope merge on this branch — deferred, documentation debt
