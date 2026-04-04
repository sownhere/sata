# Story 2.3: Spec Confirmation & Rejection Checkpoint

Status: review

## Story

As a developer,
I want to explicitly confirm or reject the spec at a human checkpoint,
So that no tests are ever generated against a spec I have not approved.

## Acceptance Criteria

1. **Given** the spec review panel is visible with at least one endpoint, **when** the developer reviews the spec, **then** explicit "Confirm Spec" and "Reject & Re-parse" buttons are visible **and** neither action triggers automatically because the pipeline remains paused until the user acts.

2. **Given** the developer clicks "Confirm Spec", **when** confirmation is processed, **then** `SataState` marks the spec as confirmed **and** the app advances to Test Plan Generation **and** the confirmed spec can no longer be edited unless the user explicitly returns by rejecting first.

3. **Given** the developer clicks "Reject & Re-parse", **when** rejection is processed, **then** the stage header and next-action area clearly state which step the user is returning to and why **and** the app routes back to spec ingestion with the previous input preserved for reuse/editing.

4. **Given** the spec contains auth configuration (Bearer token or API key), **when** the confirmation checkpoint is displayed, **then** auth details are shown in a dedicated labelled section **and** the safety notice reads: "These credentials will be sent only to your target API - never to the LLM."

## Tasks / Subtasks

- [x] Task 1: Add deterministic checkpoint-display helpers in `src/ui/spec_review.py` (AC: 1, 4)
  - [x] Add a pure helper that formats the top-level auth object into user-facing rows/details using the canonical shape from the parser: `type`, `scheme`, `in`, `name`
  - [x] Add a pure helper for the rejection-return message so the wording is deterministic and testable for `file`, `url`, and `chat` sources
  - [x] Keep these helpers presentation-only; do not move state-mutation or routing logic into the UI helper module
  - [x] Reuse existing `build_endpoint_summary_rows(...)`, `build_endpoint_detail_view(...)`, and `get_stage_display_label(...)` rather than duplicating review formatting

- [x] Task 2: Add the explicit confirmation panel to the `review_spec` stage in `app.py` (AC: 1, 4)
  - [x] Replace the current placeholder note that says confirm/re-parse is not implemented yet with a real checkpoint panel rendered above the edit controls
  - [x] Keep the "Next required action" copy explicit: review, then either confirm or reject
  - [x] Render "Confirm Spec" and "Reject & Re-parse" in one stable location within the checkpoint panel, not scattered through the page
  - [x] Show the dedicated auth section inside the same checkpoint panel when the parsed model has auth details or any endpoint has `auth_required=True`
  - [x] Show the exact safety copy from the acceptance criteria; do not expose secrets, token values, or raw auth headers anywhere in the UI

- [x] Task 3: Implement the confirm path using the existing graph instrumentation and a visible next stage (AC: 2)
  - [x] On confirm, set `state["spec_confirmed"] = True`, clear any stale `error_message`, and preserve the edited `parsed_api_model` as the approved source of truth
  - [x] Record the `review_spec -> generate_tests` transition via the existing instrumentation helpers so the visualization matches the checkpoint decision
  - [x] Update `src/nodes/generate_tests.py` from a pure passthrough stub to a minimal stage stub that sets `pipeline_stage = "generate_tests"` and clears stale errors without attempting real test generation yet
  - [x] After confirmation, route the app onto that visible placeholder stage so the stage header advances immediately and the review-stage editing controls are no longer shown
  - [x] Add a minimal `generate_tests` stage body in `app.py` that tells the user the spec is confirmed and Story 3.1 owns actual test generation

- [x] Task 4: Implement the reject path and preserved-input reuse flow (AC: 3)
  - [x] On reject, set `state["spec_confirmed"] = False`, clear checkpoint-only review artifacts that should not survive a restart of ingestion (`parsed_api_model`, `detected_gaps`, `gap_answers`), and preserve the original ingestion inputs needed to retry (`spec_source`, `raw_spec`)
  - [x] Record the `review_spec -> ingest_spec` transition via the existing instrumentation helpers so the visualization shows the rejection branch
  - [x] Return the app to `pipeline_stage = "spec_ingestion"` with a clear reason banner explaining that the user is back in ingestion to revise the source input
  - [x] Because Streamlit cannot pre-populate `st.file_uploader`, implement the preserved-input path around `raw_spec`: show an editable pre-filled text area or equivalent reuse control seeded from the stored raw spec content, plus a button to parse that preserved source again
  - [x] For URL imports, preserve the entered URL in `st.session_state` as a UI convenience if practical, but treat `raw_spec` as the canonical retry source because it works for both uploaded files and fetched URLs
  - [x] Do not silently auto-reparse on rejection; the user must see they have returned to ingestion and choose the next action there

