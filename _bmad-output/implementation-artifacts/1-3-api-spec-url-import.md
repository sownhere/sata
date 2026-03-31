# Story 1.3: API Spec URL Import

Status: review

## Story

As a developer,
I want to provide a URL pointing to a public OpenAPI spec,
so that the system fetches and parses it without requiring me to download the file manually.

## Acceptance Criteria

1. **Given** the developer enters a valid URL to a publicly accessible OpenAPI 3.0 JSON or YAML spec, **when** they submit the URL, **then** the system fetches the spec and passes it through the same parser as Story 1.2, and `SataState` is populated identically to a file upload.

2. **Given** the entered URL is unreachable or returns a non-200 response, **when** the fetch fails, **then** a clear error message is displayed (for example, "Could not reach URL - check the address or your connection"), and the user can retry with a different URL without restarting the app.

3. **Given** the URL returns a non-OpenAPI document such as an HTML page, **when** parsing fails, **then** the system displays a specific error distinguishing a fetch failure from a parse failure.

## Tasks / Subtasks

- [x] Task 1: Add URL fetch support without introducing unnecessary dependencies (AC: 1, 2, 3)
  - [x] Create `app/utils/spec_fetcher.py` with `fetch_spec_from_url(url: str) -> str`
  - [x] Use Python standard library networking (`urllib.request` / `urllib.error`) rather than adding `requests` or `httpx`
  - [x] Validate the URL is `http` or `https` before making the request
  - [x] Raise `ValueError` with user-safe messages for invalid URL, network failure, timeout, and non-200 responses
  - [x] Decode response bodies as UTF-8 with graceful fallback handling; never include response body content in error messages

- [x] Task 2: Reuse the existing parsing path from Story 1.2 (AC: 1, 3)
  - [x] Do not duplicate JSON/YAML/OpenAPI parsing logic in the new fetcher
  - [x] After a successful fetch, set `state["spec_source"] = "url"` and `state["raw_spec"] = fetched_content`
  - [x] Call the existing `parse_spec(state)` node so `parsed_api_model`, `pipeline_stage`, and parser-side error handling stay consistent with file upload behavior
  - [x] Preserve the canonical `parsed_api_model` shape established in Story 1.2 exactly

- [x] Task 3: Update the Spec Ingestion UI to support URL import alongside file upload (AC: 1, 2, 3)
  - [x] In `app.py`, keep the stage-header-driven rendering for `spec_ingestion` and `spec_parsed`
  - [x] Add a URL input control and explicit submit action near the existing upload UI
  - [x] Show helper copy that this field expects a public OpenAPI 3.0 JSON or YAML URL
  - [x] On submit: fetch first, then parse through `parse_spec`, then store the updated state in `st.session_state.state`
  - [x] On fetch failure: surface a fetch-specific `st.error(...)` message and do not call `parse_spec`
  - [x] On parse failure after a successful fetch: surface the parser error so users can distinguish "URL reachable but document invalid" from "URL could not be reached"
  - [x] Keep retry UX simple: the user can edit the URL and resubmit immediately without restarting the app

- [x] Task 4: Keep pipeline and state conventions intact (AC: 1)
  - [x] Do not add new LangGraph nodes for URL import
  - [x] Do not redefine `SataState`; reuse `spec_source`, `raw_spec`, `parsed_api_model`, `pipeline_stage`, and `error_message`
  - [x] Leave `_route_after_ingest` unchanged because file/URL inputs already route to `parse_spec`
  - [x] Ensure successful URL parsing leaves the app in the same `spec_parsed` state as a successful file upload

- [x] Task 5: Add focused automated tests for fetch and integration behavior (AC: 1, 2, 3)
  - [x] Add `tests/test_spec_fetcher.py` covering valid fetch, invalid scheme, timeout/network error, non-200 response, and decode handling
  - [x] Mock standard-library URL access in tests; do not rely on live network calls
  - [x] Add or extend tests to verify a successful fetched spec passed into `parse_spec` yields the same model shape as file upload
  - [x] Add a test case proving fetch failures are reported separately from parse failures

## Dev Notes

