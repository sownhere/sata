# Story 4.1: HTTP Test Execution with Auth & Retry

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the system to execute all confirmed test cases as real HTTP requests against my target API, with proper auth handling, retry logic, and visible progress,
so that I get accurate results without managing the execution loop manually.

## Acceptance Criteria

1. **Given** the test plan is confirmed and the user triggers execution, **when** the `execute_tests` node runs, **then** a progress indicator shows how many tests have completed vs. total (e.g., "14 / 38 tests run"), **and** the Streamlit UI does not freeze (browser tab stays responsive via spinner/status).

2. **Given** a test case requires Bearer token authentication, **when** the HTTP request is built, **then** the token is included in the `Authorization: Bearer <token>` header, **and** the token is never sent to the LLM or written to any log or UI element.

3. **Given** a test case requires API key authentication, **when** the HTTP request is built, **then** the key is included in the correct header or query param as defined by `parsed_api_model["auth"]`, **and** the key is never logged or displayed in the UI.

4. **Given** a test case HTTP request fails with a network/connection error, **when** the first attempt fails, **then** the system retries once before marking the test as failed, **and** the `attempt_count` field in the result records whether retrying occurred.

5. **Given** the target API is completely unreachable (first test gets a `ConnectionError` or `ConnectTimeout`), **when** the failure is detected, **then** execution halts with `error_message = "Target API is unreachable — check the URL and your connection"`, **and** partial results (if any) are stored, **and** the user is shown the error with a "Retry" option.

6. **Given** `iteration_count` reaches `settings.pipeline.max_iterations`, **when** a node tries to execute another test case, **then** execution stops for that node, **and** `error_message` records why execution stopped early.

7. **Given** individual test cases execute, **when** each completes, **then** the result is appended to `state["test_results"]` with: `test_id`, `test_title`, `endpoint_method`, `endpoint_path`, `actual_status_code`, `actual_response_body`, `error_message`, and `attempt_count`.

## Tasks / Subtasks

- [x] Task 1: Add `target_api_url` field to `SataState` and update env example (AC: 5)
  - [ ] In `src/core/state.py`, add `target_api_url: Optional[str]` under the `# ── Execution` section, above `test_results`.
  - [ ] In `initial_state()`, add `target_api_url=None`.
  - [ ] Update `tests/unit/test_state.py` and `tests/unit/test_core_state.py`: add `target_api_url` to the instantiation dicts and required-keys lists; update the key count from 21 → 22.
  - [ ] Add `TARGET_API_URL`, `API_BEARER_TOKEN`, and `API_KEY` to `.env.example` as optional/commented-out entries with brief explanations.

- [x] Task 2: Create `src/tools/http_executor.py` with auth building and request execution (AC: 2, 3, 4, 5, 7)
  - [ ] Add `get_auth_headers(auth_config: dict | None) -> dict` — reads credentials from env only (`os.environ.get("API_BEARER_TOKEN")` for bearer, `os.environ.get("API_KEY")` for apiKey type). Returns `{"Authorization": "Bearer <token>"}` for bearer type. Returns `{name: key}` in the correct header for apiKey+header location, or an empty dict plus a note if credential is absent. Never accepts credentials as function arguments (security boundary).
  - [ ] Add `build_request_url(base_url: str, endpoint_path: str, path_params: dict | None = None) -> str` — strips trailing slash from `base_url`, substitutes `{param}` placeholders from `path_params`, returns full URL string.
  - [ ] Add `execute_single_test(test_case: dict, base_url: str, auth_headers: dict, timeout: int, retry_count: int) -> dict` — builds URL using `build_request_url`; extracts `body` from `test_case["request_overrides"].get("body", {})`, `query_params` from `test_case["request_overrides"].get("query_params", {})`, `extra_headers` from `test_case["request_overrides"].get("headers", {})`; merges auth_headers and extra_headers; sends request via `httpx.request(method, url, ...)` with the configured timeout; on `httpx.RequestError`: retries once if `retry_count >= 1`; returns dict `{test_id, test_title, endpoint_method, endpoint_path, actual_status_code, actual_response_body, error_message, attempt_count}`.
  - [ ] `actual_response_body` should be the parsed JSON dict if response is JSON (Content-Type: application/json), otherwise the response text truncated to 2000 chars. Never store raw bytes.
  - [ ] For `actual_status_code`: the HTTP status integer on success, `None` on unrecoverable network error.
  - [ ] Add unit tests in `tests/unit/test_http_executor.py` using `unittest.mock.patch` on `httpx.request` (no real network calls). Test: (a) bearer auth header is set correctly, (b) apiKey header auth is set correctly, (c) query-param apiKey is NOT added as a header (no apiKey support in query params for 4.1 — `get_auth_headers` returns `{}` and a warning for non-header apiKey), (d) retry fires once on `httpx.RequestError`, (e) `build_request_url` substitutes path params, (f) successful response stores status code and JSON body.

