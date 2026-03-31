# Story 1.2: OpenAPI/Swagger File Upload & Parsing

Status: done

## Story

As a developer,
I want to upload an OpenAPI/Swagger JSON or YAML file,
so that the system automatically extracts all endpoints, methods, parameters, schemas, and auth requirements without manual input.

## Acceptance Criteria

1. **Given** the app is on the Spec Ingestion stage, **when** the developer uploads a valid OpenAPI 3.0 JSON file, **then** the system parses it and populates `SataState` with all discovered endpoints, HTTP methods, path/query/body parameters, request/response schemas, and auth requirements.

2. **Given** the developer uploads a valid OpenAPI 3.0 YAML file, **when** parsing completes, **then** the same fields are extracted as with a JSON file.

3. **Given** the developer uploads a malformed or non-OpenAPI file, **when** parsing fails, **then** a clear error message is displayed explaining the issue, and the user is prompted to upload a different file without crashing the app.

4. **Given** a spec is successfully parsed, **when** extraction completes, **then** a summary count of discovered endpoints is shown to the user (e.g., "Found 12 endpoints"), and the pipeline advances to the next node (`detect_gaps`).

## Tasks / Subtasks

- [x] Task 1: Add `pyyaml` and `openapi-spec-validator` to `requirements.txt` (AC: 1, 2)
  - [x] Add `PyYAML>=6.0.0` for YAML parsing
  - [x] Add `openapi-spec-validator>=0.7.0` for spec structure validation
  - [x] Verify `pip install -r requirements.txt` succeeds

- [x] Task 2: Create `app/utils/spec_parser.py` — OpenAPI parsing utility (AC: 1, 2, 3)
  - [x] Implement `parse_openapi_spec(raw_spec: str) -> dict` — detect JSON vs YAML, parse, validate structure
  - [x] Implement `_extract_endpoints(spec: dict) -> list[dict]` — extract all path+method combos
  - [x] Implement `_extract_auth(spec: dict) -> dict` — extract security schemes
  - [x] Each endpoint dict must match the canonical `parsed_api_model` schema (see Dev Notes)
  - [x] Raise `ValueError` with descriptive messages on malformed input; never let exceptions bubble up raw

- [x] Task 3: Replace `parse_spec` stub in `app/pipeline.py` with real implementation (AC: 1, 2, 3, 4)
  - [x] Import `parse_openapi_spec` from `app.utils.spec_parser`
  - [x] On success: set `state["parsed_api_model"]`, `state["pipeline_stage"] = "spec_parsed"`, clear `state["error_message"]`
  - [x] On failure: set `state["error_message"]` with clear message, set `state["parsed_api_model"] = None`
  - [x] Do NOT re-raise exceptions — always return state (NFR2: single node failure must not crash pipeline)

- [x] Task 4: Replace `ingest_spec` stub in `app/pipeline.py` with real routing logic (AC: 4)
  - [x] Set `state["pipeline_stage"] = "spec_ingestion"` when entering
  - [x] Router `_route_after_ingest` already correct: `spec_source == "chat"` → `fill_gaps`, else → `parse_spec`
  - [x] No changes needed to router — only update the node body to ensure `pipeline_stage` is set

- [x] Task 5: Update `app.py` — replace placeholder with file upload UI (AC: 1, 2, 3, 4)
  - [x] Remove `st.info("Pipeline skeleton initialised...")` placeholder
  - [x] Add `st.file_uploader("Upload OpenAPI/Swagger spec", type=["json", "yaml", "yml"])` in "spec_ingestion" stage
  - [x] On file upload: read content → set `state["spec_source"] = "file"`, `state["raw_spec"] = content` → call `parse_spec(state)` directly → update `st.session_state.state`
  - [x] After successful parse: display `st.success(f"Found {n} endpoints")` + endpoint count
  - [x] On error: display `st.error(state["error_message"])` and reset file uploader state
  - [x] Keep stage-header driven rendering: only show uploader if `pipeline_stage == "spec_ingestion"` or `"spec_parsed"`
  - [x] "Next required action" area (UX-DR2): show "Upload your OpenAPI/Swagger spec to begin" when no file yet