### Previous Story Intelligence

- Story 1.2 already established the canonical parsing path:
  - `app/utils/spec_parser.py` owns JSON/YAML/OpenAPI parsing
  - `app.pipeline.parse_spec()` owns state mutation on parse success/failure
  - `app.py` currently invokes `parse_spec(state)` directly from the ingestion UI
- Do not fork or partially reimplement that flow for URL import. URL import should only add a fetch step before the same parse path.
- Story 1.2 explicitly warns against introducing unnecessary new modules or state fields when existing structure already covers the need. For Story 1.3, one small fetch utility is justified; broader pipeline refactors are not.

### Current Codebase Conventions To Follow

- `app/state.py`
  - `SataState` already supports `spec_source: "file" | "url" | "chat"` and `raw_spec`
  - No new state fields are needed for this story
- `app/pipeline.py`
  - `parse_spec()` never raises and clears/sets `error_message` appropriately
  - `_route_after_ingest()` already routes non-chat ingestion to `parse_spec`
- `app.py`
  - Uses stage-driven rendering and direct node invocation from the UI
  - Error banners are shown via `state["error_message"]`
- `tests/`
  - Existing tests use small inline fixtures and unit-level mocking rather than external network resources

### Implementation Guidance

- Preferred fetch helper signature:

```python
def fetch_spec_from_url(url: str) -> str:
    """Return raw spec text fetched from a public URL or raise ValueError."""
```

- Recommended behavior for `fetch_spec_from_url()`:
  - Parse with `urllib.parse.urlparse`
  - Reject non-`http`/`https` schemes with a clear message
  - Use a bounded timeout
  - Treat HTTP errors and transport errors as fetch failures
  - Return decoded response text only on success
  - Do not attempt HTML detection inside the fetcher; let `parse_spec()` / `parse_openapi_spec()` own document validation so failure boundaries stay clean

- Recommended UI flow in `app.py`:
  - Keep the existing file uploader intact
  - Add a separate URL import section with a text input and button
  - On button press:
    - call `fetch_spec_from_url(url)`
    - on success set `spec_source` and `raw_spec`
    - call `parse_spec(state)`
    - persist `st.session_state.state = updated_state`
    - `st.rerun()`
  - On fetch error:
    - set or show a clear fetch-specific error
    - leave any existing parsed model untouched unless intentionally resetting for retry

### Architecture Compliance

- Follow the existing Streamlit-first architecture; this story extends the local app UI, not the graph topology.
- Preserve the single-source-of-truth rule around `SataState`.
- Maintain graceful failure handling so a bad URL or bad response cannot crash the app.
- Continue enforcing the security boundary: URL-imported content may be stored in `raw_spec` temporarily for parsing, but must never be logged or rendered back to the user.

### File Structure Requirements

- Modify:
  - `app.py`
- Add:
  - `app/utils/spec_fetcher.py`
  - `tests/test_spec_fetcher.py`
- Reuse as-is:
  - `app/pipeline.py`
  - `app/state.py`
  - `app/utils/spec_parser.py`
- Avoid adding unrelated modules, service layers, or dependencies for this story.

### Testing Requirements

- Keep tests deterministic and offline.
- Mock all URL fetches; no live PetStore/ReqRes/JSONPlaceholder calls in unit tests.
- Cover both categories of failure explicitly:
  - fetch failed before parse
  - fetch succeeded but parse failed
- Verify that a URL-imported valid spec produces the same downstream `parsed_api_model` shape and `pipeline_stage == "spec_parsed"` behavior as file upload.

### Risks And Guardrails

- Regression risk: accidentally duplicating parser logic in the fetch path can create divergence between file-upload parsing and URL-import parsing.
- UX risk: if both fetch and parse failures collapse into one generic message, the user will not know whether the URL is wrong or the document is invalid.
- Security risk: never echo remote response bodies or secrets in errors, logs, or Streamlit widgets.
- Scope risk: Story 1.3 is only public spec URL import. Conversational fallback for zero endpoints remains Story 1.5.

### References

