# Story 2.2: Spec Editing — Modify, Add & Remove Endpoints and Fields

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to edit the parsed spec directly in the review panel — modifying field values, adding missing endpoints, or removing incorrect ones —
So that I can correct parser errors or fill in details before committing to test generation.

## Acceptance Criteria

1. **Given** the spec review panel is displayed, **when** the developer clicks to edit a field (e.g., a parameter type or response schema), **then** the field becomes editable inline **and** changes are immediately reflected in `SataState` on save.

2. **Given** the developer wants to add a new endpoint, **when** they use the "Add endpoint" action, **then** a form appears requesting: path, method, parameters, and optional schema fields **and** the new endpoint is appended to the spec in `SataState`.

3. **Given** the developer wants to remove an endpoint, **when** they trigger the remove action on an endpoint row, **then** the endpoint is removed from the display and from `SataState` **and** no other endpoints are affected.

4. **Given** the developer makes edits and then navigates away or refreshes, **when** they return to the review panel, **then** their edits are preserved in `SataState` (not lost on re-render).

## Tasks / Subtasks

- [ ] Task 1: Add spec-mutation helpers to `app/utils/spec_editor.py` (AC: 1, 2, 3)
  - [ ] Implement `update_endpoint_field(parsed_api_model: dict, endpoint_index: int, field: str, value) -> dict` — returns a new dict with the field updated; does not mutate in place
  - [ ] Implement `add_endpoint(parsed_api_model: dict, new_endpoint: dict) -> dict` — appends a valid endpoint dict to the endpoints list; validates required keys (`path`, `method`) before appending; raises `ValueError` for missing required fields
  - [ ] Implement `remove_endpoint(parsed_api_model: dict, endpoint_index: int) -> dict` — removes the endpoint at the given index; no-op if index is out of range
  - [ ] Keep all helpers pure (no Streamlit imports, no side effects); return a new `parsed_api_model` dict each time
  - [ ] Do NOT modify `app/utils/spec_review.py` — that module is display-only

- [ ] Task 2: Add inline edit controls to the Spec Review panel in `app.py` (AC: 1, 4)
  - [ ] Wrap existing endpoint detail expanders (from Story 2.1) with per-endpoint edit forms using `st.form` keyed by endpoint index (e.g., `form_edit_{i}`)
  - [ ] Expose editable fields within the form: `path` (text), `method` (selectbox: GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS), `summary` (text), `operation_id` (text)
  - [ ] On form submit ("Save changes"), call `update_endpoint_field` for each changed field, write the resulting model back to `st.session_state.state["parsed_api_model"]`, then `st.rerun()`
  - [ ] Do NOT expose parameter-level or schema-level sub-editing in this story — endpoint-level fields only
  - [ ] Keep the read-only summary table (from Story 2.1) above the edit forms so the developer can see all endpoints at a glance

- [ ] Task 3: Add "Add endpoint" form in `app.py` (AC: 2, 4)
  - [ ] Render a collapsible "Add endpoint" section below the endpoint list (use `st.expander("+ Add endpoint", expanded=False)`)
  - [ ] Inside the expander, use a single `st.form("form_add_endpoint")` with fields: path (text, required), method (selectbox, required), summary (text, optional), operation_id (text, optional)
  - [ ] On form submit ("Add endpoint"), call `add_endpoint(...)` with the minimal canonical endpoint shape, write result to `st.session_state.state["parsed_api_model"]`, then `st.rerun()`
  - [ ] The minimal canonical shape for a new endpoint must match the Story 1.2 contract:
    ```python
    {
        "path": path,
        "method": method,
        "operation_id": operation_id or "",
        "summary": summary or "",
        "parameters": [],
        "request_body": None,
        "response_schemas": {},
        "auth_required": False,
        "tags": [],
    }
    ```
  - [ ] Show a validation error via `st.error(...)` if path or method is empty — do not submit the form

