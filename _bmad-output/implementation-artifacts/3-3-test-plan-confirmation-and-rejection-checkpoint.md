# Story 3.3: Test Plan Confirmation & Rejection Checkpoint

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to explicitly confirm the test plan or reject it to regenerate,
so that no tests execute until I've reviewed and acknowledged everything — including any destructive operations.

## Acceptance Criteria

1. **Given** the test plan review panel is visible, **when** the developer has reviewed the plan, **then** explicit "Confirm Test Plan" and "Reject & Regenerate" buttons are visible at the bottom of the panel, **and** neither action triggers automatically.

2. **Given** the enabled test plan (`state["test_cases"]`) contains destructive operations (`is_destructive=True`) and the developer clicks "Confirm Test Plan", **when** the ack UI renders, **then** a blocking acknowledgement section appears listing all destructive endpoints from the enabled plan, requiring two explicit checkboxes before "Proceed" is enabled, **and** the pipeline does not advance until the developer confirms both.

3. **Given** all destructive tests are acknowledged (or none exist) and the developer confirms, **when** confirmation is processed, **then** `SataState` sets `test_plan_confirmed = True`, `pipeline_stage` advances to `"execute_tests"`, and `state["test_cases"]` remains the final filtered execution set.

4. **Given** the developer clicks "Reject & Regenerate", **when** rejection is processed, **then** `test_plan_confirmed` stays `False`, test-plan-specific state is cleared, the pipeline routes back to `generate_tests`, auto-transitions to `review_test_plan`, and the user sees the fresh plan — the confirmed spec is never touched.

## Tasks / Subtasks

- [x] Task 1: Add `extract_destructive_test_groups` helper to `src/ui/test_plan_review.py` (AC: 2)
  - [x] Add function `extract_destructive_test_groups(test_cases: list[dict]) -> list[dict]` that filters `is_destructive=True` cases from the provided list and groups them by `(endpoint_method, endpoint_path)`, returning `[{"endpoint_method": ..., "endpoint_path": ..., "count": N}, ...]` sorted by method then path.
  - [x] Return empty list when `test_cases` is None, empty, or has no destructive entries.
  - [x] Add unit tests in `tests/unit/test_test_plan_review.py`: (a) empty input returns `[]`, (b) mixed input returns only destructive groups with correct counts, (c) multiple tests on same endpoint are collapsed into one group with summed count.

- [x] Task 2: Add `prepare_rejection_for_test_regeneration` to `src/nodes/review_test_plan.py` (AC: 4)
  - [x] Mirror the `prepare_rejection_for_reparse` pattern from `src/nodes/review_spec.py`.
  - [x] Clear `generated_test_cases`, `disabled_test_categories`, `test_cases` to `None`; set `test_plan_confirmed = False`; set `pipeline_stage = "generate_tests"`; clear `error_message`.
  - [x] Preserve `spec_confirmed = True` and all spec-related state — do NOT clear `parsed_api_model`, `raw_spec`, `gap_answers`, etc.
  - [x] Add integration tests in `tests/integration/test_pipeline.py`: (a) rejection clears all test-plan fields to None, (b) rejection preserves `spec_confirmed`, `parsed_api_model`, and `gap_answers`, (c) `pipeline_stage` is set to `"generate_tests"`.

- [x] Task 3: Update `execute_tests` stub to set `pipeline_stage = "execute_tests"` (AC: 3)
  - [x] In `src/nodes/execute_tests.py`, add `state["pipeline_stage"] = "execute_tests"` before returning. This is the minimal change required so that after Story 3.3 routes to the stub, `pipeline_stage` advances and the UI does not re-render the `review_test_plan` block.
  - [x] Do NOT add any other logic — execution is Story 4.1 scope.
  - [x] Update `tests/integration/test_pipeline.py` to assert that the stub sets `pipeline_stage = "execute_tests"`.