- [x] Task 5: Keep the review-stage editing boundary intact while integrating the checkpoint (AC: 1, 2, 3)
  - [x] Preserve all Story 2.1 and 2.2 capabilities before confirmation: summary table, endpoint detail expanders, edit forms, add-endpoint expander, and remove actions
  - [x] Do not allow confirm when zero endpoints are present; rely on the existing guardrail and keep the checkpoint buttons hidden or disabled in that state
  - [x] Do not add parameter-level editing, schema editing, or auth editing in this story; Epic 2 scope remains checkpointing the already-editable spec
  - [x] Do not invoke real test generation, LLM calls, or checkpoint-2 UI from this story

- [x] Task 6: Add focused automated coverage for the new checkpoint behavior (AC: 1, 2, 3, 4)
  - [x] Extend `tests/unit/test_spec_review.py` to cover any new pure helpers for auth presentation and rejection-return messaging
  - [x] Add or extend integration coverage for the minimal `generate_tests` stage stub so confirming a spec lands on a visible next stage instead of a blank screen
  - [x] Add integration coverage for the review-spec routing decision path already declared in `src/core/graph.py`: confirmed route leads toward `generate_tests`, rejected route leads toward `ingest_spec`
  - [x] Add regression coverage proving the preserved-input retry path uses `raw_spec` deterministically and does not discard the original source on reject
  - [x] Keep tests offline and deterministic; do not add browser automation or live Streamlit UI tests for this story

## Dev Notes

### Epic & Scope Context

- Epic 2 owns Checkpoint 1 end to end: show the parsed API model, allow editing, then require an explicit human decision before any test generation begins.
- Story 2.1 introduced the review panel and Story 2.2 added endpoint-level editing. Story 2.3 completes Epic 2 by wiring the explicit gate.
- Story 3.1 owns real test generation. This story may only add the minimal stage handoff needed so the user can see that confirmation advanced them to the next phase.

### Story 2.2 Intelligence You Must Preserve

- The current `review_spec` block in `app.py` already renders the summary table, endpoint detail expanders, remove buttons, edit forms, add-endpoint expander, and the captured-clarifications block.
- That block currently includes a placeholder note saying confirmation and re-parse are not implemented yet. Replace that placeholder; do not rewrite the review panel from scratch.
- `remove_endpoint(...)`, `update_endpoint_field(...)`, and `add_endpoint(...)` already exist in `app/utils/spec_editor.py`. Reuse them exactly as-is.
- `src/ui/spec_review.py` already owns deterministic review formatting helpers. Keep presentation logic there; avoid reintroducing formatting logic directly into `app.py`.

### Current Codebase Conventions To Follow

- Canonical source modules are under `src/`. `app/pipeline.py` and `app/state.py` are backward-compatibility shims over `src.core.graph` and `src.core.state`.
- `app.py` is still the Streamlit entrypoint and the correct place for checkpoint button handling because it owns `st.session_state`, stage-driven rendering, and user-triggered reruns.
- `src/core/state.py`
  - `spec_confirmed` is already part of `SataState`
  - `raw_spec` and `spec_source` already exist and should be reused for the reject/retry path
  - do not add new persistent state fields unless a clear gap is unavoidable
- `src/core/graph.py`
  - already declares the two review-spec branches:
    - `("review_spec", "generate_tests"): "confirmed"`
    - `("review_spec", "ingest_spec"): "rejected"`
  - reuse `record_route_transition(...)` and `run_pipeline_node(...)`; do not invent parallel visualization bookkeeping
- `src/nodes/review_spec.py`
  - already guards against entering review with zero endpoints
  - resets `spec_confirmed` to `False` when the user re-enters the checkpoint, which protects against stale approvals
- `src/nodes/generate_tests.py`
  - is currently a pure passthrough stub, so confirmation would otherwise advance to an empty screen
  - this story may upgrade it only enough to mark the visible stage, not to generate tests

### Input-Preservation Design Decision

- Acceptance Criterion 3 requires the app to return to ingestion with the previous input preserved.
- Streamlit cannot pre-populate `st.file_uploader`, so "previous input preserved" cannot rely on rehydrating the upload widget itself.
- Use the already-stored `raw_spec` as the canonical preserved input for retry/edit:
  - if the original source was a file, show the raw spec content in an editable control and let the user re-parse it
  - if the original source was a URL, preserving the URL text is helpful, but the `raw_spec` retry path is still the reliable source of truth
  - if the original source was chat, preserve the existing conversational transcript behavior already stored in session state instead of inventing a new path
- Do not auto-run parsing when the user rejects; the point of the checkpoint is that transitions remain explicit.

### UX Requirements That Must Stay Visible