- [x] Task 3: Implement `execute_tests` node (AC: 1, 2, 3, 4, 5, 6, 7)
  - [ ] Replace the stub in `src/nodes/execute_tests.py` with real logic:
    - Guard: if `not state.get("test_plan_confirmed")` → set `error_message`, return.
    - Guard: if not `state.get("target_api_url", "").strip()` → set `error_message = "Target API URL is required — set TARGET_API_URL in .env"`, return.
    - Guard: if `not state.get("test_cases")` → set `error_message = "No confirmed test cases to execute."`, return.
    - Load settings via `get_settings()` from `src.core.config`.
    - Build auth_headers via `get_auth_headers(state.get("parsed_api_model", {}).get("auth"))`.
    - Loop over `state["test_cases"]`, incrementing `state["iteration_count"]` each iteration; if `iteration_count >= settings.pipeline.max_iterations`, set `error_message = f"Execution halted: reached max_iterations ({settings.pipeline.max_iterations})"` and break.
    - Call `execute_single_test(test_case, base_url, auth_headers, timeout, retry_count)` for each test case.
    - **Unreachable API detection:** if the first result has `actual_status_code is None` AND `error_message` contains a connection-failure phrase, set `state["error_message"] = "Target API is unreachable — check the URL and your connection"` and break.
    - Append each result to a local `results` list; after loop set `state["test_results"] = results`.
    - Always set `state["pipeline_stage"] = "execute_tests"` (keep at this stage — Stories 4.2–4.4 will advance it).
    - Clear `state["error_message"]` to None on clean completion (all tests attempted without network halt).
  - [ ] Import path: `from src.tools.http_executor import execute_single_test, get_auth_headers` and `from src.core.config import get_settings`.
  - [ ] Add integration tests in `tests/integration/test_pipeline.py`:
    - `test_execute_tests_requires_target_api_url` — state without `target_api_url` set → node returns with error_message set.
    - `test_execute_tests_requires_test_plan_confirmed` — state without `test_plan_confirmed=True` → error.
    - `test_execute_tests_populates_test_results` — mock `execute_single_test` to return fake results; assert `state["test_results"]` is populated and matches expected structure.

- [x] Task 4: Update `execute_tests` UI stage in `app.py` (AC: 1, 5)
  - [ ] Replace the existing placeholder `elif current_stage == "execute_tests":` block with:
    - If `state.get("test_results")` is not None: show summary — `st.success` with test count, `st.info` that analysis is coming in Epic 4, and a `st.dataframe` of results (columns: test_id, endpoint_method, endpoint_path, actual_status_code, error_message).
    - If `state.get("test_results")` is None AND `state.get("error_message")`: show `st.error(state["error_message"])` with a "Retry" button that re-calls `run_pipeline_node(state, "execute_tests")`.
    - If `state.get("test_results")` is None AND no error: show target URL input (`st.text_input`, key `"target_api_url_input"`, pre-filled from `state.get("target_api_url", "")`) and a "Run Tests" button. On click: set `state["target_api_url"] = url_input.strip()`, run node via spinner (`st.spinner("Running tests...")`), store result, rerun.
  - [ ] Token/key credentials are NEVER rendered in the UI — only show "Bearer token from API_BEARER_TOKEN" or "API key from API_KEY" as labels. Never call `os.environ.get("API_BEARER_TOKEN")` from app.py.

## Dev Notes

### Previous Story Handoff (Story 3.3)

At Checkpoint 2 completion:
- `state["test_plan_confirmed"] == True`
- `state["test_cases"]` is the final filtered execution set (destructive acknowledged)
- `state["pipeline_stage"] == "execute_tests"`
- `state["target_api_url"]` is `None` — Task 1 adds this field, Task 4 UI collects it

### HTTP Library: `httpx` 0.28.1 (Already Available)

`httpx` is already in the environment (transitively via `langchain-openai`). Do NOT add it to `pyproject.toml`. Use `import httpx` directly.