- [x] Task 4: Add Checkpoint 2 confirm/reject UI and destructive ack to `app.py` (AC: 1, 2, 3, 4)
  - [x] At the bottom of the `elif current_stage == "review_test_plan":` block (after the enabled-count `st.success`), add:
    - Optional rejection feedback text area with a stable session_state key (`checkpoint2_reject_feedback`).
    - Side-by-side `st.columns(2)` containing "Confirm Test Plan" (primary) and "Reject & Regenerate" (secondary) buttons.
  - [x] **Confirm path — no destructive tests:** if `extract_destructive_test_groups(state.get("test_cases") or [])` returns empty, set `state["test_plan_confirmed"] = True`, `record_route_transition`, `run_pipeline_node(state, "execute_tests")`, update session state, `st.rerun()`.
  - [x] **Confirm path — destructive tests exist:** set `st.session_state["checkpoint2_ack_pending"] = True`, `st.rerun()`. Do NOT set `test_plan_confirmed` yet.
  - [x] **Ack section (rendered when `checkpoint2_ack_pending`):** Show `st.warning` with bulleted list of destructive endpoint groups. Two checkboxes with stable keys. "Proceed" (disabled unless both checked) and "Cancel" buttons. Proceed: set `test_plan_confirmed = True`, clear ack session state, route and rerun. Cancel: clear ack keys, rerun.
  - [x] **Reject path:** call `prepare_rejection_for_test_regeneration`, clear ack and toggle session state, route to `generate_tests`, auto-route to `review_test_plan` if test cases exist. Update session state, `st.rerun()`.
  - [x] **Do NOT use `st.form`** for either button group or the ack section.
  - [x] Add `elif current_stage == "execute_tests":` block with confirmation summary and test count.

- [x] Task 5: Reset ack session state on plan regeneration (AC: 2, 4)
  - [x] Extend `_reset_test_plan_toggle_state()` in `app.py` to also delete keys: `"checkpoint2_ack_pending"`, `"checkpoint2_ack_1"`, `"checkpoint2_ack_2"`, `"checkpoint2_reject_feedback"`.

## Dev Notes

### Epic & Scope Context

Story 3.3 is the final checkpoint story in Epic 3:
- Story 3.1: Generates candidate test cases (categories, priorities, `is_destructive`).
- Story 3.2: Category toggles, exclusion marking, inline destructive warnings. Ends at `pipeline_stage = "review_test_plan"` with `test_plan_confirmed = False`.
- **Story 3.3 (this story):** Adds explicit Confirm/Reject controls with destructive acknowledgement gating. Sets `test_plan_confirmed = True` and advances to `execute_tests`.

### What Story 3.2 Delivered (Build On, Don't Break)

- `state["generated_test_cases"]` — full plan before category filtering; never overwrite except on fresh plan capture.
- `state["disabled_test_categories"]` — sorted list of excluded category keys; preserved across toggle reruns.
- `state["test_cases"]` — filtered execution set (generated minus disabled); this is what gets executed; Story 3.3 freezes it at confirmation.
- `src/ui/test_plan_review.py` exports: `build_test_plan_review_sections`, `filter_enabled_test_cases`, `format_test_category_label`. Extend this module with `extract_destructive_test_groups` — do NOT add it to `app.py`.
- `src/nodes/review_test_plan.py` already keeps `test_plan_confirmed = False` and stays anchored at `pipeline_stage = "review_test_plan"`. The rejection helper belongs here (mirrors `prepare_rejection_for_reparse`).
- `app.py` `review_test_plan` block runs from `elif current_stage == "review_test_plan":` and ends with the toggle-change rerun logic. Task 4 adds the confirm/reject section at the end of that `else:` branch (inside the `if not generated_test_cases: ... else: ...` block, after the `st.success` count line).

### Checkpoint 1 Pattern to Mirror Exactly (Story 2.3)