- [ ] Task 4: Add "Remove endpoint" button per endpoint in `app.py` (AC: 3, 4)
  - [ ] Add a "Remove" button inside each endpoint's expander (outside any `st.form`, using `st.button(f"Remove endpoint {i}", key=f"btn_remove_{i}")`)
  - [ ] On click, call `remove_endpoint(...)`, write result to `st.session_state.state["parsed_api_model"]`, then `st.rerun()`
  - [ ] After removal, if zero endpoints remain, the panel must show the empty-state message (already implemented in Story 2.1 pipeline node — no new logic needed, just trigger `st.rerun()`)
  - [ ] Do NOT add a confirmation dialog — removal is immediate

- [ ] Task 5: Add focused automated tests for spec-mutation helpers (AC: 1, 2, 3)
  - [ ] Add `tests/test_spec_editor.py` covering:
    - `update_endpoint_field` — updates a known field; leaves other endpoints untouched; returns new dict (not same reference)
    - `add_endpoint` — appends a valid endpoint; raises `ValueError` for missing `path` or `method`; preserves existing endpoints
    - `remove_endpoint` — removes the correct endpoint by index; no-op for out-of-range index; does not affect other endpoints
  - [ ] Keep all tests offline and deterministic; no Streamlit imports in test file

## Dev Notes

### Epic & Scope Context

- Epic 2 owns Checkpoint 1: spec review and confirmation before test generation.
- Story 2.1 built the **read-only** panel (summary table + expanders).
- **This story (2.2) adds editing controls** to that panel.
- Story 2.3 will add the explicit "Confirm Spec" / "Reject & Re-parse" buttons — do NOT add those here.
- Scope boundary: the only user-facing additions in this story are inline edit forms, the "Add endpoint" expander, and per-endpoint "Remove" buttons. Nothing else.

### Previous Story Intelligence (Story 2.1)

- `app/utils/spec_review.py` — read-only display helpers; do NOT add mutation logic here
- `app.py` line 413: `elif current_stage == "review_spec":` — this is where all Story 2.2 UI additions go
- The current `review_spec` section in `app.py` is a placeholder stub (`st.info("Story 2.1 will provide the full review panel...")`). Story 2.1 (status: review) established the utilities and tests, but the full review panel rendering in `app.py` may still be minimal. Story 2.2 must render the full editing panel correctly regardless of what Story 2.1 left in `app.py`.
- `app/utils/spec_review.py` provides `build_endpoint_summary_rows(parsed_api_model)` and `build_endpoint_detail_view(endpoint)` — reuse for the read-only summary above editing controls
- The canonical `parsed_api_model` shape from Story 1.2 must not change:
  ```python
  {
      "endpoints": [
          {
              "path": str,
              "method": str,
              "operation_id": str,
              "summary": str,
              "parameters": list,
              "request_body": None | dict,
              "response_schemas": dict,
              "auth_required": bool,
              "tags": list,
          }
      ],
      "auth": {"type": ..., "scheme": ..., "in": ..., "name": ...},
      "title": str,
      "version": str,
  }
  ```

### Current Codebase Conventions To Follow

- `app.py`
  - Stage-driven rendering keyed on `state["pipeline_stage"]`; the review block is `elif current_stage == "review_spec":`
  - Streamlit form pattern: use `st.form(key)` + `st.form_submit_button(...)` for batched saves (avoids multiple reruns per keystroke)
  - For remove buttons that live outside a form, use `st.button(label, key=unique_key)` and call `st.rerun()` after mutation
  - All state mutations write to `st.session_state.state[field]` then call `st.rerun()`
  - Never raise exceptions in UI code — catch and show `st.error(...)`
- `app/pipeline.py`
  - Node functions mutate and return the same state dict in place — NOT applicable here; editing bypasses the LangGraph pipeline and writes directly to session state
  - `spec_confirmed` remains `False` until Story 2.3 adds confirm logic
