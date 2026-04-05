# Story 3.1: Test Case Generation - Categories & Priorities

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,  
I want the system to automatically generate a comprehensive set of test cases across multiple defect categories with assigned priorities,  
so that I have thorough coverage without manually designing each test.

## Acceptance Criteria

1. **Given** the spec has been confirmed and `SataState` contains the confirmed API model, **when** the test generation node runs, **then** test cases are generated across all applicable defect categories: happy path, missing data, invalid format, wrong type, auth failure, boundary, duplicate, and method not allowed, **and** each test case is assigned a priority: `P1`, `P2`, or `P3`.

2. **Given** test cases are generated, **when** the generation node validates them, **then** every test case references only endpoints and fields present in the confirmed spec (`FR35`), **and** any test case referencing a non-existent endpoint is discarded before display.

3. **Given** an endpoint has no auth requirements in the spec, **when** test cases are generated for it, **then** no auth failure test cases are generated for that endpoint.

4. **Given** the LLM returns an error or times out during generation, **when** the failure occurs, **then** the system retries once and displays a helpful message on second failure, **and** partial results already generated are preserved in `SataState`.

## Tasks / Subtasks

- [x] Task 1: Define a canonical test case contract for Epic 3 in `src/core/models.py` (AC: 1, 2)
  - [x] Add a `TestCaseModel` Pydantic model that captures the fields Story 3.x will rely on (at minimum: `id`, `endpoint_path`, `endpoint_method`, `category`, `priority`, `title`, `description`, and execution-oriented payload/expectation fields).
  - [x] Add narrow helper validation/normalization functions (or model methods) so category and priority values are constrained to known enums.
  - [x] Keep the existing `SataState["test_cases"]` type as `list[dict]` for compatibility, but validate generated records through `TestCaseModel` before writing state.
  - [x] Do not introduce execution-only result fields (`actual_status`, `passed`) here; those remain Epic 4 concerns.

- [x] Task 2: Implement test-generation logic in a dedicated tool module under `src/tools/` (AC: 1, 3, 4)
  - [x] Add `src/tools/test_case_generator.py` as canonical generation logic (do not place generation logic in `app.py`).
  - [x] Replace the placeholder prompt in `src/prompts/test_generation.md` with a strict JSON-output prompt that requests only the supported categories and priorities.
  - [x] Implement generation per endpoint so partial success is naturally preserved if one endpoint generation fails.
  - [x] Enforce category applicability rules:
    - Always generate happy path, missing data, invalid format, wrong type, boundary, duplicate, method not allowed where applicable.
    - Generate auth failure only when `endpoint["auth_required"]` is `True`.
  - [x] Assign priority deterministically (`P1`/`P2`/`P3`) and normalize casing.
  - [x] Include one retry for transient LLM failure/timeout per generation attempt.

- [x] Task 3: Add confirmed-spec validation and discard logic (`FR35`) in the same tool module (AC: 2)
  - [x] Implement `filter_test_cases_against_confirmed_spec(...)` (or equivalent) that removes cases whose `endpoint_path` + `endpoint_method` pair is absent from `parsed_api_model`.
  - [x] Validate field references from generated tests against known endpoint fields where present (parameters and request-body fields that are explicitly named in the test record).
  - [x] Return both accepted and dropped cases so the node can expose transparent counts.
  - [x] Keep this validation deterministic and offline; no LLM calls in the filter.

- [x] Task 4: Upgrade `src/nodes/generate_tests.py` from stage stub to functional node behavior (AC: 1, 2, 3, 4)
  - [x] Add guardrails: require `state["spec_confirmed"] is True` and non-empty `state["parsed_api_model"]["endpoints"]`; otherwise set a user-safe error and route back to review/ingest as appropriate.
  - [x] Generate test cases via the new tool module, validate them against the confirmed spec, and persist results in `state["test_cases"]`.
  - [x] Preserve already generated cases if later endpoint generation fails after retry; do not clear `state["test_cases"]` on partial failure.
  - [x] On full success, clear stale `error_message`; on partial failure, set a concise actionable message (for example, endpoint-level generation failed after retry, review partial plan).
  - [x] Keep `state["test_plan_confirmed"] = False`; Story 3.1 must not implement Checkpoint 2 confirmation behavior.

