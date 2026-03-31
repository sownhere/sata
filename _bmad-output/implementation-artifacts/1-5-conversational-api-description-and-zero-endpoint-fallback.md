# Story 1.5: Conversational API Description & Zero-Endpoint Fallback

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to describe my API endpoints through conversational chat, either by choice or when my uploaded spec contains zero parseable endpoints,
so that I can still build a complete test suite even without a formal spec file.

## Acceptance Criteria

1. **Given** the developer selects "Describe my API manually" instead of uploading a file or URL, **when** the conversational ingestion node activates, **then** a chat interface is presented with a prompt explaining what information is needed (endpoint paths, methods, expected inputs/outputs).

2. **Given** the developer's uploaded spec parses successfully but contains zero endpoints, **when** the pipeline reaches the endpoint extraction node, **then** the system automatically switches to conversational mode, **and** displays a clear fallback message: "No endpoints were found in your spec. Let's describe them together."

3. **Given** the developer provides endpoint descriptions through chat, **when** the LLM processes the conversation, **then** `SataState` is populated with the extracted API model in the same structure as file/URL parsing, **and** the pipeline advances to Spec Review.

4. **Given** the developer provides ambiguous or incomplete descriptions, **when** the LLM detects missing required information, **then** it asks follow-up questions until sufficient detail is captured to generate test cases.

## Tasks / Subtasks

- [x] Task 1: Add a manual-ingestion entry point and shared chat UI in `app.py` (AC: 1, 2)
  - [x] Add an explicit "Describe my API manually" action in the existing `spec_ingestion` screen alongside file upload and URL import.
  - [x] Render the conversational UI with Streamlit chat primitives (`st.chat_message`, `st.chat_input`) rather than inventing a custom chat widget.
  - [x] Reuse the same chat UI for both manual entry and zero-endpoint fallback so there is one conversational path to maintain.
  - [x] Display the exact fallback copy from AC2 when a parsed spec yields zero endpoints.
  - [x] Keep the stage header and "Next required action" messaging explicit so the user always knows they are still in the ingestion/checkpoint flow.

- [x] Task 2: Implement the Story 1.5 conversational node in `app/pipeline.py` without renaming graph topology (AC: 1, 2, 3, 4)
  - [x] Replace the `fill_gaps` stub with real logic for manual API description and zero-endpoint fallback.
  - [x] Keep the node name `fill_gaps`; do not rename graph nodes or rewrite the graph structure just for this story.
  - [x] Update `_route_after_ingest` so `spec_source == "chat"` routes into `fill_gaps`.
  - [x] Update `_route_after_parse` so a successful parse with zero extracted endpoints routes into `fill_gaps`; non-empty models still route to `detect_gaps`.
  - [x] Keep malformed/non-OpenAPI parse failures on the existing parse-error path; only successful zero-endpoint parses should trigger fallback.

- [x] Task 3: Add a focused conversational-spec builder utility that returns the canonical `parsed_api_model` shape (AC: 3, 4)
  - [x] Add a small utility module under `app/utils/` to own prompt construction, LLM invocation, and response validation for manual API description.
  - [x] Use `langchain_openai.ChatOpenAI` with `LLM_API_KEY`, `LLM_CHAT_MODEL`, and `LLM_BASE_URL`; do not add a second LLM client stack.
  - [x] Require structured JSON output from the model so the result can be validated before writing to `state["parsed_api_model"]`.
  - [x] Validate that the generated model matches the same top-level shape already produced by `parse_openapi_spec`: `endpoints`, `auth`, `title`, `version`.
  - [x] Support two outcomes from each chat turn: `needs_more_info` with one concrete follow-up question, or `complete` with a valid canonical API model.

