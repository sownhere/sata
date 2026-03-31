# Deferred Work

## Deferred from: code review of 1-3-api-spec-url-import (2026-03-31)

- Concurrent double-click on "Fetch" button submits two simultaneous requests — pre-existing Streamlit single-threaded architecture; no state lock in place; low impact in practice
- Slow-loris / total read time unbounded — per-recv socket timeout does not bound cumulative transfer time; partially mitigated by the response size cap patch (reading stops at MAX_BYTES regardless of rate)



## Deferred from: code review of 1-2-openapi-swagger-file-upload-and-parsing (2026-03-31)

- `_route_after_parse` stub unconditionally returns `detect_gaps`, never routes to `fill_gaps` on zero endpoints (`app/pipeline.py:99-101`) — Story 1.5 scope
- Stub routers create infinite loop (`analyze_results → review_results → analyze_results`) (`app/pipeline.py:119-121`) — pre-existing stubs, not story 1.2 scope; all routers need real implementations as their stories are implemented
- Explicit `security: []` per-operation opt-out loses semantic distinction from "no security declared" (`app/utils/spec_parser.py:85`) — Story 1.4 gap-detection needs to distinguish explicitly-public endpoints from undeclared-security endpoints
- `auth_required: True` with `auth.type: None` contradiction when `securitySchemes` is absent but `security` field references a scheme — `auth.type` being None gives no actionable auth info to test execution; Story 4.1 scope