- [x] Task 5: Update generate-stage UI messaging in `app.py` for Story 3.1 outputs (AC: 1, 4)
  - [x] Replace the current Story 2.3 placeholder copy in `elif current_stage == "generate_tests":` with real generation summary content.
  - [x] Show generated totals and compact breakdowns by category and priority from `state["test_cases"]`.
  - [x] If generation was partial, show the node-provided warning without hiding generated tests.
  - [x] Do not implement category toggles, destructive-operation inline warnings, or Confirm/Reject Test Plan controls here; those belong to Stories 3.2 and 3.3.

- [x] Task 6: Add focused automated tests for category coverage, filtering, and retry/partial-preservation behavior (AC: 1, 2, 3, 4)
  - [x] Add unit tests for `src/tools/test_case_generator.py`:
    - Generates required categories with valid `P1`/`P2`/`P3` priorities.
    - Skips auth-failure category when `auth_required=False`.
    - Filters out non-existent endpoint references and invalid field references.
  - [x] Add integration coverage in `tests/integration/test_pipeline.py`:
    - `generate_tests` populates `state["test_cases"]` for a confirmed spec.
    - LLM failure path retries once and preserves partial results on second failure.
    - Node does not mutate `spec_confirmed`/`test_plan_confirmed` incorrectly.
  - [x] Keep tests deterministic and offline using fake/mocked LLM responses; no live network calls.

## Dev Notes

### Epic & Scope Context

- Epic 3 introduces Checkpoint 2 in three stories:
  - Story 3.1: generate and validate test cases.
  - Story 3.2: review UI with category toggles and destructive warnings.
  - Story 3.3: explicit confirm/reject test-plan checkpoint.
- Story 3.1 must produce a high-quality `state["test_cases"]` dataset that Stories 3.2/3.3 can review and gate.

### Previous Story Intelligence (Story 2.3)

- Confirm flow in `app.py` already does:
  - set `state["spec_confirmed"] = True`
  - record route `review_spec -> generate_tests`
  - execute `run_pipeline_node(state, "generate_tests")`
- `src/nodes/generate_tests.py` is currently a minimal stage stub and is the main Story 3.1 implementation target.
- Rejection flow already preserves `raw_spec` and routes back to ingestion; Story 3.1 should not alter that behavior.

### Current Codebase Conventions To Follow

- Canonical business logic belongs in `src/*`; `app/pipeline.py` is only a compatibility shim.
- Node functions mutate and return the same state object.
- Prompt content is externalized in `src/prompts/*.md`; do not hardcode long prompt strings in node files.
- Use user-safe `error_message` text; never include raw tokens/credentials.

### Suggested Test Case Record Shape (Story 3.1 baseline)

```python
{
    "id": "tc-get-users-happy-path-p1",
    "endpoint_path": "/users",
    "endpoint_method": "GET",
    "category": "happy_path",
    "priority": "P1",
    "title": "GET /users returns success payload",
    "description": "Valid request returns expected status and schema.",
    "request_overrides": {},
    "expected": {"status_code": 200},
    "is_destructive": False,
}
```

- Keep this schema additive-friendly for Stories 3.2/3.3/4.x.
- `is_destructive` should be derivable from method/test intent to support Story 3.2 warning UX.

### Architecture Compliance

- Enforce `FR35` at generation time by validating generated tests against the confirmed spec before storing/displaying.
- Keep the security boundary intact:
  - no credentials/tokens in generated test content shown to users,
  - auth metadata may drive scenario generation but not reveal secrets.
- Keep node-level resilience: failed generation should not crash the pipeline state machine.

### File Structure Requirements

- Add:
  - `src/tools/test_case_generator.py`
  - `tests/unit/test_test_case_generator.py`
- Modify:
  - `src/core/models.py` (add `TestCaseModel`)
  - `src/nodes/generate_tests.py`
  - `src/prompts/test_generation.md`
  - `app.py` (`generate_tests` stage rendering block)
  - `tests/integration/test_pipeline.py` (generation behavior coverage)
- Reuse as-is:
  - `src/core/state.py`
  - `src/core/graph.py`
  - `src/tools/spec_parser.py`
  - `src/ui/spec_review.py`

### Testing Requirements

- Validate all required categories and priorities for representative endpoint types.
- Validate auth-failure suppression when auth is not required.
- Validate discard behavior for hallucinated endpoints/fields (`FR35`).
- Validate retry-once behavior and partial-preservation semantics under simulated LLM failure.
- Keep tests offline/deterministic and compatible with existing unit/integration layout.

