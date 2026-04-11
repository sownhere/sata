# Story 6.3: Demo Mode - Sample APIs and Guided End-to-End Flow

Status: review

## Story

As a developer or evaluator,
I want to select a pre-loaded sample API and run a fully guided end-to-end demo flow,
so that I can see the complete tool in action without needing my own API or spec file.

## Acceptance Criteria

1. **Given** the app is on spec-ingestion stage **when** the user selects Demo Mode **then** PetStore, ReqRes, and JSONPlaceholder are available and selecting one pre-populates state with bundled spec metadata/content.

2. **Given** demo mode starts **when** the guided flow runs **then** the pipeline proceeds through all stages with pre-configured defaults while still honoring human checkpoints (confirm/reject is never bypassed).

3. **Given** demo execution reaches HTTP testing **when** requests are sent **then** real requests hit the public sample API endpoints and return real responses.

4. **Given** demo completes **when** results are shown **then** the results experience matches normal runs (dashboard, drill-down, analysis, and report paths remain available).

## Tasks / Subtasks

- [x] Task 1: Define demo catalog and fixtures (AC: 1, 3)
  - [x] Add a deterministic sample catalog module (recommended: `src/tools/demo_catalog.py`) with entries for:
    - PetStore
    - ReqRes
    - JSONPlaceholder
  - [x] Include source URL/spec payload references and safe defaults for auth/headers (none by default).

- [x] Task 2: Add Demo Mode entrypoint in ingestion UI (AC: 1)
  - [x] Add explicit Demo Mode selector in `app.py` ingestion controls.
  - [x] Populate `SataState` with selected sample input and tag run context as demo.

- [x] Task 3: Implement guided flow orchestration with checkpoints preserved (AC: 2)
  - [x] Auto-fill optional user inputs where applicable, but keep required human approvals manual.
  - [x] Ensure rejection paths still behave normally in demo runs.

- [x] Task 4: Ensure execution uses real endpoints and robust error handling (AC: 3)
  - [x] Route demo requests through existing `execute_tests` path.
  - [x] Show clear guidance when public sample endpoint is temporarily unavailable.

- [x] Task 5: Reuse existing review/results UI for parity (AC: 4)
  - [x] Confirm demo results render through same `review_results` branch as standard runs.
  - [x] Add subtle demo badges/labels without creating a separate parallel UI.

- [x] Task 6: Add tests for demo selection and flow integrity (AC: 1-4)
  - [x] Unit tests for demo catalog shape and selection mapping.
  - [x] Integration tests for checkpoint preservation and state transitions in demo mode.
  - [x] Tests proving demo mode does not bypass destructive-operation acknowledgment when applicable.

## Dev Notes

### Previous Story Intelligence (from 6.1 / 6.2)

- Use observability from Story 6.2 and reasoning-log facilities from Story 6.1 to make demo behavior explainable.
- Demo mode should be additive; it must not fork or duplicate core pipeline logic.

### Architecture and Security Guardrails

- Reuse existing parsing, generation, execution, and analysis paths.
- Do not hardcode credentials for demo APIs.
- Keep sample configuration non-secret and version-controlled.
- Keep UI responsive and checkpoint-driven as defined in UX principles.

### File Structure Requirements

**Likely modify/add:**
- `app.py`
- `src/tools/demo_catalog.py` (new)
- `src/core/state.py` (optional demo metadata fields)
- `src/ui/components.py` (demo selector and labeling helpers)
- `tests/unit/test_state.py`
- `tests/integration/test_pipeline.py`

### Testing Requirements

- Verify selecting each sample populates correct source and metadata.
- Verify all checkpoint gates remain active in demo mode.
- Verify demo-mode run reaches execution and analysis using real endpoints.
- Verify demo-mode results are rendered through the standard results flow.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.3)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR39, FR40, FR27, UX-DR1/2/3/7)
- Related implementation context: `_bmad-output/implementation-artifacts/6-2-langgraph-pipeline-visualization.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added `src/tools/demo_catalog.py` with bundled PetStore, ReqRes, and JSONPlaceholder fixtures plus source URLs, base URLs, and safe defaults.
- Added a Demo Mode selector to ingestion and store demo metadata/base URL in state without forking the core pipeline.
- Demo runs reuse normal parse/generate/execute/analyze/results flow and keep human checkpoints intact.
- Added lightweight demo labels in the app plus demo catalog and checkpoint-preservation tests.

### File List

- `src/tools/demo_catalog.py`
- `src/core/state.py`
- `app.py`
- `tests/unit/test_demo_catalog.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/6-3-demo-mode-sample-apis-and-guided-end-to-end-flow.md`

### Change Log

- 2026-04-11: Implemented Demo Mode with bundled sample APIs and moved the story to `review`.