```python
# In app.py, review_spec block — use this as the 1:1 template for Story 3.3

# Reject path
if reject_clicked:
    updated_state = prepare_rejection_for_reparse(state)
    record_route_transition(updated_state, "review_spec", target_override="ingest_spec")
    updated_state = run_pipeline_node(updated_state, "ingest_spec")
    st.session_state.state = updated_state
    st.rerun()

# Confirm path
if confirm_clicked:
    state["spec_confirmed"] = True
    record_route_transition(state, "review_spec", target_override="generate_tests")
    updated_state = run_pipeline_node(state, "generate_tests")
    if updated_state.get("test_cases"):
        _reset_test_plan_toggle_state()
        record_route_transition(updated_state, "generate_tests", target_override="review_test_plan")
        updated_state = run_pipeline_node(updated_state, "review_test_plan")
    st.session_state.state = updated_state
    st.rerun()
```

**Story 3.3 confirm path (non-destructive) mirrors the Checkpoint 1 confirm pattern:**
```python
# (non-destructive or after ack)
pending_state = {**state, "test_plan_confirmed": True}
record_route_transition(pending_state, "review_test_plan", target_override="execute_tests")
updated_state = run_pipeline_node(pending_state, "execute_tests")
st.session_state.state = updated_state
st.rerun()
```

**Always build a shallow copy** (`{**state, ...}`) before mutating, consistent with the P1 patch applied during the Story 3.2 code review.

**Story 3.3 reject path:**
```python
pending_state = prepare_rejection_for_test_regeneration({**state})
_reset_test_plan_toggle_state()  # also clears ack keys (Task 5)
record_route_transition(pending_state, "review_test_plan", target_override="generate_tests")
updated_state = run_pipeline_node(pending_state, "generate_tests")
if updated_state.get("test_cases"):
    record_route_transition(updated_state, "generate_tests", target_override="review_test_plan")
    updated_state = run_pipeline_node(updated_state, "review_test_plan")
st.session_state.state = updated_state
st.rerun()
```

### Destructive Acknowledgement — Inline Pattern (No `st.dialog`)

Do NOT use `st.dialog` or `st.modal` — requires Streamlit ≥ 1.29 and is not in the current stack. Use session-state-driven conditional rendering instead, exactly like the Story 3.2 toggle pattern.

**Stable session state keys for ack:**
- `"checkpoint2_ack_pending"` — `bool`, True while ack section is visible.
- `"checkpoint2_ack_1"` — `bool`, checkbox: "I understand these tests will DELETE or modify real data."
- `"checkpoint2_ack_2"` — `bool`, checkbox: "I am targeting a safe, non-production test environment."
- `"checkpoint2_reject_feedback"` — `str`, optional rejection feedback text area.

**Rendering order within the `review_test_plan` block (after existing content):**
1. Always render the rejection feedback text area and both buttons.
2. If `checkpoint2_ack_pending` → render the ack section above the buttons (or replace them). The buttons should be disabled while ack is pending to avoid double-triggers.
3. Ack section contains: `st.warning` with destructive group list, two `st.checkbox` (keyed), `st.columns(2)` with "Proceed" (disabled unless both checked) and "Cancel".

### Routing & Graph Contract (CRITICAL)

The routing functions are already wired in `src/core/graph.py`:
```python
# _route_test_plan already reads test_plan_confirmed:
def _route_test_plan(state: SataState) -> str:
    return "execute_tests" if state.get("test_plan_confirmed") else "generate_tests"
```
Story 3.3 must set `test_plan_confirmed = True` before calling `run_pipeline_node(state, "execute_tests")` so the LangGraph router works correctly if the graph is ever invoked end-to-end. Use the `{**state, "test_plan_confirmed": True}` shallow-copy pattern.

`execute_tests` stub returns state unchanged — Task 3 adds `state["pipeline_stage"] = "execute_tests"` so the `app.py` top-level `current_stage` moves forward after the `st.rerun()`.

### Architecture Compliance