- The stage header is already driven by `state["pipeline_stage"]`; keep using that mechanism rather than a parallel label state.
- The "Next required action" message must explain both the current checkpoint and the outcome of rejection.
- Approval/rejection controls should live in a single stable location near the top of the checkpoint, not mixed into per-endpoint expanders.
- The auth section must be clearly labelled and must repeat the security boundary: credentials go only to the target API, never to the LLM.
- After confirmation, the user should immediately see a visible "Generate Tests" placeholder state rather than a blank page.

### File Structure Requirements

- Modify:
  - `app.py`
  - `src/nodes/generate_tests.py`
  - `src/ui/spec_review.py`
  - `tests/unit/test_spec_review.py`
  - one or more integration tests under `tests/integration/`
- Reuse as-is where possible:
  - `app/utils/spec_editor.py`
  - `src/core/graph.py`
  - `src/core/state.py`
  - `src/nodes/review_spec.py`
- Do not create new `app/utils/*` modules for logic that belongs in canonical `src/*` locations.

### Testing Requirements

- Verify the auth-display helper formats bearer/basic/api-key/no-auth shapes predictably.
- Verify the rejection-return helper text is deterministic for each source type.
- Verify the confirm path results in a visible `generate_tests` stage without requiring Story 3.1 implementation.
- Verify the reject path preserves `raw_spec` and returns to `spec_ingestion`.
- Verify no test introduces live HTTP, LLM calls, browser automation, or Streamlit end-to-end rendering.

### Risks And Guardrails

- Do not break Story 2.2 editing behavior while adding the checkpoint panel.
- Do not discard the edited approved model on confirm; it is the contract for Story 3.x.
- Do not leak auth secrets or suggest that credentials are sent to the LLM.
- Do not rely on the upload widget itself for preserved-input UX; that approach is not supported by Streamlit.
- Do not implement real test generation, category toggles, destructive-operation warnings for tests, or checkpoint-2 controls in this story.

### Project Structure Notes

- Earlier Epic 2 story files still mention pre-refactor `app/utils/*` and `app/pipeline.py` implementation paths. The live repo now uses canonical `src/*` modules with `app/*` shims.
- Treat `src/*` as authoritative for new logic and tests. Touch `app.py` only where the Streamlit entrypoint must orchestrate UI actions and reruns.

### References

- Story requirements and Epic 2 context: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Product requirements FR6-FR9: [Source: `_bmad-output/planning-artifacts/prd.md`]
- Architecture requirement for checkpoint gating and shared state: [Source: `_bmad-output/planning-artifacts/architecture.md`]
- UX guidance for visible stage gating, rejection transparency, and single-location approvals: [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`]
- Previous story context and current review-panel behavior: [Source: `_bmad-output/implementation-artifacts/2-2-spec-editing-modify-add-and-remove-endpoints-and-fields.md`]
- Current Streamlit review-stage implementation: [Source: `app.py`]
- Shared state contract: [Source: `src/core/state.py`]
- Review-spec routing and visualization helpers: [Source: `src/core/graph.py`]
- Review-spec guardrail node: [Source: `src/nodes/review_spec.py`]
- Generate-tests stub: [Source: `src/nodes/generate_tests.py`]
- Review formatting helpers: [Source: `src/ui/spec_review.py`]
- Auth extraction contract: [Source: `src/tools/spec_parser.py`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `pytest -q tests/unit/test_spec_review.py tests/integration/test_pipeline.py` -> `39 passed`
- `pytest -q` -> `165 passed`
- `ruff check app.py src/ui/spec_review.py src/nodes/review_spec.py src/nodes/generate_tests.py tests/unit/test_spec_review.py tests/integration/test_pipeline.py` -> passed

### Completion Notes List

- Added deterministic checkpoint helpers in `src/ui/spec_review.py` for auth display, auth-section visibility, and source-specific rejection messaging.
- Replaced the placeholder review-stage note in `app.py` with a real Checkpoint 1 panel containing `Confirm Spec` and `Reject & Re-parse` actions in one stable location.
- Implemented the confirm handoff to a visible `generate_tests` placeholder stage using the existing graph instrumentation and a minimal `src/nodes/generate_tests.py` stage stub.
- Added a pure rejection helper in `src/nodes/review_spec.py` so review-only state is cleared while `spec_source` and `raw_spec` are preserved for retry.
- Added the preserved raw-spec editor and re-parse button in ingestion, plus keyed URL input persistence via `st.session_state.spec_url_input`.
- Extended unit and integration coverage for auth formatting, rejection messaging, review-spec branch routing, visible generate-tests staging, and preserved-input rejection behavior.

### File List

- `app.py`
- `src/nodes/generate_tests.py`
- `src/nodes/review_spec.py`
- `src/ui/spec_review.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_spec_review.py`
- `_bmad-output/implementation-artifacts/2-3-spec-confirmation-and-rejection-checkpoint.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- `2026-04-04`: Implemented Story 2.3 checkpoint confirmation/rejection flow, preserved-source retry UX, minimal generate-tests stage stub, and story-scoped unit/integration coverage.