- [x] Task 6: Add tests for spec parser and updated pipeline nodes (AC: 1, 2, 3, 4)
  - [x] `tests/test_spec_parser.py`: test valid JSON parse, valid YAML parse, malformed input, missing paths key
  - [x] `tests/test_parse_spec_node.py`: test node with valid state, node with missing raw_spec, node with malformed spec
  - [x] Use sample fixtures (see Dev Notes for minimal valid OpenAPI 3.0 spec)

## Dev Notes

### `parsed_api_model` Canonical Schema — MUST Follow This Exactly

All downstream stories (Spec Review 2.x, Test Generation 3.x) depend on this shape. Never deviate.

```python
parsed_api_model = {
    "endpoints": [
        {
            "path": "/users",               # str: e.g. "/users/{id}"
            "method": "GET",                # str: uppercase HTTP method
            "operation_id": "listUsers",    # str | None: from operationId
            "summary": "List all users",    # str | None: from summary
            "parameters": [                 # list: path + query params
                {
                    "name": "limit",
                    "in": "query",          # "path" | "query" | "header"
                    "required": False,
                    "schema": {"type": "integer"},
                    "description": None,
                }
            ],
            "request_body": None,           # dict | None: parsed requestBody schema
            "response_schemas": {           # dict: status_code → schema
                "200": {"type": "array", "items": {}},
            },
            "auth_required": True,          # bool: True if security applies
            "tags": ["users"],              # list[str]: from tags
        }
    ],
    "auth": {                               # Top-level auth info
        "type": "bearer",                   # "bearer" | "api_key" | "basic" | None
        "scheme": "Bearer",                 # str | None
        "in": "header",                     # "header" | "query" | None (for api_key)
        "name": "Authorization",            # str | None (header/param name)
    },
    "title": "Petstore API",               # str: from info.title
    "version": "1.0.0",                    # str: from info.version
}
```

### `app/utils/spec_parser.py` — Implementation Guide

```python
import json
import yaml
from typing import Optional

def parse_openapi_spec(raw_spec: str) -> dict:
    """Parse raw OpenAPI 3.0 JSON or YAML string into parsed_api_model dict.

    Raises ValueError with human-readable message on any failure.
    """
    # 1. Detect and parse format
    spec = _load_spec(raw_spec)

    # 2. Validate OpenAPI 3.0 structure (must have "openapi" and "paths")
    _validate_structure(spec)

    # 3. Extract
    return {
        "endpoints": _extract_endpoints(spec),
        "auth": _extract_auth(spec),
        "title": spec.get("info", {}).get("title", "Unknown API"),
        "version": spec.get("info", {}).get("version", "unknown"),
    }

def _load_spec(raw_spec: str) -> dict:
    """Try JSON first, then YAML. Raise ValueError on both failures."""
    # Try JSON
    try:
        return json.loads(raw_spec)
    except json.JSONDecodeError:
        pass
    # Try YAML
    try:
        result = yaml.safe_load(raw_spec)
        if isinstance(result, dict):
            return result
        raise ValueError("File content is not a valid OpenAPI spec (not a YAML mapping).")
    except yaml.YAMLError as e:
        raise ValueError(f"Could not parse file as JSON or YAML: {e}")

def _validate_structure(spec: dict) -> None:
    if "openapi" not in spec:
        raise ValueError("Not an OpenAPI spec: missing 'openapi' version field.")
    if not spec.get("openapi", "").startswith("3."):
        raise ValueError(f"Only OpenAPI 3.x is supported. Found: {spec.get('openapi')}")
    if "paths" not in spec:
        raise ValueError("OpenAPI spec has no 'paths' — no endpoints to extract.")

def _extract_endpoints(spec: dict) -> list:
    endpoints = []
    paths = spec.get("paths", {})
    global_security = spec.get("security", [])

    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

    for path, path_item in paths.items():
        path_params = path_item.get("parameters", [])
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            # Operation-level security overrides global; empty list = no auth
            op_security = operation.get("security", global_security)
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary"),
                "parameters": _extract_parameters(
                    path_params + operation.get("parameters", [])
                ),
                "request_body": _extract_request_body(operation.get("requestBody")),
                "response_schemas": _extract_responses(operation.get("responses", {})),
                "auth_required": bool(op_security),
                "tags": operation.get("tags", []),
            })
    return endpoints

def _extract_auth(spec: dict) -> dict:
    """Extract primary auth scheme from securitySchemes."""
    schemes = spec.get("components", {}).get("securitySchemes", {})
    for name, scheme in schemes.items():
        stype = scheme.get("type", "")
        if stype == "http":
            http_scheme = scheme.get("scheme", "").lower()
            return {
                "type": "bearer" if http_scheme == "bearer" else "basic",
                "scheme": scheme.get("scheme"),
                "in": "header",
                "name": "Authorization",
            }
        elif stype == "apiKey":
            return {
                "type": "api_key",
                "scheme": None,
                "in": scheme.get("in"),      # "header" or "query"
                "name": scheme.get("name"),  # e.g. "X-API-Key"
            }
    return {"type": None, "scheme": None, "in": None, "name": None}
```

