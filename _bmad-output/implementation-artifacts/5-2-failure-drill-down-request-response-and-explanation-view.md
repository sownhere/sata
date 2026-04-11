# Story 5.2: Failure Drill-Down - Request, Response, and Explanation View

Status: review

## Story

As a developer,
I want to click into any failing test case and see the full request that was sent, the response that came back, and the plain-language explanation of what went wrong,
so that I have everything I need to reproduce and fix the issue without leaving the tool.

## Acceptance Criteria

1. **Given** the results dashboard is displayed with one or more failures **when** the developer selects a failing test **then** a detail view opens with request metadata, response payload/metadata, and the explanation from Story 4.3.

2. **Given** the detail view is open **when** request headers are shown **then** auth tokens/API keys are redacted and never rendered in full.

3. **Given** the user navigates back from detail view **when** they return to dashboard **then** dashboard context is preserved (filters, selected grouping, and scroll context where feasible).

4. **Given** the selected test case passed **when** detail view opens **then** the view shows request/response details and a deterministic "Test passed" message instead of failure explanation.

## Tasks / Subtasks

- [x] Task 1: Add deterministic detail-view formatter helpers (AC: 1, 2, 4)
  - [x] Implement/extend UI helpers in `src/ui/` for detail-view payload shaping:
    - Safe request section (method, URL, headers redacted, body)
    - Response section (status, headers, body)
    - Analysis section (failure explanation or pass message)
  - [x] Centralize redaction logic in one helper to avoid inconsistent masking.

- [x] Task 2: Add dashboard-to-detail selection state contract (AC: 1, 3, 4)
  - [x] Track selected `test_id` in `SataState` (or Streamlit session key with documented contract).
  - [x] Add deterministic open/close behavior for the detail pane/modal/expander.
  - [x] Preserve dashboard filters/selections when returning.

- [x] Task 3: Integrate detail renderer in `review_results` UI flow (AC: 1-4)
  - [x] Connect selection actions from story 5.1 list/heatmap rows.
  - [x] Render explanation from `failure_analysis["explanations"]` keyed by `test_id`.
  - [x] Fall back cleanly when explanation is unavailable (for passed tests or parse errors).

- [x] Task 4: Add strict security redaction tests (AC: 2)
  - [x] Unit tests for header redaction helper including:
    - `Authorization`, `X-API-Key`, common token aliases
    - Case-insensitive key matching
  - [x] Integration assertion that no unredacted secrets are displayed in drill-down.

## Dev Notes

### Previous Story Intelligence (from 5.1)

- Story 5.1 establishes the top-level dashboard and primary result-grouping views.
- Story 5.2 should reuse those groupings and IDs, not re-query or reshape independently.
- Keep interaction lightweight and deterministic to avoid UI regressions during reruns.

### Existing Data Contracts

- `state["test_results"]` contains request/response execution fields from Story 4.1 and validation fields from Story 4.2.
- `state["failure_analysis"]["explanations"]` contains `what_broke/why_it_matters/how_to_fix` keyed by `test_id` from Story 4.3.
- `state["failure_analysis"]["parse_error"]` may exist; in that case, drill-down should still show request/response and a graceful fallback message.

### Architecture Guardrails

- Keep formatting logic in `src/ui/*`, and keep state mutation explicit/minimal in `app.py`.
- No LLM calls in drill-down rendering path.
- Never render full secrets from headers or auth config.

### File Structure Requirements

**Likely modify:**
- `app.py`
- `src/ui/components.py`
- `src/ui/results_dashboard.py` (if created in 5.1)
- `src/core/state.py` (if selected-test state key is added)
- `tests/unit/test_state.py`
- `tests/unit/test_spec_review.py` or new UI helper tests

### Testing Requirements

- Verify failure detail view links correct explanation by `test_id`.
- Verify pass detail view uses pass message and no failure explanation.
- Verify header redaction is always applied and case-insensitive.
- Verify returning from detail preserves dashboard selection/filter context.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.2)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR28, FR27, NFR8)
- Dependency context: `_bmad-output/implementation-artifacts/5-1-results-dashboard-pass-fail-metrics-and-defect-heatmap.md`
- Existing execution/analysis fields: `src/core/state.py`, `src/nodes/execute_tests.py`, `src/nodes/analyze_results.py`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added shared redaction helpers in `src/tools/redaction.py` and reused them across execution results, drill-down shaping, and future reporting/observability work.
- Extended HTTP execution results with safe request/response metadata so drill-down can show method, URL, headers, query params, body, and response details without leaking secrets.
- Added `selected_test_id` and `results_filters` state so detail view open/close keeps dashboard context stable across reruns.
- `review_results` now opens detail panels from both heatmap rows and filtered result rows, and falls back cleanly for passed tests or missing explanations.

### File List

- `src/tools/redaction.py`
- `src/tools/http_executor.py`
- `src/ui/results_dashboard.py`
- `src/core/state.py`
- `app.py`
- `tests/unit/test_redaction.py`
- `tests/unit/test_http_executor.py`
- `tests/unit/test_results_dashboard.py`
- `tests/unit/test_state.py`
- `_bmad-output/implementation-artifacts/5-2-failure-drill-down-request-response-and-explanation-view.md`

### Change Log

- 2026-04-11: Implemented failure drill-down, request/response shaping, and strict redaction; story moved to `review`.