- **Dependency rule:** `src/ui/test_plan_review.py` is a UI module — it may import from `src/core/` but NOT from `src/nodes/`. The `extract_destructive_test_groups` helper belongs there because it formats display data.
- **No new third-party dependencies** — use Streamlit primitives and Python stdlib only.
- **Do NOT import `prepare_rejection_for_test_regeneration` from a UI file** — it's a node helper; import it in `app.py` directly from `src.nodes.review_test_plan`.
- **Keep `test_cases` as the execution contract** — Story 3.3 must not change `state["test_cases"]` at confirmation; it is already the filtered execution set.
- **Checkpoint gating is absolute:** Story 3.3 ends at `pipeline_stage = "execute_tests"`. It must not auto-execute, bypass the ack, or clear the confirmed spec.

### Project Structure Notes

**Modify:**
- `src/ui/test_plan_review.py` — add `extract_destructive_test_groups`
- `src/nodes/review_test_plan.py` — add `prepare_rejection_for_test_regeneration`
- `src/nodes/execute_tests.py` — set `pipeline_stage = "execute_tests"` (1-line)
- `app.py` — Checkpoint 2 confirm/reject UI, ack section, `execute_tests` stage block, ack key cleanup in `_reset_test_plan_toggle_state`
- `tests/unit/test_test_plan_review.py` — add tests for `extract_destructive_test_groups`
- `tests/integration/test_pipeline.py` — add tests for rejection helper and execute_tests stub

**Do NOT modify:**
- `src/core/state.py` — no new state fields needed (ack is UI session state; `test_plan_confirmed` already exists)
- `src/core/graph.py` — routing already correct for Story 3.3
- `src/nodes/generate_tests.py` — rejection calls it as-is
- `src/ui/spec_review.py` — stage labels already cover both checkpoints
- `tests/unit/test_state.py`, `test_core_state.py` — no new state fields added

### Testing Requirements

- All tests must be deterministic and offline (no LLM calls, no network).
- `extract_destructive_test_groups`: test empty input, mixed input, duplicate-endpoint collapsing.
- `prepare_rejection_for_test_regeneration`: test that spec state survives, test-plan state is cleared.
- `execute_tests` stub: test that `pipeline_stage == "execute_tests"` after the call.
- Keep tests within the existing `pytest` unit/integration split.

### Risks & Guardrails

- **Do NOT set `test_plan_confirmed = True` before the ack is complete** when destructive tests exist. The `checkpoint2_ack_pending` flag gates this.
- **Do NOT clear `generated_test_cases` on confirmation** — only on rejection. Re-confirmation after a failed execution (future story) must still see the original full plan.
- **Do NOT implement any execution logic** — the `execute_tests` node is a stub that only sets `pipeline_stage`. All HTTP execution is Story 4.1.
- **Do NOT add a confirm/reject button to `generate_tests` stage** — that stage is still the interim plan-preview view from Story 3.1. Checkpoint 2 controls live only in the `review_test_plan` block.
- **Do NOT use `st.form`** for ack checkboxes or buttons — forms only submit on `st.form_submit_button` and cannot have `on_change` callbacks, breaking immediate ack behavior.
- **`prepare_rejection_for_test_regeneration` must never touch `spec_confirmed`** — the user already confirmed the spec at Checkpoint 1.

### References