- `app/state.py`
  - `parsed_api_model` is `Optional[dict]` — always guard with `or {}`
  - Do NOT add new fields to `SataState` for this story; editing state lives in `parsed_api_model["endpoints"]` itself

### Architecture Compliance

- Human-in-the-loop must remain **state-driven**: editing writes to `SataState["parsed_api_model"]` in `st.session_state.state`, not to a parallel UI-only structure.
- Spec edits do NOT re-run the pipeline — editing is a direct session state mutation followed by `st.rerun()`.
- Never expose `raw_spec`, tokens, or credentials in any edit form.
- `spec_confirmed` must stay `False` while the user is editing; Story 2.3 owns the confirmation gate.

### Streamlit Form Pattern — Key Design Choice

Use `st.form` for the per-endpoint edit and add-endpoint forms. This is the correct pattern because:
- Batches all field changes into a single submission (no intermediate reruns on every keystroke)
- Preserves `st.session_state` correctly across reruns (AC 4)
- Compatible with `streamlit>=1.32.0` floor

**Do NOT use `on_change` callbacks** for individual text inputs in this story — it creates complex state synchronization issues and conflicts with LangGraph's own state management pattern.

### File Structure Requirements

- Add:
  - `app/utils/spec_editor.py` — pure mutation helpers (no Streamlit imports)
  - `tests/test_spec_editor.py` — unit tests for spec_editor helpers
- Modify:
  - `app.py` — add editing UI to the `review_spec` stage block
- Do NOT modify:
  - `app/utils/spec_review.py` — display helpers only
  - `app/pipeline.py` — no new node behavior needed
  - `app/state.py` — no new state fields

### Testing Requirements

- All tests offline and deterministic (no Streamlit imports, no live HTTP, no LLM calls)
- Test pure helpers in `app/utils/spec_editor.py` only — no UI rendering tests
- Cover:
  - `update_endpoint_field`: field updated correctly; other endpoints unchanged; returns new dict (not same `id()`)
  - `add_endpoint`: new endpoint appended; existing endpoints preserved; `ValueError` on empty path; `ValueError` on empty method
  - `remove_endpoint`: correct index removed; adjacent endpoints intact; out-of-range index returns unchanged model
- Run `pytest tests/test_spec_editor.py` to verify — should pass completely offline

### Risks And Guardrails

- **Regression risk:** Mutating the canonical `parsed_api_model` shape will break Story 1.2 parser contract tests and Story 2.1 display helpers. Keep the spec structure identical.
- **Scope creep risk:** Do NOT implement parameter-level editing, response schema editing, auth editing, or Confirm/Reject — those belong to future stories.
- **State loss risk:** Never store edit state in a local Python variable across Streamlit reruns. Always write to `st.session_state.state["parsed_api_model"]` before calling `st.rerun()`.
- **Form key collision risk:** Each `st.form` must have a unique key (e.g., `form_edit_0`, `form_edit_1`, `form_add_endpoint`). Duplicate keys cause Streamlit runtime errors.
- **Remove button outside form:** Streamlit buttons inside `st.form` only fire on form submit. Place remove buttons outside any `st.form` block with their own unique keys.

### References

- Story requirements and acceptance criteria: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Canonical parsed model contract: [Source: `_bmad-output/implementation-artifacts/1-2-openapi-swagger-file-upload-and-parsing.md`]
- Read-only display helpers: [Source: `app/utils/spec_review.py`]
- Current spec review rendering block: [Source: `app.py`, line 413]
- SataState definition: [Source: `app/state.py`]
- Pipeline node patterns: [Source: `app/pipeline.py`]
- Story 2.1 dev notes (scope boundary, canonical model guardrail): [Source: `_bmad-output/implementation-artifacts/2-1-spec-review-panel-endpoint-table-display.md`]
- Streamlit `st.form` docs: [Source: `https://docs.streamlit.io/develop/api-reference/execution-flow/st.form`]

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

_TBD_

### Completion Notes List

_TBD_

### File List

_TBD_

### Change Log

_TBD_
