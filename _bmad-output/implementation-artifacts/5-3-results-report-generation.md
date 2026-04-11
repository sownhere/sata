# Story 5.3: Results Report Generation

Status: review

## Story

As a developer,
I want to generate a structured results report from the completed test run,
so that I can share findings with my team or keep a record of API quality at a point in time.

## Acceptance Criteria

1. **Given** execution and analysis are complete **when** the user requests report generation **then** a report is produced with run metadata, summary counts, category breakdown, failures with explanations, and smart outcomes (all-pass suggestions or all-fail diagnosis).

2. **Given** a generated report is viewed/downloaded **when** content is rendered **then** output is readable Markdown or plain text and includes no secrets/tokens/keys.

3. **Given** report generation is triggered again for the same run **when** output is saved **then** prior output is deterministically replaced or timestamped to avoid ambiguity.

## Tasks / Subtasks

- [x] Task 1: Define report schema and deterministic renderer (AC: 1, 2)
  - [x] Add a dedicated formatter module in `src/ui/` or `src/tools/` (recommended: `src/tools/report_builder.py`) that consumes `SataState` and returns report text.
  - [x] Include sections in fixed order: run metadata, summary metrics, category breakdown, failed test details, diagnosis/suggestions.
  - [x] Ensure formatting is stable for test snapshots.

- [x] Task 2: Add user action and output handling in UI (AC: 1-3)
  - [x] Add "Generate Report" action in `review_results` stage.
  - [x] Render preview in UI and provide download action.
  - [x] Persist generated report path/content reference in state if needed for re-open.

- [x] Task 3: Implement redaction and safe serialization layer (AC: 2)
  - [x] Reuse shared header/token redaction helper from Story 5.2.
  - [x] Exclude sensitive fields from request/response bodies when configured as secret-like.
  - [x] Ensure report never includes raw auth config values.

- [x] Task 4: Define overwrite/timestamp behavior (AC: 3)
  - [x] Preferred default: timestamped report files in a predictable folder.
  - [x] Alternative: explicit overwrite mode with clear UI label.
  - [x] Keep decision documented in story completion notes.

- [x] Task 5: Add tests for content and safety (AC: 1-3)
  - [x] Unit tests for report section assembly and deterministic ordering.
  - [x] Security tests for secret redaction.
  - [x] Integration test for repeated generation behavior.

## Dev Notes

### Previous Story Intelligence (from 5.1 / 5.2)

- Reuse dashboard/drill-down aggregation outputs where possible; avoid duplicate computation.
- Keep report generation decoupled from Streamlit widgets so it can be reused for future CI/headless mode.

### Architectural Guardrails

- Put transformation/business logic in tools/helpers, not directly in `app.py`.
- Keep report generation side effects explicit (file write path, naming strategy, overwrite policy).
- Maintain node/tool/ui dependency boundaries from architecture constraints.

### File Structure Requirements

**Likely modify/add:**
- `app.py`
- `src/tools/report_builder.py` (new)
- `src/ui/components.py` (download/render helpers)
- `src/core/state.py` (optional report metadata fields)
- `tests/unit/test_report_builder.py` (new)
- `tests/integration/test_pipeline.py` or results-flow integration tests

### Testing Requirements

- Verify report includes mandatory sections and expected totals.
- Verify report includes failure explanations and smart outcomes.
- Verify secret redaction in all report variants.
- Verify repeated report generation follows chosen overwrite/timestamp rule.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 5, Story 5.3)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR38, FR27, FR28, NFR8)
- Dependency context: `_bmad-output/implementation-artifacts/5-1-results-dashboard-pass-fail-metrics-and-defect-heatmap.md`, `_bmad-output/implementation-artifacts/5-2-failure-drill-down-request-response-and-explanation-view.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added `src/tools/report_builder.py` to render stable Markdown reports with run metadata, summary counts, category breakdown, failure details, and smart outcomes.
- `review_results` now exposes a `Generate Report` action, inline preview, and download flow, while persisting report metadata in state for re-open.
- Chose timestamped report files under `reports/` as the default persistence strategy so repeated generation is unambiguous.
- Report generation reuses the shared redaction layer and keeps secrets out of rendered content.

### File List

- `src/tools/report_builder.py`
- `src/core/state.py`
- `app.py`
- `tests/unit/test_report_builder.py`
- `_bmad-output/implementation-artifacts/5-3-results-report-generation.md`

### Change Log

- 2026-04-11: Implemented results report generation with timestamped persistence and moved the story to `review`.