- Checkpoint 1 confirm/reject pattern: [`app.py`, `review_spec` block ~line 463–522]
- Rejection helper pattern: [`src/nodes/review_spec.py`, `prepare_rejection_for_reparse`]
- Routing function: [`src/core/graph.py`, `_route_test_plan` line 185–187]
- execute_tests stub: [`src/nodes/execute_tests.py`]
- Destructive test source of truth: [`src/core/models.py`, `TestCaseModel.is_destructive`]
- Story 3.2 handoff: [`_bmad-output/implementation-artifacts/3-2-test-plan-review-category-toggles-and-destructive-warnings.md`]
- State contract: [`src/core/state.py`]
- UI helpers: [`src/ui/test_plan_review.py`]
- Checkpoint 2 node: [`src/nodes/review_test_plan.py`]
- Streamlit session state: [Streamlit Session State docs — no `st.dialog` in current version]
- Architecture checkpoint gating requirements: [`_bmad-output/planning-artifacts/architecture.md`]
- UX safety affordance coupling: [`_bmad-output/planning-artifacts/ux-design-specification.md`]
- PRD FR13–FR16, FR35: [`_bmad-output/planning-artifacts/prd.md`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `pytest -q tests/unit/test_test_plan_review.py`
- `pytest -q tests/integration/test_pipeline.py`
- `python3 -m py_compile app.py src/nodes/review_test_plan.py src/nodes/execute_tests.py src/ui/test_plan_review.py`
- `ruff check app.py src/nodes/review_test_plan.py src/nodes/execute_tests.py src/ui/test_plan_review.py tests/unit/test_test_plan_review.py tests/integration/test_pipeline.py`
- `pytest -q` (194 passed)

### Completion Notes List

- Added `extract_destructive_test_groups` to `src/ui/test_plan_review.py` — groups `is_destructive=True` test cases by endpoint, returns sorted `[{endpoint_method, endpoint_path, count}]` list for the ack prompt.
- Added `prepare_rejection_for_test_regeneration` to `src/nodes/review_test_plan.py` — mirrors `prepare_rejection_for_reparse`; clears all test-plan state, preserves confirmed spec, sets `pipeline_stage = "generate_tests"`.
- Updated `execute_tests` stub to set `pipeline_stage = "execute_tests"` so the UI advances past `review_test_plan` after confirmation.
- Added Checkpoint 2 confirm/reject UI to `app.py`: rejection feedback textarea, "Confirm Test Plan" and "Reject & Regenerate" buttons, inline destructive ack section (session-state driven, no `st.form`), `execute_tests` stage display block.
- Extended `_reset_test_plan_toggle_state()` to also clear all Checkpoint 2 ack session state keys on plan regeneration.
- All shallow-copy patterns (`{**state, ...}`) used consistently — no in-place mutation of `st.session_state.state` before node calls.
- 194 tests pass; 7 new tests added (4 unit, 3 integration).

### File List

- `src/ui/test_plan_review.py`
- `src/nodes/review_test_plan.py`
- `src/nodes/execute_tests.py`
- `app.py`
- `tests/unit/test_test_plan_review.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/3-3-test-plan-confirmation-and-rejection-checkpoint.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

- [x] [Review][Patch] Checkpoint 2 confirm path eagerly ran `execute_tests` even when `target_api_url` was unset, landing users on an error screen with only a "Retry" button and no way to supply the URL (dead-end). Fixed by (a) skipping the pre-run when no URL is set so the `execute_tests` stage shows the URL form first, and (b) refactoring the `execute_tests` stage so the error branch re-renders the URL input + auth status + Run/Retry button instead of a bare error. Applies to both the non-destructive confirm branch and the destructive-ack Proceed branch. [`app.py`, `review_test_plan` confirm/proceed blocks and `execute_tests` stage]

- [x] [Review][Patch] Re-running the full test plan through the Story 5.4 loop never reset `iteration_count`, so every subsequent re-run accumulated against `execute_tests`' `max_iterations` (NFR5 = 10). After the third run with a 4+ test plan, executions halted prematurely. Fixed by resetting `iteration_count = 0` in `_prepare_rerun_tracking` and in the `execute_tests` Retry path; added `tests/unit/test_results_iteration.py` regression coverage for multiple sequential re-runs. [`app.py`, `_prepare_rerun_tracking` and `execute_tests` Retry block]

- [x] [Review][Decision] Story 3.3 does not fork `test_plan_confirmed` for destructive-only test plans — same flag gates both destructive and non-destructive confirmations, with the ack UI as a pre-gate. Resolved: keep the single boolean; the session-state `checkpoint2_ack_pending` flag already guarantees destructive tests can't advance without acknowledgement.

### Change Log

- 2026-04-11: Implemented Story 3.3 — Checkpoint 2 confirm/reject controls with destructive acknowledgement gating, rejection helper, execute_tests stub advancement, and full test coverage; story moved to review.
- 2026-04-11: Code review complete. 2 patches landed (Checkpoint 2 → execute_tests dead-end, re-run iteration guard reset), 1 decision confirmed.
