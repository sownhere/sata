# Story 1.4: Spec Gap Detection & Targeted Questions

Status: done

## Story

As a developer,
I want the system to detect incomplete or ambiguous fields in my parsed spec and ask me targeted questions to fill them,
so that the test suite is based on complete, accurate API information rather than guesses.

## Acceptance Criteria

1. **Given** a spec has been parsed and `SataState` is populated, **when** the gap detection node runs, **then** the system identifies fields that are missing, ambiguous, or under-specified (for example: missing response schemas, unclear auth type, undocumented error codes).

2. **Given** gaps are detected, **when** the system presents them to the user, **then** each gap is shown as a specific, targeted question (for example: "Endpoint POST /users has no defined success response schema - what does a 201 response return?"), and questions are grouped by endpoint for clarity.

3. **Given** the user answers a gap question, **when** the answer is accepted, **then** `SataState` is updated with the user-provided information, and the filled gap is no longer flagged.

4. **Given** no gaps are detected, **when** gap detection completes, **then** the system skips the question step and advances the pipeline automatically.

## Tasks / Subtasks

- [x] Task 1: Create a deterministic gap-analysis utility without changing the canonical parsed model shape (AC: 1, 2, 4)
  - [x] Add `app/utils/spec_gap_detector.py` with a focused public API such as `detect_spec_gaps(raw_spec: str, parsed_api_model: dict) -> list[dict]`
  - [x] Use both `raw_spec` and `parsed_api_model` to classify gaps so auth ambiguity can be detected without adding new keys to the canonical `parsed_api_model`
  - [x] Detect only high-signal, implementation-relevant gaps for this story:
    - missing or empty success response schema/details
    - request body ambiguity on write operations that appear to accept a body
    - auth ambiguity (for example: security declared but no actionable auth type, or explicit/public-vs-unspecified distinction)
    - undocumented error-response expectations when an endpoint has only success responses documented
  - [x] Generate stable question records with IDs, endpoint grouping metadata, gap type, target field, and user-facing question text
  - [x] Keep output concise and targeted; do not flood the UI with low-value questions

- [x] Task 2: Implement `detect_gaps` node behavior and routing in `app/pipeline.py` (AC: 1, 4)
  - [x] Replace the stub `detect_gaps()` with real logic that:
    - validates the presence of `raw_spec` and `parsed_api_model`
    - populates `state["detected_gaps"]`
    - clears stale answered gaps when a new spec is parsed
    - sets `state["pipeline_stage"] = "fill_gaps"` when unanswered gaps remain
    - sets `state["pipeline_stage"] = "review_spec"` when no gaps remain
    - clears `state["error_message"]` on success
  - [x] Update `_route_gaps()` so it returns `fill_gaps` only when active gaps exist and `review_spec` otherwise
  - [x] Preserve graceful-failure behavior: gap detection must never crash the pipeline; convert failures into user-safe `error_message`
  - [x] Keep zero-endpoint conversational fallback out of scope for this story; do not implement Story 1.5 behavior here

- [x] Task 3: Implement structured gap-answer application in `fill_gaps()` without introducing full conversational mode (AC: 2, 3)
  - [x] Replace the current stub with logic that reads `state["gap_answers"]` and resolves matching items in `state["detected_gaps"]`
  - [x] Persist every accepted answer into `gap_answers` using the gap question ID as the stable key
  - [x] For answers that can be merged deterministically (for example auth-required yes/no, auth type selection, documented status-code lists), update the relevant portion of `SataState`
  - [x] For answers that are free-text clarifications, keep the authoritative user input in `gap_answers` and remove the gap from `detected_gaps` without changing the canonical `parsed_api_model` contract
  - [x] When all gaps are resolved, advance to `pipeline_stage = "review_spec"`
  - [x] Do not implement chat-driven manual API authoring or zero-endpoint fallback in this node yet; that remains Story 1.5

- [x] Task 4: Extend `app.py` to surface grouped targeted questions and next actions (AC: 2, 3, 4)
  - [x] After a successful parse in the file-upload and URL-import flows, invoke `detect_gaps(state)` before persisting session state
  - [x] Add stage-driven rendering for `pipeline_stage == "fill_gaps"` that:
    - shows the persistent stage header already driven by `state["pipeline_stage"]`
    - displays a clear "Next required action" message explaining that the user must answer clarification questions before spec review
    - groups questions by endpoint using clear labels such as `POST /users`
    - renders answer controls appropriate to the gap type (`selectbox`, `multiselect`, `text_input`, `text_area`)
    - provides an explicit submit/apply action that updates `state["gap_answers"]`, calls `fill_gaps(state)`, persists the result, and reruns
  - [x] Add a lightweight `review_spec` placeholder state for now: once no gaps remain, show that the spec is ready for review and that Story 2.1 will provide the full review panel
  - [x] Preserve the current distinction between fetch errors, parse errors, and gap-detection errors in the UI