### `app/pipeline.py` — `parse_spec` Node Replacement

Replace the existing `parse_spec` stub entirely:

```python
from app.utils.spec_parser import parse_openapi_spec

def parse_spec(state: SataState) -> SataState:
    """Parse OpenAPI/Swagger spec from state["raw_spec"].

    On success: populates parsed_api_model, advances pipeline_stage.
    On failure: sets error_message, clears parsed_api_model. Never raises.
    """
    raw = state.get("raw_spec")
    if not raw:
        state["error_message"] = "No spec content found. Please upload a file."
        state["parsed_api_model"] = None
        return state
    try:
        model = parse_openapi_spec(raw)
        state["parsed_api_model"] = model
        state["pipeline_stage"] = "spec_parsed"
        state["error_message"] = None
    except ValueError as e:
        state["error_message"] = str(e)
        state["parsed_api_model"] = None
    except Exception as e:
        state["error_message"] = f"Unexpected error parsing spec: {e}"
        state["parsed_api_model"] = None
    return state
```

### `app.py` — UI Update (Stage-Driven Rendering)

Replace the placeholder section with stage-driven rendering. Keep the existing structure above `st.divider()` unchanged.

```python
# ── Stage-driven content rendering ────────────────────────────────────────
state = st.session_state.state
current_stage = state["pipeline_stage"]

# Show error banner if set (cleared on next successful action)
if state.get("error_message"):
    st.error(state["error_message"])

if current_stage in ("spec_ingestion", "spec_parsed"):
    # Next required action area (UX-DR2)
    if not state.get("parsed_api_model"):
        st.info("**Next:** Upload your OpenAPI/Swagger spec (JSON or YAML) to begin.")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload OpenAPI/Swagger spec",
        type=["json", "yaml", "yml"],
        help="Supports OpenAPI 3.0 in JSON or YAML format",
    )

    if uploaded_file is not None:
        raw_spec = uploaded_file.read().decode("utf-8")
        # Update state and invoke parse_spec node directly
        state["spec_source"] = "file"
        state["raw_spec"] = raw_spec
        updated_state = parse_spec(state)
        st.session_state.state = updated_state
        st.rerun()

    # Show parse results
    model = state.get("parsed_api_model")
    if model:
        n = len(model.get("endpoints", []))
        st.success(f"Found {n} endpoint{'s' if n != 1 else ''}  — '{model.get('title', 'API')}'")
        # AC: pipeline advanced — next story (1.3/1.4) will handle the next stage UI
        st.info("**Next:** Proceed to gap detection (Story 1.4) or URL import (Story 1.3).")
```

**Import to add at top of `app.py`:**
```python
from app.pipeline import parse_spec
```

### Project Structure — New and Modified Files

```
sata/
├── app.py                          # MODIFIED: replace placeholder, add file uploader
├── app/
│   ├── pipeline.py                 # MODIFIED: parse_spec stub → real implementation
│   └── utils/
│       └── spec_parser.py          # NEW: parse_openapi_spec() + helpers
├── requirements.txt                # MODIFIED: add PyYAML, openapi-spec-validator
└── tests/
    ├── test_spec_parser.py         # NEW: unit tests for parser
    └── test_parse_spec_node.py     # NEW: unit tests for pipeline node
```

