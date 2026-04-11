# Story 5.4: Deeper Analysis, Re-test Loop, and Iteration

Status: review

## Story

As a developer,
I want to request deeper analysis on specific failing areas or trigger a full re-test after I make fixes,
so that I can iterate quickly without restarting the entire pipeline from scratch.

## Acceptance Criteria

1. **Given** the results dashboard is visible **when** the developer selects endpoints/categories for deeper analysis **then** the system re-runs test generation/execution scoped to that subset and merges the new scoped results into state.

2. **Given** the developer requests a full re-test after making fixes **when** the re-test loop starts **then** the pipeline re-runs the full confirmed test plan without re-ingestion/re-confirmation of spec.

3. **Given** re-test starts **when** execution begins **then** running progress UI is shown and stage text clearly indicates a re-run attempt (for example, "Re-running - Attempt 2").

4. **Given** re-test completes **when** results are rendered **then** improvement/regression indicators vs previous run are shown.

## Tasks / Subtasks

- [x] Task 1: Define iteration state model and comparison baseline (AC: 1-4)
  - [x] Add state fields for run history metadata (attempt number, previous summary, optional scoped selection).
  - [x] Keep storage minimal and serializable for Streamlit session state.

- [x] Task 2: Add scoped deeper-analysis execution flow (AC: 1)
  - [x] Add UI controls to choose endpoints/categories for deeper analysis.
  - [x] Build scoped test case set from existing confirmed plan.
  - [x] Reuse `execute_tests` and `analyze_results` logic; avoid duplicate execution code paths.

- [x] Task 3: Add full re-test loop entry point from results stage (AC: 2, 3)
  - [x] Add explicit "Re-test full plan" action in `review_results`.
  - [x] Reset only execution/analysis outputs while preserving confirmed spec/test plan.
  - [x] Increment attempt counter and update stage messaging.

- [x] Task 4: Implement run-to-run comparison indicators (AC: 4)
  - [x] Compare pass/fail totals and optionally key category deltas between last and current run.
  - [x] Render concise delta indicators with up/down semantics.

- [x] Task 5: Add route and regression tests for loop behavior (AC: 1-4)
  - [x] Integration tests for scoped run and full re-test run.
  - [x] Guard tests proving spec/test-plan checkpoints are not forced again for re-test.
  - [x] Tests for attempt numbering and comparison output.

## Dev Notes

### Previous Story Intelligence (from 5.1-5.3)

- Dashboard/drill-down/report outputs already exist as read-models over `test_results` and `failure_analysis`.
- Story 5.4 should orchestrate re-execution and then reuse those same renderers.
- Preserve deterministic rerun behavior to avoid stale-state confusion.

### Routing and Pipeline Considerations

- Current `review_results` node is still a stub; iteration orchestration is currently UI-driven in `app.py`.
- Keep any new loop transitions explicit and visible to users (UX no-hidden-transitions principle).
- Ensure max-iteration and timeout safeguards from execution flow remain active.

### Architecture Guardrails

- Keep state as single source of truth for current and previous run summaries.
- No secret leakage across run-history snapshots.
- Prefer helper utilities in `src/ui` / `src/tools` over embedding logic in one large `app.py` branch.

### File Structure Requirements

**Likely modify/add:**
- `app.py`
- `src/core/state.py`
- `src/ui/components.py`
- `src/ui/results_dashboard.py` (if created)
- `src/nodes/review_results.py` (only if route contract is formalized now)
- `tests/integration/test_pipeline.py`
- `tests/unit/test_state.py`

### Testing Requirements

- Verify scoped deeper-analysis only executes selected subset.
- Verify full re-test reuses confirmed test plan and bypasses ingestion/review checkpoints.
- Verify attempt counter and stage labels update correctly.
- Verify comparison delta (improved/regressed/unchanged) matches run outcomes.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.4)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR29, FR30, UX-DR6, UX-DR7)
- Dependency context: `_bmad-output/implementation-artifacts/5-1-results-dashboard-pass-fail-metrics-and-defect-heatmap.md`, `_bmad-output/implementation-artifacts/5-2-failure-drill-down-request-response-and-explanation-view.md`, `_bmad-output/implementation-artifacts/5-3-results-report-generation.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added `run_attempt`, `previous_run_summary`, `run_history`, and `scoped_run_selection` to state so results iteration stays serializable and explicit.
- Added scoped deeper-analysis selectors for endpoints/categories and a full-plan re-test action in `review_results`.
- Reused existing `execute_tests` and `analyze_results` nodes for reruns, including merged scoped results and preserved confirmed checkpoints.
- Added run-to-run deltas to the dashboard so improvements/regressions show up immediately after each rerun.

### File List

- `src/core/state.py`
- `src/ui/results_dashboard.py`
- `app.py`
- `tests/unit/test_state.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/5-4-deeper-analysis-re-test-loop-and-iteration.md`

### Change Log

- 2026-04-11: Implemented scoped/full results iteration loops and moved the story to `review`.