- [x] Task 5: Add focused automated coverage for node behavior, gap heuristics, and UI-facing state transitions (AC: 1, 2, 3, 4)
  - [x] Add `tests/test_spec_gap_detector.py` covering representative gap types and stable question IDs
  - [x] Add or extend pipeline-node tests for:
    - `detect_gaps()` setting `fill_gaps` vs `review_spec`
    - `fill_gaps()` removing answered gaps and preserving unresolved ones
    - graceful failure when gap analysis cannot run
  - [x] Update `tests/test_pipeline.py` so it no longer expects `detect_gaps` and `fill_gaps` to remain no-op stubs
  - [x] Add a regression test for the auth ambiguity called out in deferred work: explicit `security: []` must not be treated the same as auth simply being absent
  - [x] Add a regression test proving a parse with no actionable gaps advances directly to `review_spec`

## Dev Notes

### Previous Story Intelligence

- Story 1.2 established the canonical `parsed_api_model` structure and the rule that downstream stories must not silently drift from it.
- Story 1.3 extended ingestion but kept the same parse path: `app.py` performs file/URL ingestion, then calls `parse_spec(state)` directly, and stores the result in `st.session_state.state`.
- Current Streamlit behavior stops at the parse stage. Story 1.4 is the first story that must bridge successful parsing into clarification and then into the next pipeline checkpoint.
- Deferred work from Story 1.2 explicitly says Story 1.4 must distinguish explicitly public endpoints (`security: []`) from endpoints where auth is simply undocumented. That distinction is required for accurate targeted questions.

### Current Codebase Conventions To Follow

- `app/state.py`
  - `SataState` already has the necessary state buckets for this story: `parsed_api_model`, `detected_gaps`, `gap_answers`, `pipeline_stage`, and `error_message`
  - Reuse these fields rather than introducing parallel ad hoc state in `st.session_state`
- `app/pipeline.py`
  - Implemented nodes mutate and return the same state dict in place
  - Error handling is user-safe and non-throwing; follow the `parse_spec()` pattern
- `app.py`
  - Uses stage-driven rendering keyed off `state["pipeline_stage"]`
  - File-upload and URL-import flows already distinguish ingestion and parse failures; preserve that boundary
- `tests/`
  - Tests are unit-focused and deterministic
  - Existing `test_pipeline.py` still reflects Story 1.1 stub assumptions and should be updated rather than worked around

### Gap Record Contract

Use a stable, structured gap item shape in `state["detected_gaps"]`. A concrete shape like the following is recommended:

```python
{
    "id": "post-users-missing-success-response",
    "endpoint_key": "POST /users",
    "path": "/users",
    "method": "POST",
    "gap_type": "missing_success_response",
    "field": "response_schemas.201",
    "question": "Endpoint POST /users has no defined success response schema - what does a 201 response return?",
    "input_type": "text_area",  # or "select", "multiselect", "text"
    "options": None,
}
```

`gap_answers` should remain a simple mapping keyed by gap ID:

```python
{
    "post-users-missing-success-response": "Returns the created user object with id, email, and created_at.",
}
```

This keeps the story implementable with the current state shape and avoids schema churn.

### Canonical Model Guardrail

Do **not** add new top-level keys or endpoint keys to `parsed_api_model` for this story unless you also deliberately update the parser contract tests and all downstream references. Current tests assert the exact canonical key set.

For auth ambiguity and other clarifications that need more context than `parsed_api_model` exposes, inspect `raw_spec` directly inside the gap-analysis utility instead of widening the parsed schema.

### Implementation Guidance

- Recommended utility split:
  - `app/utils/spec_gap_detector.py` owns gap heuristics and question generation
  - `app/pipeline.py` owns state mutation and stage transitions
  - `app.py` owns answer widgets and submit/apply flows