Key `httpx` API for this story:
```python
import httpx

# Sync request with timeout
try:
    response = httpx.request(
        method="GET",
        url="https://api.example.com/users",
        headers={"Authorization": "Bearer token"},
        json={"key": "value"},   # body (POST/PUT)
        params={"page": 1},       # query params
        timeout=30,
    )
    status_code = response.status_code
    body = response.json()  # or response.text for non-JSON
except httpx.RequestError as exc:
    # Network error, connection refused, DNS failure, timeout
    ...
except httpx.HTTPStatusError:
    # This is NOT raised by default — only if .raise_for_status() called
    ...
```

`httpx.RequestError` covers: `ConnectError`, `TimeoutException`, `ReadError`, etc. Unreachable API raises `httpx.ConnectError`.

Check Content-Type for JSON:
```python
is_json = "application/json" in response.headers.get("content-type", "")
body = response.json() if is_json else response.text[:2000]
```

### Auth Model Contract

`parsed_api_model["auth"]` is a dict (serialized `AuthModel`). Key fields:
- `type`: `"bearer"` | `"apiKey"` | `None`
- `location` (aliased as `"in"` in OpenAPI): `"header"` | `"query"`
- `name`: header/query param name (e.g., `"Authorization"`, `"X-API-Key"`)

```python
# Example auth dicts from state:
# Bearer: {"type": "bearer", "scheme": "Bearer", "in": None, "name": "Authorization"}
# ApiKey: {"type": "apiKey", "scheme": None, "in": "header", "name": "X-Api-Key"}
```

**IMPORTANT:** `AuthModel` uses `alias="in"` for the `location` field. When serialized to dict via `model_dump()`, it outputs `"location"` (not `"in"`) unless `by_alias=True` is used. When reading from `parsed_api_model["auth"]` dict in state, check both `"location"` and `"in"` keys for robustness.

**Credential lookup:**
```python
# get_auth_headers reads from env only — never as function parameters
import os
bearer_token = os.environ.get("API_BEARER_TOKEN", "").strip()
api_key = os.environ.get("API_KEY", "").strip()
```

### test_results Format (Story 4.1 Contract)

Each entry in `state["test_results"]`:
```python
{
    "test_id": str,              # matches test_case["id"]
    "test_title": str,           # test_case["title"]
    "endpoint_method": str,      # "GET", "DELETE", etc.
    "endpoint_path": str,        # "/users/{id}"
    "actual_status_code": int | None,   # None on unrecoverable network error
    "actual_response_body": dict | str | None,  # JSON dict or text[:2000] or None
    "error_message": str | None, # description of network failure if any
    "attempt_count": int,        # 1 (first try) or 2 (retried)
}
```

**Story 4.2 extends this with:** `expected_status_code`, `passed`, `validation_errors`.
Do NOT add those fields in Story 4.1.

### request_overrides Convention

`TestCaseModel.request_overrides` is a freeform dict generated by the LLM. Honour these keys:
```python
overrides = test_case.get("request_overrides") or {}
path_params = overrides.get("path_params") or {}   # {"id": "123"}
body = overrides.get("body") or {}                 # JSON body for POST/PUT
query_params = overrides.get("query_params") or {} # {"filter": "active"}
extra_headers = overrides.get("headers") or {}     # {"Accept": "application/json"}
```

### Architecture Compliance

- **Dependency rule:** `src/tools/http_executor.py` → may import from `src.core.config` only. No imports from `src.nodes` or `src.ui`.
- **Security boundary:** auth credentials are read inside `get_auth_headers` from `os.environ` only. The function signature MUST NOT accept a credential as a parameter. This prevents credentials leaking through call chains or LLM reasoning logs.
- **No credential display in UI:** `app.py` never calls `os.environ.get("API_BEARER_TOKEN")`. The UI only says "Bearer token configured" or "No Bearer token found — set API_BEARER_TOKEN in .env".
- **Logging:** no print statements or log calls that include auth headers or request body (could expose secrets).
- **No LLM calls:** `execute_tests` node is fully deterministic — no LangChain/Gemini calls. All work in `src/tools/http_executor.py`.

### State Fields Added by This Story

One new field in `SataState`:
- `target_api_url: Optional[str]` — base URL of target API (e.g., `"https://api.example.com"`). Collected via UI before execution. After this story, state has **22 required keys** (was 21 after Story 3.2).

### Performance & Iteration Guard

From `settings.execution`:
- `request_timeout_seconds: int = 30` — per-request timeout
- `retry_count: int = 1` — how many retries on network error