**DO NOT create**: any new pipeline nodes, no new state fields, no new modules beyond `spec_parser.py`.

### Test Fixtures — Minimal Valid OpenAPI 3.0 Spec

Use this in tests to avoid coupling tests to external files:

```python
MINIMAL_OPENAPI_JSON = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List users",
                "parameters": [
                    {"name": "limit", "in": "query", "required": False,
                     "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "OK"}}
            }
        }
    }
})

MINIMAL_OPENAPI_YAML = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      responses:
        "200":
          description: OK
"""
```

### Routing After Parse — Zero Endpoints Edge Case

`_route_after_parse` (already in `pipeline.py`) routes to `fill_gaps` if `parsed_api_model.endpoints` is empty. **Do not change this router.** For Story 1.2, we only implement `parse_spec`. The zero-endpoint fallback to conversational mode is Story 1.5's responsibility.

### Security Constraints (NFR6–NFR8 — Never Violate)

- Never log `raw_spec` content to console or display in Streamlit widgets — specs may contain secrets
- `state["raw_spec"]` should be cleared or left as-is after parsing; do not render it in the UI
- `state["error_message"]` is safe to display — it must never include raw file content

### Dependencies: What Story 1.2 Builds On

- `app/state.py` → `SataState`, `initial_state()` — import as-is, do NOT modify
- `app/pipeline.py` → only replace `parse_spec` and optionally set `pipeline_stage` in `ingest_spec`; all other nodes remain stubs
- `app/utils/env.py` → `validate_env()` — untouched
- `app.py` → keep `validate_env()`, `initial_state()`, `build_pipeline()`, and stage header; only replace placeholder section

### References