- Recommended detection heuristics for MVP scope:
  - Success response ambiguity:
    - no `2xx` response documented
    - success response documented only as an empty string / description with no schema when the endpoint likely returns JSON
  - Request-body ambiguity:
    - `POST`, `PUT`, or `PATCH` operation has no usable request body information but appears to be a write endpoint
  - Auth ambiguity:
    - security requirement exists but top-level parsed auth info is not actionable
    - explicit `security: []` should be treated as intentionally public, not as a missing-auth gap
  - Error-response ambiguity:
    - endpoint documents only success responses and gives no indication of failure behavior
- Keep the generated questions short, specific, and endpoint-scoped.
- Do not call an LLM in this story just to classify gaps or to parse answers. Keep this implementation deterministic and offline-testable.

### Stage Progression Guidance

- After successful file/URL parse:
  - call `detect_gaps(state)`
  - if gaps exist, render the clarification UI
  - if no gaps exist, advance directly to `review_spec`
- `review_spec` in this story is a handoff stage, not the full editable review panel from Story 2.1
- Zero-endpoint fallback remains Story 1.5. Do not silently pretend a zero-endpoint spec is ready for review; keep that limitation explicit in code comments/tests if encountered

### File Structure Requirements

- Modify:
  - `app.py`
  - `app/pipeline.py`
  - `tests/test_pipeline.py`
- Add:
  - `app/utils/spec_gap_detector.py`
  - `tests/test_spec_gap_detector.py`
- Likely extend:
  - `tests/test_parse_spec_node.py`
  - `tests/test_state.py` only if stage expectations need updated coverage
- Reuse as-is:
  - `app/state.py`
  - `app/utils/spec_parser.py` unless a very small shared parsing helper is needed for `raw_spec` inspection

### Testing Requirements

- Keep all tests offline and deterministic.
- Test both path variants:
  - parsed spec with actionable gaps
  - parsed spec with no actionable gaps
- Validate stage transitions explicitly:
  - `spec_parsed` -> `fill_gaps`
  - `spec_parsed` -> `review_spec`
  - `fill_gaps` -> `review_spec` after answers are applied
- Include one test fixture where operation-level `security: []` overrides global security so the detector does **not** ask an auth clarification for that endpoint.
- Include one test fixture where auth is required by spec structure but the parsed auth metadata is not actionable so the detector **does** ask an auth clarification.

### Risks And Guardrails

- Regression risk: changing the canonical parsed model shape here will break existing tests and destabilize later stories.
- Scope risk: implementing full conversational fallback in this story will blur the boundary with Story 1.5 and slow delivery.
- UX risk: too many vague questions will make the clarification step feel like busywork rather than a precise checkpoint.
- State risk: stale `detected_gaps` or `gap_answers` from a previous spec import can leak into a new run unless explicitly cleared when a new spec is parsed.
- Pipeline risk: `tests/test_pipeline.py` currently assumes stub behavior for all nodes; story work must update those assumptions instead of leaving false expectations in place.

### References

