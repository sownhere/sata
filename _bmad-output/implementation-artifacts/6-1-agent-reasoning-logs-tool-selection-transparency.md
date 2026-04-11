# Story 6.1: Agent Reasoning Logs - Tool Selection Transparency

Status: review

## Story

As a developer,
I want to view the agent reasoning logs showing which tools were selected and why at each pipeline step,
so that I can understand and trust the agent's decision-making and debug unexpected behavior.

## Acceptance Criteria

1. **Given** at least one pipeline stage has executed **when** reasoning logs are opened **then** each tool call entry shows tool name, stated reason, and sanitized input summary.

2. **Given** any log entry contains auth tokens or API-key-like values **when** rendered **then** all sensitive values are redacted and never shown in full.

3. **Given** multiple stages executed **when** full logs are viewed **then** entries are grouped by pipeline stage in chronological order.

4. **Given** the model emits reasoning with no tool call **when** recorded **then** it is represented as a reasoning event distinct from a tool-call event.

## Tasks / Subtasks

- [x] Task 1: Define observability log schema in shared state (AC: 1-4)
  - [x] Add a serializable `reasoning_log` structure to `SataState` with event types:
    - `tool_call`
    - `reasoning`
    - optional `system_event`
  - [x] Include stage key, timestamp/order index, and sanitized payload fields.

- [x] Task 2: Instrument tool invocation and reasoning capture paths (AC: 1, 3, 4)
  - [x] Capture logs where LLM/tool decisions are made (nodes/tools orchestration path).
  - [x] Ensure instrumentation works for both graph-driven and UI-triggered execution paths.
  - [x] Keep event ordering deterministic for replay in UI.

- [x] Task 3: Add redaction layer for logs (AC: 2)
  - [x] Implement shared sanitizer for secrets/tokens/keys and sensitive header fields.
  - [x] Apply sanitizer before writing to state and before rendering as defense in depth.

- [x] Task 4: Build reasoning-log UI panel (AC: 1-4)
  - [x] Add developer-facing log panel (tab/expander) in `app.py` or `src/ui/components.py`.
  - [x] Render by stage groups with per-event details and clear event-type badges.
  - [x] Add empty-state messaging when no events are available yet.

- [x] Task 5: Add test coverage for instrumentation and redaction (AC: 1-4)
  - [x] Unit tests for sanitizer and event formatter.
  - [x] Integration tests ensuring stage grouping and event ordering.
  - [x] Regression tests proving reasoning-only events are preserved.

## Dev Notes

### Previous Story Intelligence (from 6.2)

- Story 6.2 introduced execution observability fields (`active_node`, `completed_nodes`, `taken_edges`) and visualization patterns.
- Reuse those patterns for grouping context; do not create conflicting parallel tracking structures.

### Architecture Guardrails

- Reasoning logs must never store raw secrets, auth headers, or full credential values.
- Keep log formatting utilities deterministic and testable under `src/ui`/`src/tools`.
- Preserve node/tool/core dependency direction.

### File Structure Requirements

**Likely modify/add:**
- `src/core/state.py`
- `app.py`
- `src/ui/components.py` (or a new `src/ui/reasoning_logs.py`)
- `src/nodes/*` and/or orchestration layer where tool calls are made
- `tests/unit/test_state.py`
- `tests/integration/test_pipeline.py`

### Testing Requirements

- Verify tool-call entries include tool name, reason, and sanitized input summary.
- Verify stage grouping and chronological ordering.
- Verify reasoning-only events are rendered as distinct type.
- Verify no secret material appears in stored/rendered log entries.

### References

- Story source: `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.1)
- Requirements: `_bmad-output/planning-artifacts/prd.md` (FR37, FR31, FR32, NFR8)
- Related implementation context: `_bmad-output/implementation-artifacts/6-2-langgraph-pipeline-visualization.md`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5)

### Debug Log References

### Completion Notes List

- Added `reasoning_log` to `SataState` plus `src/core/observability.py` to append ordered, sanitized reasoning/tool-call events.
- Instrumented parse, test-generation, execution, and analysis paths so logs capture both reasoning-only and tool-call events from the main pipeline.
- Reused the shared redaction layer before storing and rendering log payloads.
- Added a developer reasoning-log expander in `src/ui/components.py` grouped by stage with empty-state handling.

### File List

- `src/core/state.py`
- `src/core/observability.py`
- `src/tools/redaction.py`
- `src/nodes/parse_spec.py`
- `src/nodes/generate_tests.py`
- `src/nodes/execute_tests.py`
- `src/nodes/analyze_results.py`
- `src/ui/components.py`
- `app.py`
- `tests/unit/test_reasoning_logs.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/6-1-agent-reasoning-logs-tool-selection-transparency.md`

### Change Log

- 2026-04-11: Implemented reasoning logs, stage grouping, and redaction; story moved to `review`.