- `parsed_api_model` shape: FR3 — "extract endpoints, methods, parameters, request/response schemas, and auth" [Source: epics.md#Story 1.2]
- YAML support: NFR11 — "OpenAPI/Swagger 3.0 spec format (JSON and YAML)" [Source: epics.md#NonFunctional Requirements]
- Error handling: NFR2 — "each LangGraph node handles errors gracefully so a single failed test case does not crash" [Source: epics.md#NonFunctional Requirements]
- Stage header + next required action: UX-DR1, UX-DR2 [Source: ux-design-specification.md#Platform Strategy]
- Fallback to conversational mode: FR41, Story 1.5 (not in scope here) [Source: epics.md#Story 1.5]
- Auth types (bearer, api_key): FR18 [Source: epics.md#Story 4.1 / prd.md#MVP Feature Set]
- Security: NFR6–NFR8 [Source: prd.md#Non-Functional Requirements]

## Review Findings

- [x] `Review/Decision` — `openapi-spec-validator` added to requirements but never imported or called — **fixed**: imported and used in `_validate_structure` (Auditor)
- [x] `Review/Decision` — `$ref` in parameters/responses/requestBody silently produces null/empty data — **fixed**: `_resolve_ref()` added, all extraction helpers resolve internal `$ref`s (Edge)
- [x] `Review/Decision` — `oauth2`/`openIdConnect` security schemes return null auth object — **fixed**: named type stubs added; full implementation deferred to Story 4.1 (Blind+Edge)
- [x] `Review/Patch` — Float `openapi` version crashes `_validate_structure` on YAML `openapi: 3.0` (unquoted) — **fixed**: `str()` wrap added — `app/utils/spec_parser.py`
- [x] `Review/Patch` — `path_item` not dict-guarded — `paths: null` or null path item causes `AttributeError` — **fixed**: `isinstance` guard + `paths or {}` — `app/utils/spec_parser.py`
- [x] `Review/Patch` — `info: null` causes `AttributeError` on `.get()` call — **fixed**: `info = spec.get("info") or {}` — `app/utils/spec_parser.py`
- [x] `Review/Patch` — `decode("utf-8")` crashes unhandled on non-UTF-8 or UTF-8-BOM encoded uploads — **fixed**: `decode("utf-8-sig")` with `UnicodeDecodeError` catch — `app.py`
- [x] `Review/Patch` — Streamlit infinite re-render loop — **fixed**: gate on `not state.get("parsed_api_model")` — `app.py`
- [x] `Review/Patch` — YAML unquoted `version: 1.0` parsed as float, canonical model receives float not str — **fixed**: `str()` wrap on version — `app/utils/spec_parser.py`
- [x] `Review/Patch` — Duplicate path+operation parameters concatenated instead of operation-level overriding path-level — **fixed**: `_extract_parameters` deduplicates by `(name, in)` key — `app/utils/spec_parser.py`
- [x] `Review/Patch` — PyYAML `YAMLError` messages echoed into `error_message` can include raw spec content, violating NFR6-NFR8 — **fixed**: sanitized to generic message; bare `except Exception` in pipeline also sanitized — `app/utils/spec_parser.py`, `app/pipeline.py`
- [x] `Review/Patch` — `test_malformed_spec_sets_error` relies on `initial_state()` default — **fixed**: `test_failure_resets_stage_from_spec_parsed` added — `tests/test_parse_spec_node.py`
- [x] `Review/Defer` — `_route_after_parse` stub unconditionally returns `detect_gaps`, never routes to `fill_gaps` on zero endpoints — `app/pipeline.py:99-101` — Story 1.5 scope
- [x] `Review/Defer` — Stub routers create infinite loop (`analyze_results → review_results → analyze_results`) — `app/pipeline.py:119-121` — pre-existing stubs, not story 1.2 scope
- [x] `Review/Defer` — Explicit `security: []` per-operation opt-out loses semantic distinction from "no security declared" — `app/utils/spec_parser.py:85` — Story 1.4 gap-detection concern
- [x] `Review/Defer` — `auth_required: True` with `auth.type: None` contradiction when `securitySchemes` absent — `app/utils/spec_parser.py:151-173` — Story 4.1 scope

## Change Log

- 2026-03-31: Implemented full OpenAPI/Swagger file upload and parsing — all 6 tasks complete, 31 new tests added, 112 total tests passing.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (Thinking)

### Debug Log References

- All 112 tests pass (0 regressions)
- Dependencies `PyYAML>=6.0.0` and `openapi-spec-validator>=0.7.0` installed successfully

### Completion Notes List

- ✅ Task 1: Added PyYAML and openapi-spec-validator to requirements.txt; pip install verified
- ✅ Task 2: Created `app/utils/spec_parser.py` with `parse_openapi_spec()`, `_extract_endpoints()`, `_extract_auth()`, `_extract_parameters()`, `_extract_request_body()`, `_extract_responses()` — all following canonical `parsed_api_model` schema exactly
- ✅ Task 3: Replaced `parse_spec` stub in pipeline.py — populates `parsed_api_model` on success, sets `error_message` on failure, never raises (NFR2)
- ✅ Task 4: Updated `ingest_spec` node to set `pipeline_stage = "spec_ingestion"` — router unchanged as specified
- ✅ Task 5: Replaced placeholder in app.py with stage-driven file upload UI — file uploader for JSON/YAML/YML, success message with endpoint count, error banner, next-action prompts (UX-DR2)
- ✅ Task 6: Created 22 tests in `test_spec_parser.py` (valid JSON/YAML parse, multi-endpoint, auth extraction, error handling, canonical schema compliance) and 9 tests in `test_parse_spec_node.py` (valid state, missing/empty raw_spec, malformed spec, never-raises, error clearing)

### File List

- `requirements.txt` — MODIFIED: added PyYAML>=6.0.0, openapi-spec-validator>=0.7.0
- `app/utils/spec_parser.py` — NEW: OpenAPI/Swagger parsing utility
- `app/pipeline.py` — MODIFIED: replaced parse_spec and ingest_spec stubs with real implementations
- `app.py` — MODIFIED: replaced placeholder with stage-driven file upload UI
- `tests/test_spec_parser.py` — NEW: 22 unit tests for spec parser
- `tests/test_parse_spec_node.py` — NEW: 9 unit tests for parse_spec pipeline node
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED: story status updated