- [x] Task 4: Preserve current state and UI conventions instead of broad refactors (AC: 1, 2, 3, 4)
  - [x] Keep `SataState` as the source of truth for pipeline data; only add new fields if the node truly needs persisted conversation metadata across reruns.
  - [x] Prefer `st.session_state` keys for UI-only chat transcript or banner state rather than bloating `SataState` with presentation-only data.
  - [x] Continue the repo's current in-place state-mutation pattern in pipeline nodes; current tests assert same-object returns.
  - [x] On successful conversational extraction, populate `state["parsed_api_model"]`, clear stale `error_message`, and move into the same post-parse state already used by file/URL ingestion (`pipeline_stage = "spec_parsed"` for now).
  - [x] Do not implement Spec Review UI in this story; Story 2.x owns that screen.

- [x] Task 5: Add deterministic tests for routing, model-shape validation, and follow-up behavior (AC: 1, 2, 3, 4)
  - [x] Add unit tests for the new conversational utility with mocked LLM responses covering `complete`, `needs_more_info`, malformed JSON, and wrong-shape outputs.
  - [x] Add pipeline tests proving `_route_after_parse` sends zero-endpoint models to `fill_gaps` and non-empty models to `detect_gaps`.
  - [x] Add tests proving manual chat completion produces the same canonical model keys expected by downstream stories.
  - [x] Add tests proving parse failure does not silently become chat fallback.
  - [x] If `SataState` changes, update `tests/test_state.py` with safe defaults and explicit key expectations.

## Dev Notes

### Story Boundaries And Dependencies

- Story 1.5 covers two entry paths only:
  - manual API description chosen by the user
  - automatic fallback after a successful parse with zero extracted endpoints
- Do not implement generic gap detection for parsed specs here. Story 1.4 owns the normal parsed-spec gap-detection flow.
- AC4 follow-up questions apply within the conversational/manual path only.

### Previous Story Intelligence

- Story 1.2 established the canonical `parsed_api_model` contract. Story 1.5 must produce that exact shape so Story 2.x can treat file, URL, and chat ingestion identically.
- Story 1.3 kept a strict separation between fetch failures and parse failures. Preserve the same clarity here:
  - parse failure remains an error
  - zero-endpoint fallback is an intentional guided flow, not an error
  - manual mode is a deliberate user choice, not a recovery path
- Story 1.3 also standardized clearing stale `error_message` at the start of a new user action and using `st.rerun()` after state updates. Follow that pattern for chat submissions.

### Current Codebase Reality To Build On

- `app.py`
  - Already owns stage-driven ingestion rendering and directly invokes node functions from the UI.
  - Already supports file upload and URL import in the `spec_ingestion` / `spec_parsed` stages.
- `app/pipeline.py`
  - `fill_gaps` is still a stub and is the intended Story 1.5 implementation point.
  - `_route_after_ingest()` currently ignores `spec_source == "chat"` in practice because it always returns `"parse_spec"`; this story should fix that.
  - `_route_after_parse()` currently always returns `"detect_gaps"`; this story must add the zero-endpoint branch.
- `app/state.py`
  - `spec_source` already supports `"chat"`.
  - No conversation-history field exists yet.
- `app/utils/spec_parser.py`
  - Defines the canonical parsed model shape.
  - Returns zero endpoints when a spec has `paths: {}` or no supported operations.
  - Raises a `ValueError` when `paths` is missing entirely; do not convert that condition into fallback.
- `tests/test_pipeline.py`
  - Currently assumes `fill_gaps` is still a stub. Update the tests to match real Story 1.5 behavior.

### Canonical Output Contract

Manual conversational extraction must produce the same shape used by file and URL parsing:

```python
parsed_api_model = {
    "endpoints": [
        {
            "path": "/users",
            "method": "GET",
            "operation_id": "listUsers",
            "summary": "List users",
            "parameters": [],
            "request_body": None,
            "response_schemas": {"200": {"type": "object"}},
            "auth_required": False,
            "tags": [],
        }
    ],
    "auth": {
        "type": None,
        "scheme": None,
        "in": None,
        "name": None,
    },
    "title": "User API",
    "version": "unknown",
}
```

- Do not add extra top-level keys to `parsed_api_model`.
- Do not let free-form LLM output bypass validation.
- Downstream stories expect `method` uppercase and `response_schemas` keyed by status code strings.