From `settings.pipeline`:
- `max_iterations: int = 10` — node iteration limit (anti-infinite-loop, NFR5)

Increment `state["iteration_count"]` once per test case. If `iteration_count >= max_iterations` → halt.

### Project Structure Notes

**Add:**
- `src/tools/http_executor.py`
- `tests/unit/test_http_executor.py`

**Modify:**
- `src/core/state.py` — add `target_api_url`
- `src/nodes/execute_tests.py` — replace stub with real implementation
- `app.py` — update `execute_tests` stage block
- `tests/unit/test_state.py` — add field to instantiation dicts, update key count
- `tests/unit/test_core_state.py` — add field to instantiation dicts, update key count
- `tests/integration/test_pipeline.py` — add 3 new tests
- `.env.example` — add TARGET_API_URL, API_BEARER_TOKEN, API_KEY

**Do NOT modify:**
- `src/core/models.py` — TestCaseModel is correct as-is
- `src/core/config.py` — ExecutionSettings already has timeout/retry
- `src/core/graph.py` — routing already correct
- `pyproject.toml` — httpx is already available transitively

### Testing Requirements

- `test_http_executor.py` must mock `httpx.request` — no real network calls.
- `test_pipeline.py` integration tests must mock `execute_single_test` — no real network calls.
- All tests deterministic and offline.
- Keep existing 194 tests passing.

### Risks & Guardrails

- **Do NOT read credentials in `app.py`** — only `get_auth_headers()` in `http_executor.py` reads from env.
- **Do NOT add `httpx` to `pyproject.toml`** — it's already available transitively; adding it would be redundant.
- **Do NOT implement response schema validation** — that is Story 4.2. For 4.1, record `actual_status_code` and `actual_response_body` only.
- **Do NOT implement failure analysis or pattern detection** — Story 4.3.
- **Do NOT implement all-pass/all-fail diagnosis** — Story 4.4.
- **Handle `httpx.ConnectError` specifically** for unreachable API detection — not all `RequestError` subclasses indicate unreachable API.
- **Path params in test cases may be missing** — if `path_params` is empty, leave `{param}` placeholders as-is; the request will fail naturally and result will capture the error.
- **Do NOT advance `pipeline_stage` past `"execute_tests"`** in this story — Analysis stage is Story 4.2/4.3.

### References

- `httpx` sync API: [httpx.dev/quickstart](https://www.python-httpx.org/quickstart/)
- Auth model: [`src/core/models.py`, `AuthModel` — note `alias="in"` for `location` field]
- Settings: [`src/core/config.py`, `ExecutionSettings`, `PipelineSettings`]
- State contract: [`src/core/state.py`]
- TestCaseModel: [`src/core/models.py`, `TestCaseModel`]
- Previous story: [`_bmad-output/implementation-artifacts/3-3-test-plan-confirmation-and-rejection-checkpoint.md`]
- Execute_tests stub (current): [`src/nodes/execute_tests.py`]
- Graph routing: [`src/core/graph.py`, `_route_test_plan`, linear edge `execute_tests → analyze_results`]
- Architecture NFR5 (iteration limit), NFR6–NFR8 (auth security), NFR12–NFR14 (performance): [`_bmad-output/planning-artifacts/architecture.md`]
- PRD FR17–FR21: [`_bmad-output/planning-artifacts/prd.md`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Python 3.9 doesn't support `dict | None` union syntax — used `Optional[dict]` from typing throughout.
- `patch("src.nodes.execute_tests.execute_single_test")` fails due to `__init__.py` re-exporting `execute_tests` function as `src.nodes.execute_tests` attribute — resolved with `importlib.import_module` + `patch.object`.

### Completion Notes List

- 215 tests passing (up from 194).
- `get_auth_headers` reads from env only — credentials never flow through call chains.
- Query-param apiKey (location=query) returns empty dict (not supported in 4.1 per story spec).
- Unreachable API detection keys on connection-related substrings in the first result's error_message.

### File List

- `src/core/state.py`
- `src/nodes/execute_tests.py`
- `src/tools/http_executor.py`
- `app.py`
- `tests/unit/test_state.py`
- `tests/unit/test_core_state.py`
- `tests/unit/test_http_executor.py`
- `tests/integration/test_pipeline.py`
- `.env.example`
- `_bmad-output/implementation-artifacts/4-1-http-test-execution-with-auth-and-retry.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log
