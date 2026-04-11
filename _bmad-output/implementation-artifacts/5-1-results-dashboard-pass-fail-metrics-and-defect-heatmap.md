# Story 5.1: Results Dashboard - Pass/Fail Metrics and Defect Heatmap

Status: review

## Story

As a developer,
I want a high-level results dashboard showing pass/fail metrics, a defect heatmap, and category summaries,
so that I can triage the overall health of my API at a glance without reading every test result individually.

## Acceptance Criteria

1. **Given** test execution and analysis are complete **when** the results dashboard is displayed **then** the stage header reflects results review and shows total tests, pass count, fail count, and pass-rate percentage.

2. **Given** the dashboard is rendered **when** the developer views defect summaries **then** failures are grouped by defect category with counts and endpoint-level concentration is visible via heatmap-style indicators.

3. **Given** the dashboard is rendered **when** the developer views priority distribution **then** P1, P2, and P3 failures are shown separately so critical failures are immediately visible.

4. **Given** all tests passed **when** the dashboard renders **then** a clear success state is shown along with deeper-testing suggestions from Story 4.4.

## Tasks / Subtasks

- [x] Task 1: Define dashboard view-model contract in UI layer (AC: 1-4)
  - [x] Add deterministic formatter helpers (recommended new module: `src/ui/results_dashboard.py`) for:
    - Run summary metrics
    - Defect-category buckets
    - Priority buckets
    - Endpoint-failure heatmap rows
  - [x] Keep formatters pure and testable (no Streamlit imports in pure transforms).

- [x] Task 2: Add dashboard rendering inside `review_results` stage (AC: 1-4)
  - [x] Refactor `app.py` `review_results` branch to render:
    - Metrics row (`st.metric`)
    - Category summary section
    - Priority breakdown section
    - Endpoint heatmap table/chart equivalent
  - [x] Keep existing explanation panels from Story 4.3 accessible.

- [x] Task 3: Implement heatmap mapping without new heavy dependencies (AC: 2)
  - [x] Use a deterministic visual representation from existing Streamlit primitives.
  - [x] Ensure endpoint label format is stable (`METHOD path`) for drill-down linkage in Story 5.2.

- [x] Task 4: Handle state edge-cases safely (AC: 1, 4)
  - [x] If `test_results` is missing, render actionable empty-state guidance instead of crashing.
  - [x] If no failures, render success-state card and reuse Story 4.4 deeper-testing suggestions.

- [x] Task 5: Add coverage for dashboard computations and rendering guards (AC: 1-4)
  - [x] Unit tests for metric and aggregation helpers.
  - [x] Integration test(s) asserting `review_results` stage can render with mixed/all-pass data.

## Dev Notes

### Epic Dependencies and Handoff

- Story 4.3 already provides grouped `patterns` and per-test `explanations`.
- Story 4.4 introduces all-pass/all-fail smart outputs; this dashboard must surface those outputs, not re-compute them.
- Story 5.2 drill-down will consume the selected endpoint/test context created by this dashboard.

### Architecture and UX Guardrails

- Keep stage-driven flow consistent with UX principles (persistent stage + next action messaging).
- UI composition should live under `src/ui/*`; avoid expanding business logic inside `app.py`.
- Never show secret-bearing headers or raw token/key values in any summary card or table.

### File Structure Requirements

**Likely modify:**
- `app.py`
- `src/ui/components.py` and/or new `src/ui/results_dashboard.py`
- `tests/unit/test_spec_review.py` (or add a dedicated dashboard UI-unit test module)
- `tests/unit/test_state.py` (if new state key is needed for selected rows/filters)

**Likely avoid changing:**
- `src/nodes/review_results.py` control-flow behavior unless strictly required.

### Testing Requirements

- Verify pass-rate math and divide-by-zero handling.
- Verify category/priority grouping for mixed pass/fail data.
- Verify all-pass branch surfaces deeper-test suggestions.
- Verify no secret values are rendered in dashboard summaries.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.1)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR27, FR38, UX-DR5)
- UX guidance: `_bmad-output/planning-artifacts/ux-design-specification.md`
- Existing analysis outputs: `_bmad-output/implementation-artifacts/4-3-failure-analysis-and-developer-friendly-explanations.md`, `_bmad-output/implementation-artifacts/4-4-smart-diagnosis-all-pass-suggestions-and-all-fail-detection.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added pure dashboard helpers in `src/ui/results_dashboard.py` for run summary, category buckets, priority buckets, result-row joins, and endpoint heatmaps.
- Reworked `review_results` to show metrics, category summaries, P1/P2/P3 breakdown, stable `METHOD path` heatmap rows, and preserved explanation panels.
- Added safe empty-state handling and all-pass success rendering that reuses Story 4.4 deeper-test suggestions.
- Added dashboard helper coverage in `tests/unit/test_results_dashboard.py`.

### File List

- `src/ui/results_dashboard.py`
- `app.py`
- `src/core/state.py`
- `tests/unit/test_results_dashboard.py`
- `tests/unit/test_state.py`
- `_bmad-output/implementation-artifacts/5-1-results-dashboard-pass-fail-metrics-and-defect-heatmap.md`

### Change Log

- 2026-04-11: Implemented the results dashboard and moved the story to `review`.