### Recommended Implementation Shape

- Add one utility module such as `app/utils/conversational_spec_builder.py` with a small public API, for example:

```python
def extract_api_model_from_conversation(messages: list[dict]) -> dict:
    """Return {'status': 'needs_more_info', 'question': str} or {'status': 'complete', 'api_model': dict}."""
```

- Keep prompt design narrow and structured:
  - Ask the model to extract only API structure, not test cases.
  - Ask only for auth type/header names, never actual secrets or tokens.
  - Require JSON-only output.
- Validate model output locally before accepting it:
  - top-level keys present
  - endpoint list not empty for `complete`
  - each endpoint has `path`, `method`, `parameters`, `response_schemas`, `auth_required`, and `tags`
  - unsupported or missing values should trigger `needs_more_info`, not silent acceptance

### Architecture Compliance

- Stay within the existing Streamlit + LangGraph + `SataState` architecture.
- Do not introduce a new UI framework, background worker, database, or message bus.
- Do not add a second LLM SDK; the repo already depends on `langchain-openai`.
- Keep node-level resilience: LLM failures must surface helpful messages and must not crash the app.
- Keep the security boundary from the PRD and architecture docs:
  - load model settings from `.env`
  - do not log raw specs, tokens, or chat content unnecessarily
  - do not ask the user for real bearer tokens or API keys in the conversational builder

### UX Requirements

- The chat prompt must explicitly tell the user what information is needed: endpoint paths, HTTP methods, inputs, outputs, and auth style.
- Zero-endpoint fallback must be a dedicated warning/info state, not a generic parse error.
- The user should see one obvious next action at a time.
- Reuse one conversation transcript for the whole manual/fallback flow so follow-up questions feel continuous.
- Do not hide stage transitions. If the app is waiting for more detail, say so plainly.

### Library And Framework Requirements

- `streamlit`
  - Use the official chat primitives: `st.chat_message` and `st.chat_input`.
  - Preserve current Streamlit rerun/session-state patterns already used in `app.py`.
- `langchain-openai`
  - Use `ChatOpenAI` with `base_url`, `api_key`, and `model` from the existing environment variables.
  - Keep calls deterministic and easy to mock in tests.
- `langgraph`
  - Keep branching in `_route_after_ingest` and `_route_after_parse` via `add_conditional_edges`; do not hardcode graph divergence only in the UI.

### File Structure Requirements

- Modify:
  - `app.py`
  - `app/pipeline.py`
  - `tests/test_pipeline.py`
  - `tests/test_state.py` only if state fields change
- Add:
  - `app/utils/conversational_spec_builder.py`
  - `tests/test_conversational_spec_builder.py`
- Reuse as-is unless a targeted update is required:
  - `app/utils/spec_parser.py`
  - `app/utils/env.py`
  - `tests/test_parse_spec_node.py`

### Testing Requirements

- Keep all tests offline and deterministic; mock all LLM calls.
- Add explicit tests for these edge cases:
  - user chooses manual mode before any file/URL upload
  - parsed spec succeeds but yields zero endpoints
  - parsed spec fails and remains an error, not a fallback
  - LLM returns invalid JSON
  - LLM returns structurally invalid API data
  - LLM asks a follow-up question when method/path/response details are missing
- Preserve existing parser and URL-import behavior; Story 1.5 must not regress Stories 1.2 or 1.3.

### Latest Technical Information

- Official Streamlit docs currently position `st.chat_input` and `st.chat_message` as the supported chat UI primitives for app chat flows. Use them instead of custom text-area-based chat.
- Official LangChain docs for `ChatOpenAI` show support for custom `base_url` plus `api_key`, which matches this repo's `LLM_BASE_URL` pattern for an OpenAI-compatible endpoint.
- Official LangGraph docs continue to document conditional branching through `add_conditional_edges`, which fits the existing graph builder and should be used for the zero-endpoint fallback branch.

### Risks And Guardrails

