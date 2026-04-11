# Story 3.2: Test Plan Review - Category Toggles & Destructive Warnings

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to see all generated test cases grouped by category with priority labels, toggle categories on or off, and see destructive-operation warnings surfaced directly next to relevant tests,
so that I can configure exactly what runs without scrolling through a flat list or missing dangerous operations.

## Acceptance Criteria

1. **Given** test generation is complete, **when** the test plan review panel is displayed, **then** the stage header updates to "Test Plan Review", **and** test cases are grouped by defect category (e.g., Happy Path, Auth Failure, Boundary), **and** each category section shows `P1`/`P2`/`P3` counts and a toggle to enable or disable the entire category.

2. **Given** a category toggle is switched off, **when** the user views the plan, **then** all tests in that category are visually marked as excluded, **and** the excluded tests are removed from `SataState`'s execution plan.

3. **Given** the test plan includes `DELETE` or `PUT` test cases, **when** those tests are displayed, **then** a destructive-operation warning is shown directly next to each affected test (for example, "This test will DELETE data"), **and** the warning is visible without requiring the user to expand or hover.

4. **Given** the developer re-enables a previously disabled category, **when** the toggle is turned back on, **then** those tests are restored to the execution plan in `SataState`.

## Tasks / Subtasks

- [x] Task 1: Extend the shared Checkpoint 2 state contract without losing the full generated plan (AC: 2, 4)
  - [x] Add `generated_test_cases: Optional[list]` to `src/core/state.py` as the preserved full test plan produced by Story 3.1.
  - [x] Add `disabled_test_categories: Optional[list]` to `src/core/state.py` so category selections persist across reruns.
  - [x] Update `initial_state()` and both state unit-test modules to include safe defaults and required-key coverage for the new fields.
  - [x] Keep `state["test_cases"]` as the currently enabled execution plan that later stories and Epic 4 execution will consume.

- [x] Task 2: Replace the `review_test_plan` stub with deterministic Checkpoint 2 reconciliation logic (AC: 1, 2, 4)
  - [x] On first entry from `generate_tests`, copy the accepted generated plan from `state["test_cases"]` into `state["generated_test_cases"]` and reset `disabled_test_categories` to `[]`.
  - [x] On subsequent reruns inside Checkpoint 2, recompute `state["test_cases"]` from `generated_test_cases` minus `disabled_test_categories` instead of mutating the full plan in place.
  - [x] Set `pipeline_stage = "review_test_plan"`, preserve `spec_confirmed = True`, and keep `test_plan_confirmed = False`.
  - [x] Do not route to `execute_tests`, do not auto-confirm the plan, and do not add destructive acknowledgements here; those belong to Story 3.3.

- [x] Task 3: Route Story 3.1 output into a real Test Plan Review stage (AC: 1)
  - [x] In `app.py`, after Checkpoint 1 confirmation runs `generate_tests`, transition to `review_test_plan` and run that node whenever usable test cases exist.
  - [x] Keep Story 3.1 partial-generation warnings visible when accepted cases exist, but land the user in Checkpoint 2 rather than the old `generate_tests` summary-only view.
  - [x] Update `src/ui/spec_review.py` and `tests/unit/test_spec_review.py` so `get_stage_display_label("review_test_plan") == "Test Plan Review"` exactly.

- [x] Task 4: Build the Checkpoint 2 UI with grouped categories, priority counts, and exclusion state (AC: 1, 2, 4)
  - [x] Add `src/ui/test_plan_review.py` with deterministic helper(s) for category labels, per-category priority counts, grouped rows, and enabled/excluded status text.
  - [x] In `app.py`, add a dedicated `elif current_stage == "review_test_plan":` rendering block that shows:
    - the "Next required action" copy for configuring the plan,
    - category sections grouped by `TestCaseModel.category`,
    - one stable-key toggle per category,
    - tests inside each section with visible enabled/excluded status.
  - [x] When a toggle changes, update `disabled_test_categories`, rerun `review_test_plan`, and ensure excluded tests remain visible in the review UI but are absent from `state["test_cases"]`.
  - [x] When re-enabled, restore the original tests from `generated_test_cases` without regenerating or reordering unrelated categories.

- [x] Task 5: Surface destructive-operation warnings inline using the existing Story 3.1 data contract (AC: 3)
  - [x] Use `test_case["is_destructive"]` as the source of truth instead of recalculating from titles or ad-hoc UI heuristics.
  - [x] Render a visible inline warning beside each destructive row/card, including the HTTP method and path where practical.
  - [x] Make the warning visible in the default view; do not require hover, expander, or drill-down.

- [x] Task 6: Add focused automated coverage for Checkpoint 2 behavior (AC: 1, 2, 3, 4)
  - [x] Add unit coverage for `src/ui/test_plan_review.py` helper outputs: grouping, priority counts, excluded status markers, and destructive-warning flags.
  - [x] Add integration coverage in `tests/integration/test_pipeline.py` for `review_test_plan` node behavior: initial full-plan capture, disabling a category removes cases from the execution plan, re-enabling restores them, and stage remains `review_test_plan`.
  - [x] Update state-related unit tests to assert the new `generated_test_cases` and `disabled_test_categories` defaults and required keys.
  - [x] Keep tests deterministic and offline; no live LLM or network calls.

