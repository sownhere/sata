# Story 4.4: Smart Diagnosis - All-Pass Suggestions and All-Fail Detection

Status: review

## Story

As a developer,
I want the system to detect when all tests pass (suggesting deeper coverage) or when all tests fail (diagnosing a systemic issue),
so that I always receive actionable next steps rather than a bare result count.

## Acceptance Criteria

1. **Given** execution completes and all enabled test cases pass **when** the `analyze_results` node processes the results **then** the system generates deeper-testing suggestions and stores them in `state["failure_analysis"]` for prominent display in `review_results`.

2. **Given** execution completes and all enabled test cases fail **when** the `analyze_results` node processes the results **then** the system runs smart diagnosis and returns the most probable systemic cause from: auth misconfiguration, wrong base URL, API down/unreachable, or required setup step missing.

3. **Given** smart diagnosis identifies auth misconfiguration as likely **when** diagnosis is displayed **then** the message references the auth scheme from `parsed_api_model["auth"]` and gives concrete token/key verification steps without exposing secrets.

4. **Given** smart diagnosis identifies target API unreachable **when** diagnosis is displayed **then** the message is distinct from per-test failure text and explicitly suggests checking `TARGET_API_URL` / base URL configuration.

5. **Given** neither all-pass nor all-fail conditions are true **when** analysis runs **then** existing pattern analysis from Story 4.3 remains unchanged and no false systemic diagnosis is added.

## Tasks / Subtasks

- [x] Task 1: Extend failure-analysis contract for smart diagnosis outcomes (AC: 1-5)
  - [x] Update the `failure_analysis` dict contract (docs + code paths) to support:
    - `all_passed: bool`
    - `all_failed: bool`
    - `next_test_suggestions: list[str]`
    - `smart_diagnosis: {"category": str, "message": str, "confidence": str}`
  - [x] Keep backward compatibility with Story 4.3 shape (`patterns`, `explanations`).

- [x] Task 2: Add deterministic diagnosis helper in tools layer (AC: 2-4)
  - [x] Create/extend a deterministic tool in `src/tools/` (recommended: `failure_analyzer.py`) to classify all-fail scenarios using only safe fields from `test_results` + `parsed_api_model`.
  - [x] Add explicit heuristics in priority order (auth, base URL, unreachable API, missing setup dependency) and return one best diagnosis.
  - [x] Ensure no token, API key, or sensitive header/body value is included in generated messages.

- [x] Task 3: Wire node behavior in `src/nodes/analyze_results.py` (AC: 1-5)
  - [x] Detect `all_passed` and attach deeper-test suggestions.
  - [x] Detect `all_failed` and attach `smart_diagnosis`.
  - [x] Preserve current mixed-result behavior and stage transition (`pipeline_stage = "review_results"`).

- [x] Task 4: Render smart outcomes in results UI (AC: 1-4)
  - [x] Update the `review_results` block in `app.py` to render:
    - Success-state deeper-test suggestions (all-pass)
    - Dedicated warning/error diagnosis panel (all-fail)
  - [x] Keep existing grouped patterns/explanations UI for mixed results.

- [x] Task 5: Add tests covering decision branches and safety (AC: 1-5)
  - [x] Unit tests for diagnosis classifier (all-pass, all-fail by cause, mixed).
  - [x] Integration tests for `analyze_results` node branch behavior.
  - [x] UI-level test coverage where available for message selection and redaction guarantees.

## Dev Notes

### Previous Story Intelligence (from 4.3)

- `src/nodes/analyze_results.py` already sets `failure_analysis` and advances to `review_results`.
- `src/tools/failure_analyzer.py` already enforces safe-field-only LLM payloads; preserve this security boundary.
- `app.py` already has `review_results` rendering branches and a "New Test Run" action; extend instead of replacing.

### Architecture Compliance Guardrails

- Keep dependency direction: `nodes -> tools -> core`, no `tools -> ui` imports.
- Keep all diagnosis logic deterministic where possible; only use LLM when heuristic signal is insufficient.
- Maintain `SataState` as the single source of truth for diagnosis/suggestion outputs.
- Do not reintroduce secrets into logs, prompts, state fields, or UI text.

### File Structure Requirements

**Likely modify:**
- `src/tools/failure_analyzer.py`
- `src/nodes/analyze_results.py`
- `app.py`
- `src/core/state.py` (if type docs/shape clarification needed)
- `tests/unit/test_failure_analyzer.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_state.py`

**Do not modify for this story:**
- `src/nodes/review_results.py` routing semantics beyond what is needed for display logic in `app.py`

### Testing Requirements

- Validate all-pass branch returns suggestions and no `smart_diagnosis`.
- Validate all-fail branch picks exactly one diagnosis category.
- Validate auth diagnosis references scheme/location, never raw credentials.
- Validate unreachable diagnosis is distinct from per-test error text.
- Run full suite to guard against regressions in Story 4.1-4.3 behavior.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.4)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR25, FR26, NFR3, NFR8)
- Existing implementation context: `_bmad-output/implementation-artifacts/4-3-failure-analysis-and-developer-friendly-explanations.md`
- Current state contract: `src/core/state.py`
- Current node/UI hooks: `src/nodes/analyze_results.py`, `app.py`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added `all_failed`, `next_test_suggestions`, and `smart_diagnosis` to the `failure_analysis` contract without breaking Story 4.3 keys.
- Implemented deterministic all-fail heuristics in `src/tools/failure_analyzer.py` for auth misconfiguration, wrong base URL, unreachable API, and missing setup.
- `analyze_results` now branches cleanly for all-pass, all-fail, and mixed runs while keeping `pipeline_stage = "review_results"`.
- `review_results` renders deeper-test suggestions and a dedicated smart-diagnosis panel.
- Added regression coverage for the new branches and preserved current suite health (`258 passed`).

### File List

- `src/tools/failure_analyzer.py`
- `src/nodes/analyze_results.py`
- `src/core/state.py`
- `app.py`
- `tests/unit/test_failure_analyzer.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_state.py`
- `_bmad-output/implementation-artifacts/4-4-smart-diagnosis-all-pass-suggestions-and-all-fail-detection.md`

### Change Log

- 2026-04-11: Implemented smart all-pass/all-fail analysis and moved the story to `review`.