- Regression risk: changing `parse_openapi_spec()` to force fallback on malformed specs would break Story 1.2/1.3 error handling.
- Contract risk: if conversational extraction returns a different schema than parser-based ingestion, Story 2.x will break.
- Scope risk: do not build generic checkpoint/review UI here.
- UX risk: if fallback, parse error, and manual mode all look the same, the user will not know what happened.
- Testing risk: current pipeline tests assume stubbed `fill_gaps`; they must be updated with the new behavior.

### References

- Story requirements and epic context: `_bmad-output/planning-artifacts/epics.md`
- Functional requirements and NFRs: `_bmad-output/planning-artifacts/prd.md`
- Architecture constraints: `_bmad-output/planning-artifacts/architecture.md`
- UX guidance for stage clarity and fallback states: `_bmad-output/planning-artifacts/ux-design-specification.md`
- Existing ingestion UI: `app.py`
- Existing state contract: `app/state.py`
- Existing graph topology and routing hooks: `app/pipeline.py`
- Canonical parser contract: `app/utils/spec_parser.py`
- Previous story learnings: `_bmad-output/implementation-artifacts/1-2-openapi-swagger-file-upload-and-parsing.md`
- Previous story learnings and review findings: `_bmad-output/implementation-artifacts/1-3-api-spec-url-import.md`
- Official Streamlit chat API docs: `https://docs.streamlit.io/develop/api-reference/chat/st.chat_input`, `https://docs.streamlit.io/develop/api-reference/chat/st.chat_message`
- Official LangChain `ChatOpenAI` docs: `https://docs.langchain.com/oss/python/integrations/chat/openai`
- Official LangGraph graph API docs: `https://docs.langchain.com/oss/python/langgraph/use-graph-api`

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Loaded BMAD config and Story 1.5 context from `_bmad/bmm/config.yaml` and this story file
- Implemented conversational extraction in `app/utils/conversational_spec_builder.py`
- Updated `app/pipeline.py`, `app.py`, and `app/state.py` for manual chat mode and zero-endpoint fallback
- Added/updated deterministic tests in `tests/test_conversational_spec_builder.py`, `tests/test_pipeline.py`, and `tests/test_state.py`
- Added `app/utils/spec_review.py`, `app/utils/pipeline_visualization.py`, and hardened `review_spec()` plus pipeline visualization exports to restore the checked-in regression suite baseline
- `pytest -q tests/test_conversational_spec_builder.py tests/test_pipeline.py tests/test_state.py` -> 26 passed
- `pytest -q tests/test_state.py tests/test_pipeline.py tests/test_pipeline_visualization.py` -> 32 passed
- `pytest -q` -> 167 passed

### Completion Notes List

- Implemented a manual "Describe my API manually" entry point and a shared Streamlit chat flow for both manual and zero-endpoint fallback ingestion
- Added an LLM-backed conversational spec builder that returns either one follow-up question or a validated canonical `parsed_api_model`
- Updated pipeline routing so chat mode enters `fill_gaps` directly and successful zero-endpoint parses switch into conversational fallback instead of generic gap detection
- Added persisted conversation metadata to `SataState` and kept UI-only banner/history handling in `st.session_state`
- Expanded automated coverage for conversational extraction, routing behavior, and state defaults
- Restored full-suite compatibility by adding the missing deterministic spec-review and pipeline-visualization helpers and tightening `review_spec()` plus pipeline metadata guardrails

### File List

- `_bmad-output/implementation-artifacts/1-5-conversational-api-description-and-zero-endpoint-fallback.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `app.py`
- `app/pipeline.py`
- `app/state.py`
- `app/utils/conversational_spec_builder.py`
- `app/utils/pipeline_visualization.py`
- `app/utils/spec_review.py`
- `tests/test_conversational_spec_builder.py`
- `tests/test_pipeline.py`
- `tests/test_state.py`

## Change Log

- 2026-03-31: Implemented Story 1.5 conversational ingestion and zero-endpoint fallback, added deterministic tests, and restored full regression-suite compatibility.