## Dev Notes

### Epic & Scope Context

- Epic 3 is split into three checkpoints/stories:
  - Story 3.1: generate and validate the candidate test cases.
  - Story 3.2: review/configure the generated plan through category toggles and visible destructive warnings.
  - Story 3.3: add explicit Confirm/Reject controls plus destructive acknowledgement gating.
- Story 3.2 must turn Checkpoint 2 into a real pipeline stage, not just placeholder copy inside the `generate_tests` render block.

### Previous Story Intelligence (Story 3.1)

- `src/tools/test_case_generator.py` already normalizes categories and priorities, validates through `TestCaseModel`, and sets `is_destructive` for `PUT`/`DELETE` cases.
- `src/nodes/generate_tests.py` preserves prior cases when regeneration yields nothing usable and keeps `test_plan_confirmed = False`; Story 3.2 must preserve those behaviors.
- The current `app.py` `generate_tests` block is explicitly temporary and contains the placeholder line: "Story 3.2 will add category toggles and destructive-operation warnings."
- Story 3.1 code review fixes already resolved:
  - preserve the previous plan when regeneration yields zero accepted cases,
  - guarantee at least one retry,
  - reject empty test-case `id` and `title`.

### Current Codebase Conventions To Follow

- Canonical business logic and shared state live in `src/*`; `app/pipeline.py` and `app/state.py` are compatibility shims only.
- Deterministic formatting helpers belong in `src/ui/*`; do not bury grouping/count logic in `app.py`.
- Node handlers mutate and return the shared `SataState` object.
- `state["test_cases"]` is already the downstream execution list; preserve that contract for future Epic 4 work.
- Keep user-facing warnings safe and concise; never surface secrets or tokens in the review UI or reasoning logs.

### Architecture Compliance

- Preserve checkpoint gating: Story 3.2 ends at `review_test_plan`; it must not auto-confirm or auto-execute.
- Preserve typed shared state semantics (`SataState`) and keep category filtering deterministic/offline.
- Preserve pipeline resilience: if accepted cases exist, partial-generation warnings should not block entry into Checkpoint 2.
- Preserve visible routing: `generate_tests -> review_test_plan` should appear in the recorded pipeline trace.

### Latest Technical Notes

- Streamlit reruns the script top-to-bottom on every interaction, so category toggle state must live in stable `st.session_state` keys and be mirrored into `SataState` rather than local variables. [Source: Streamlit Session State docs]
- `st.toggle` supports `key` and `on_change`; keyed widgets preserve identity across reruns, which fits per-category toggles. [Source: Streamlit `st.toggle` docs]
- Avoid putting category toggles inside `st.form`: Streamlit forms only send widget updates on submit, and only `st.form_submit_button` can have callbacks. Immediate enable/disable behavior should stay outside forms. [Source: Streamlit Forms docs]

### Project Structure Notes

- The app is mid-migration from `app/` to `src/`. Modify canonical modules in `src/core/` and `src/nodes/`; touch `app.py` only for Streamlit rendering and event wiring.
- `src/ui/spec_review.py` already owns stage labels and checkpoint display helpers; Checkpoint 2 should follow the same pattern in a dedicated `src/ui/test_plan_review.py`.
- Do not add a new third-party UI dependency; Streamlit primitives are sufficient and already part of the stack.

### File Structure Requirements

- Add:
  - `src/ui/test_plan_review.py`
  - `tests/unit/test_test_plan_review.py`
- Modify:
  - `app.py`
  - `src/core/state.py`
  - `src/nodes/review_test_plan.py`
  - `src/ui/spec_review.py`
  - `tests/integration/test_pipeline.py`
  - `tests/unit/test_state.py`
  - `tests/unit/test_core_state.py`
  - `tests/unit/test_spec_review.py`
- Reuse as-is:
  - `src/core/graph.py`
  - `src/core/models.py`
  - `src/tools/test_case_generator.py`
  - `src/nodes/generate_tests.py` (unless a very small stale-state reset is needed)

### Testing Requirements

- Verify the stage header label is exactly `Test Plan Review`.
- Verify each category section shows accurate `P1`/`P2`/`P3` counts based on the full generated plan.
- Verify disabling a category removes only that category from `state["test_cases"]` and visually marks those tests as excluded.
- Verify re-enabling restores the original tests from `generated_test_cases`.
- Verify destructive warnings surface for `is_destructive=True` rows and do not require hover/expand.
- Keep tests deterministic, offline, and compatible with the existing `pytest` unit/integration split.

### Risks And Guardrails

- Do not overwrite the full generated plan on every rerun, or re-enable will fail.
- Do not hide excluded tests completely; the acceptance criteria require them to remain visible and marked as excluded.
- Do not detect destructive operations from free-text titles when `is_destructive` already exists.
- Do not place immediate toggle logic inside a form.
- Do not implement Story 3.3 confirm/reject buttons or destructive acknowledgement here.
- Do not clear partial results or break Story 3.1 regeneration-preservation behavior.