- Story requirements and acceptance criteria: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Existing parser and canonical model contract: [Source: `_bmad-output/implementation-artifacts/1-2-openapi-swagger-file-upload-and-parsing.md`]
- `SataState` supports `spec_source == "url"` already: [Source: `app/state.py`]
- Current ingestion and parse flow: [Source: `app.py`], [Source: `app/pipeline.py`]
- Streamlit stage/next-action UX: [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`]
- Security and reliability NFRs: [Source: `_bmad-output/planning-artifacts/prd.md`]

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story created from sprint backlog auto-discovery (`1-3-api-spec-url-import`)
- Prior implementation context loaded from Story 1.2 and current codebase modules
- `pytest -q tests/test_spec_fetcher.py tests/test_parse_spec_node.py` → 17 passed
- `pytest -q` → 120 passed
- `ReadLints` on edited files → no linter errors

### Completion Notes List

- Story file created with implementation tasks, codebase-specific guardrails, and focused testing guidance
- Reuse of the existing parse path called out explicitly to avoid duplicated ingestion behavior
- Error-boundary guidance added so fetch failures and parse failures stay distinguishable in the UI
- Implemented `app/utils/spec_fetcher.py` using `urllib` only, with URL validation, non-200 handling, timeout/network error handling, and safe UTF-8 decoding
- Updated `app.py` to add a public URL import flow alongside file upload while reusing `parse_spec(state)` for all parsing/state mutation
- Added `tests/test_spec_fetcher.py` and expanded `tests/test_parse_spec_node.py` to cover URL-import parity and fetch-vs-parse error separation
- Full regression suite passes with no linter issues

### File List

- `_bmad-output/implementation-artifacts/1-3-api-spec-url-import.md`
- `app.py`
- `app/utils/spec_fetcher.py`
- `tests/test_spec_fetcher.py`
- `tests/test_parse_spec_node.py`

## Review Findings

- [ ] `Review/Decision` — SSRF: no private IP / localhost / cloud-metadata address blocking — URL scheme check is insufficient for server-deployed context (Blind+Edge)
- [ ] `Review/Decision` — HTTP redirect can silently downgrade HTTPS→HTTP, transmitting spec content unencrypted (Blind)
- [ ] `Review/Patch` — `TimeoutError` check is dead code on Python 3.9 (the runtime); `socket.timeout` is not a subclass of `TimeoutError` until 3.11; bare `socket.timeout` also uncaught — `app/utils/spec_fetcher.py:47-53`
- [ ] `Review/Patch` — No response body size limit — `response.read()` with no cap can exhaust memory on large/malicious responses — `app/utils/spec_fetcher.py:41`
- [ ] `Review/Patch` — Fetch error path missing `st.rerun()` — error banner timing inconsistent with file-upload path — `app.py:77-79`
- [ ] `Review/Patch` — Empty URL field not guarded in `app.py` — every button click with blank input writes an error to session state — `app.py:74`
- [ ] `Review/Patch` — `getattr(response, "status", 200)` default of `200` silently passes through when attribute absent — should default to `None` — `app/utils/spec_fetcher.py:36`
- [ ] `Review/Patch` — Stale `error_message` from previous attempt not cleared at start of new fetch — `app.py:74`
- [ ] `Review/Patch` — Fetch failure and parse failure produce indistinguishable plain-string errors in UI — violates AC3 — `app.py:58,77-85`
- [ ] `Review/Patch` — Missing test: HTML/non-OpenAPI body returned after successful fetch (AC3 scenario) — `tests/test_spec_fetcher.py`
- [ ] `Review/Patch` — Missing test: empty string URL input — `tests/test_spec_fetcher.py`
- [x] `Review/Defer` — Concurrent double-click submits two requests — pre-existing Streamlit architectural limitation, no state lock — `app.py:74`
- [x] `Review/Defer` — Slow-loris (per-recv timeout does not bound total read time) — partially mitigated by response size cap patch — `app/utils/spec_fetcher.py:41`

## Change Log

- 2026-03-31: Implemented API spec URL import using a standard-library fetcher, wired the ingestion UI to reuse the existing parse path, and added offline tests for fetch behavior and URL-import parsing parity.