### Risks And Guardrails

- Do not implement Story 3.2 UI controls (category toggles/destructive warning placement) in this story.
- Do not implement Story 3.3 test-plan confirm/reject checkpoint logic in this story.
- Do not leak secrets or include auth credential values in generated artifacts.
- Do not regress Checkpoint 1 flow (`review_spec` confirm/reject paths).

### References

- Story requirements and acceptance criteria: [Source: `_bmad-output/planning-artifacts/epics.md`]
- Product requirements (`FR10`-`FR16`, `FR35`): [Source: `_bmad-output/planning-artifacts/prd.md`]
- Architecture requirements (checkpoint gating, typed shared state, security boundary): [Source: `_bmad-output/planning-artifacts/architecture.md`]
- UX requirements (stage clarity and checkpoint sequencing): [Source: `_bmad-output/planning-artifacts/ux-design-specification.md`]
- Current generate-tests implementation target: [Source: `src/nodes/generate_tests.py`]
- Graph routing and stage metadata: [Source: `src/core/graph.py`]
- Shared state contract: [Source: `src/core/state.py`]
- Existing prompt loader and prompt location conventions: [Source: `src/core/prompts.py`], [Source: `src/prompts/test_generation.md`]
- Story 2.3 handoff context: [Source: `_bmad-output/implementation-artifacts/2-3-spec-confirmation-and-rejection-checkpoint.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `pytest -q tests/unit/test_core_models.py tests/unit/test_test_case_generator.py tests/integration/test_pipeline.py -q`
- `ruff format src/core/models.py src/nodes/generate_tests.py src/tools/test_case_generator.py tests/unit/test_test_case_generator.py`
- `ruff check app.py src/core/models.py src/nodes/generate_tests.py src/tools/test_case_generator.py src/tools/__init__.py tests/unit/test_core_models.py tests/unit/test_test_case_generator.py tests/integration/test_pipeline.py`
- `pytest -q` → `177 passed`

### Completion Notes List

- Added canonical `TestCaseModel` with strict category/priority normalization and validation constants in `src/core/models.py`.
- Implemented `src/tools/test_case_generator.py` for endpoint-by-endpoint generation, retry-once behavior, fallback category completion, and FR35 filtering against confirmed endpoints/fields.
- Replaced the `generate_tests` node stub with real guardrails + generation flow, including partial-result preservation and actionable failure messaging.
- Replaced generate-stage placeholder UI in `app.py` with summary breakdowns (category/priority) and generated test plan table.
- Added unit coverage for model and generator behavior plus integration coverage for generate-node success, partial failure, retry path handling, and guardrails.
- Updated sprint/story tracking to move Story 3.1 through in-progress to review.

### File List

- `app.py`
- `src/core/models.py`
- `src/nodes/generate_tests.py`
- `src/prompts/test_generation.md`
- `src/tools/__init__.py`
- `src/tools/test_case_generator.py`
- `tests/integration/test_pipeline.py`
- `tests/unit/test_core_models.py`
- `tests/unit/test_test_case_generator.py`
- `_bmad-output/implementation-artifacts/3-1-test-case-generation-categories-and-priorities.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Implemented Story 3.1 end-to-end (test case model, generation/filtering tool, generate node behavior, generate-stage UI summary, and unit/integration coverage); story marked review.
- 2026-04-05: Code review batch-fixes — preserve previous test plan when regeneration yields no accepted cases, minimum one retry for generation, non-empty `id`/`title` on `TestCaseModel`; story marked done.

### Review Findings

- [x] [Review][Decision] Clarify preservation when regeneration yields zero accepted cases but no endpoint-level failures — **Resolved (batch):** When `accepted_cases` is empty and `previous_cases` exists, the node now keeps the previous plan and sets a `Regeneration produced…` warning instead of clearing `test_cases`. (`src/nodes/generate_tests.py`, `app.py`)

- [x] [Review][Patch] Guarantee at least one retry for endpoint generation per AC 4 — **Resolved:** `effective_retry_count = max(1, int(configured_retry_count))` so at least two attempts per endpoint. (`src/tools/test_case_generator.py`, unit test for `retry_count=0`.)

- [x] [Review][Patch] Reject empty `id` or `title` after normalization — **Resolved:** Separate validators require non-empty `id` and `title` after strip; `description` may remain empty. (`src/core/models.py`, `tests/unit/test_core_models.py`.)