### Git Intelligence

- Recent baseline: `17d69c5 feat(test-generation): add test case categories and priorities`
- That change introduced the canonical `TestCaseModel`, `src/tools/test_case_generator.py`, the current `generate_tests` node, and the placeholder `app.py` summary view. Extend those patterns instead of introducing a parallel test-plan data contract.

### References

- Story requirements and acceptance criteria: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Product requirements (`FR12`-`FR16`, `FR35`): [Source: `_bmad-output/planning-artifacts/prd.md`]
- Architecture requirements (checkpoint gating, typed state, resilience, security boundary): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- UX requirements (stage clarity, toggle persistence, safety affordance coupling): [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`]
- Existing Checkpoint 2 node target: [Source: `src/nodes/review_test_plan.py`]
- Current generate-stage placeholder and Checkpoint 1 transition: [Source: `app.py`]
- Shared state contract: [Source: `src/core/state.py`]
- Test case contract and destructive-flag source: [Source: `src/core/models.py`], [Source: `src/tools/test_case_generator.py`]
- Stage label helper: [Source: `src/ui/spec_review.py`]
- Story 3.1 handoff and resolved review fixes: [Source: `_bmad-output/implementation-artifacts/3-1-test-case-generation-categories-and-priorities.md`]
- External implementation notes: [Streamlit Session State](https://docs.streamlit.io/develop/concepts/architecture/session-state), [Streamlit Forms](https://docs.streamlit.io/develop/concepts/architecture/forms), [Streamlit `st.toggle`](https://docs.streamlit.io/develop/api-reference/widgets/st.toggle)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `pytest -q tests/unit/test_state.py tests/unit/test_core_state.py tests/unit/test_spec_review.py tests/unit/test_test_plan_review.py tests/integration/test_pipeline.py`
- `python3 -m py_compile app.py src/core/state.py src/nodes/review_test_plan.py src/ui/spec_review.py src/ui/test_plan_review.py`
- `ruff check app.py src/core/state.py src/nodes/review_test_plan.py src/ui/spec_review.py src/ui/test_plan_review.py tests/unit/test_state.py tests/unit/test_core_state.py tests/unit/test_spec_review.py tests/unit/test_test_plan_review.py tests/integration/test_pipeline.py`
- `pytest -q`

### Completion Notes List

- Added `generated_test_cases` and `disabled_test_categories` to `SataState` so Checkpoint 2 can preserve the full generated plan while exposing a filtered execution plan.
- Replaced the `review_test_plan` stub with deterministic reconciliation logic that captures the first generated plan, filters `state["test_cases"]` by disabled categories, and keeps the stage anchored at `review_test_plan`.
- Added `src/ui/test_plan_review.py` for deterministic category grouping, priority counts, enabled/excluded state, and destructive-warning copy based on `is_destructive`.
- Routed successful Story 3.1 output from `generate_tests` into a real Test Plan Review UI in `app.py`, including stable Streamlit category toggles, visible exclusion state, and inline destructive warnings.
- Added unit and integration coverage for the new state fields, stage label mapping, test-plan review helper output, and `review_test_plan` node behavior.
- Verified the implementation with `ruff check`, `python3 -m py_compile`, and the full regression suite (`187 passed`).

### File List

- `app.py`
- `src/core/state.py`
- `src/nodes/review_test_plan.py`
- `src/ui/spec_review.py`
- `src/ui/test_plan_review.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_core_state.py`
- `tests/unit/test_spec_review.py`
- `tests/unit/test_state.py`
- `tests/unit/test_test_plan_review.py`
- `_bmad-output/implementation-artifacts/3-2-test-plan-review-category-toggles-and-destructive-warnings.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

- [x] [Review][Decision] Destructive warnings shown for excluded categories — resolved: keep banners visible regardless of toggle state (intentional; user should see what they are disabling)

- [x] [Review][Patch] In-place mutation of `st.session_state.state` before `run_pipeline_node` on toggle change — fixed: build a shallow copy `{**state, "disabled_test_categories": desired_disabled_categories}` and pass that to the node, leaving `st.session_state.state` untouched until the node returns successfully. [app.py, review_test_plan toggle rerun block]

- [x] [Review][Defer] `priority_counts` silently drops non-canonical priority strings [src/ui/test_plan_review.py:50] — `Counter` is built with only `.strip()` normalisation; values like `"p1"` or `"HIGH"` produce all-zero counts for `P1/P2/P3` with no warning. Upstream `TestCaseModel` enforces canonical values, so this only surfaces with malformed/restored session state — deferred, pre-existing

### Change Log

- 2026-04-06: Implemented Story 3.2 end-to-end by adding persistent Checkpoint 2 state, deterministic review-plan reconciliation, grouped category toggle UI, inline destructive warnings, and unit/integration coverage; story moved to review.
- 2026-04-11: Code review complete. 1 decision-needed, 1 patch, 1 deferred, ~14 dismissed.