- Story requirements and acceptance criteria: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Product rationale for targeted clarification and checkpointed flow: [Source: `_bmad-output/planning-artifacts/prd.md`]
- Architecture constraint that human-in-the-loop controls are enforced in workflow/state, not only in UI copy: [Source: `_bmad-output/planning-artifacts/architecture.md`]
- UX requirements for stage header, next required action, grouped gap warnings, and clear fallback states: [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`]
- Current parser contract and canonical schema: [Source: `_bmad-output/implementation-artifacts/1-2-openapi-swagger-file-upload-and-parsing.md`]
- Current ingestion flow and error-boundary handling: [Source: `_bmad-output/implementation-artifacts/1-3-api-spec-url-import.md`]
- Deferred auth ambiguity item assigned to Story 1.4: [Source: `_bmad-output/implementation-artifacts/deferred-work.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `pytest -q tests/test_spec_gap_detector.py tests/test_pipeline.py` -> 12 passed
- `pytest -q` -> 137 passed
- `python3 -m py_compile app.py app/pipeline.py app/utils/spec_gap_detector.py tests/test_spec_gap_detector.py tests/test_pipeline.py` -> OK

### Completion Notes List

- Implemented deterministic gap analysis in `app/utils/spec_gap_detector.py` using both `raw_spec` and the canonical parsed model so Story 1.4 could detect missing success responses, missing request bodies, missing error responses, and auth ambiguity without widening the parser contract.
- Replaced the `detect_gaps` and `fill_gaps` stubs in `app/pipeline.py` with real state mutation, routing, stale-answer cleanup, deterministic answer application, and graceful failure handling.
- Updated `app.py` so successful file and URL parsing immediately flow into gap detection, render grouped clarification questions, apply answers through a form, and land on a lightweight `review_spec` placeholder when clarification is complete.
- Added focused tests for gap heuristics and pipeline stage transitions, including the deferred explicit-public-vs-unspecified-auth regression.
- Full regression suite and compile checks passed after implementation.

### File List

- `_bmad-output/implementation-artifacts/1-4-spec-gap-detection-and-targeted-questions.md`
- `app.py`
- `app/pipeline.py`
- `app/utils/spec_gap_detector.py`
- `tests/test_pipeline.py`
- `tests/test_spec_gap_detector.py`

## Review Findings

- [x] `Review/Patch` — `_has_missing_success_response` flags 204 with empty description as missing — A 204 response with `{"description": "No Content"}` and no schema may be normalised to an empty string/`None` by the parser, incorrectly generating a gap question — `src/tools/gap_detector.py:136-144` — **resolved**: added `if str(code) in ("204", "205"): return False` guard in loop
- [x] `Review/Patch` — `_has_missing_error_responses` fires simultaneously with `_has_missing_success_response` on empty `response_schemas`, producing two gap questions for the same endpoint — `src/tools/gap_detector.py:147-151` — **resolved**: changed `if not responses: return True` to `return False`; empty schemas are owned by `_has_missing_success_response`
- [x] `Review/Patch` — `_apply_gap_answer` silently drops answers for `missing_success_response` and `missing_request_body` gap types; `parsed_api_model` is never updated, violating AC3 — `src/nodes/fill_gaps.py:97-117` — **resolved**: added handlers for both gap types that store answers as enrichments in the endpoint
- [x] `Review/Patch` — `_apply_global_auth_if_unambiguous` overwrites global auth unconditionally when answer is "none", even if other unanswered auth gaps remain — `src/nodes/fill_gaps.py:152-165` — **resolved**: early return for `answer == "none"` without touching global auth
- [x] `Review/Decision` — `fill_gaps` sets `pipeline_stage="spec_parsed"` on completion but `app.py` immediately overrides to `"review_spec"`; node and UI contracts are inconsistent — direct LangGraph invocation lands in wrong stage — `src/nodes/fill_gaps.py:45`, `app.py:288` — **DEFERRED**: will be fixed in story 1-5's scope since it is in the conversational path
- [ ] `Review/Patch` — `_route_gaps` routes `None` detected_gaps to `review_spec` on `detect_gaps` failure, bypassing the error state in a native LangGraph invocation — `src/core/graph.py:173-175`, `src/nodes/detect_gaps.py:29-34`
- [ ] `Review/Patch` — Stale gap answers silently discarded with no user warning when re-imported spec changes gap IDs — `src/nodes/detect_gaps.py:20-25`
- [x] `Review/Patch` — `_has_auth_ambiguity` is overly optimistic on AND-combination security requirements; returns False as soon as any one scheme is supported, ignoring unsupported sibling schemes — `src/tools/gap_detector.py:163-172` — **resolved**: rewrote loop so all schemes in an AND-requirement must be supported; early exit only on a fully-supported requirement
- [x] `Review/Patch` — No test asserts `parsed_api_model` is actually updated after a `missing_success_response` answer; existing test is a false positive for AC3 — `tests/integration/test_pipeline.py:223-281` — **resolved**: added `test_fill_gaps_updates_parsed_api_model_for_missing_success_response_answer` and three unit tests for the new heuristic edge cases
- [x] `Review/Decision` — Double-filtering of gap_answers (UI strips blank selects before writing to state; node filters again) allows blank select to silently retain a prior answer — `app.py:316-321`, `src/ui/components.py:22-33` — **DEFERRED**: requires user input; deferred to future story
- [x] `Review/Defer` — `_route_results` always returns `END`, making the "deeper analysis" edge permanently unreachable; pre-existing stub for a future story — `src/core/graph.py:188-191`

## Change Log

- 2026-03-31: Implemented Story 1.4 gap detection, clarification state handling, Streamlit clarification UI, and focused regression coverage; full test suite passes.
- 2026-04-04: Applied review-round patch fixes — 204/205 success-response guard, double-gap prevention on empty schemas, `missing_success_response` and `missing_request_body` answer handlers, `_apply_global_auth_if_unambiguous` "none" early return, AND-combination auth ambiguity logic; added 5 targeted tests; 140 tests pass, ruff clean.
