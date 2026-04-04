# Deferred Work

## Deferred from: code review of 1-3-api-spec-url-import (2026-03-31)

- Concurrent double-click on "Fetch" button submits two simultaneous requests — pre-existing Streamlit single-threaded architecture; no state lock in place; low impact in practice
- Slow-loris / total read time unbounded — per-recv socket timeout does not bound cumulative transfer time; partially mitigated by the response size cap patch (reading stops at MAX_BYTES regardless of rate)



## Deferred from: code review of 1-2-openapi-swagger-file-upload-and-parsing (2026-03-31)

- `_route_after_parse` stub unconditionally returns `detect_gaps`, never routes to `fill_gaps` on zero endpoints (`app/pipeline.py:99-101`) — Story 1.5 scope
- Stub routers create infinite loop (`analyze_results → review_results → analyze_results`) (`app/pipeline.py:119-121`) — pre-existing stubs, not story 1.2 scope; all routers need real implementations as their stories are implemented
- Explicit `security: []` per-operation opt-out loses semantic distinction from "no security declared" (`app/utils/spec_parser.py:85`) — Story 1.4 gap-detection needs to distinguish explicitly-public endpoints from undeclared-security endpoints
- `auth_required: True` with `auth.type: None` contradiction when `securitySchemes` is absent but `security` field references a scheme — `auth.type` being None gives no actionable auth info to test execution; Story 4.1 scope

## Deferred from: code review of Epic 7 (2026-04-03)

- `AuthModel.model_dump()` emits `location` not `"in"` without `by_alias=True` — trap for future serialization callers [`src/core/models.py`]
- `Settings` post-construction mutation relies on Pydantic v2 default mutability — undocumented contract [`src/core/config.py:100–111`]
- Story specs for 7.1–7.7 not updated to reflect multi-story scope merge on single branch — documentation debt
- `iteration_count` (NFR5) never read/incremented in routing functions — pre-existing from `app/pipeline.py` [`src/core/graph.py`]
- Private `_*` re-exports in `app/pipeline.py` shim serve no current consumer — dead surface area
- `_auth_state_from_answer("none")` handled via default fallthrough — works correctly but opaque intent [`src/nodes/fill_gaps.py:128–139`]
- Placeholder prompt files return HTML comment as real content when loaded by LLM [`src/prompts/test_generation.md`, `gap_filling.md`, `result_analysis.md`]
- `app/utils/env.py` shim has no test exercising the shim re-export path
- `execution.request_timeout_seconds` not directly asserted in any test [`tests/unit/test_core_settings.py`]
- Six orchestration helpers in `app.py` (`_conversation_mode_active` et al.) — defer extraction to `src/ui/` in a future story
