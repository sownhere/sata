# Story 4.3: Failure Analysis & Developer-Friendly Explanations

Status: review

## Story

As a developer,
I want each test failure to be analyzed for defect patterns and presented with a plain-language explanation of what broke, why it matters, and how to fix it,
So that I can act on results immediately without interpreting raw request/response diffs myself.

## Acceptance Criteria

1. **Given** test execution is complete and failures exist **when** the `analyze_results` node runs **then** failures are grouped by defect type and severity (e.g., "3× Missing Required Field — High").

2. **Given** a test case has failed **when** the analysis node processes it **then** a developer-friendly explanation is generated containing: what broke, why it matters, and a concrete suggestion for how to fix it; stored in `state["failure_analysis"]`.

3. **Given** multiple failures share the same root cause pattern (e.g., auth fails on all POST endpoints) **when** pattern analysis runs **then** the pattern is surfaced as a single grouped finding rather than N identical explanations.

4. **Given** a failure analysis explanation is generated **when** it is stored **then** no auth tokens, API keys, or sensitive request data are included in the explanation text.

5. **Given** all tests passed (no failures) **when** the analysis node runs **then** `state["failure_analysis"]` is set to `{"patterns": [], "explanations": [], "all_passed": True}` and `pipeline_stage` advances to `"review_results"`.

6. **Given** test execution has not yet run (no `test_results` in state) **when** the analysis node runs **then** it sets `error_message` and returns without modifying `failure_analysis`.

## Tasks / Subtasks

- [x] Task 1: Write the `result_analysis.md` prompt and create `src/tools/failure_analyzer.py` (AC: 1–4)
  - [x] Replace placeholder content in `src/prompts/result_analysis.md` with a structured prompt that:
    - Takes a list of failed test cases (id, title, method, path, expected_status, actual_status, validation_errors) as JSON
    - Returns JSON with `{"patterns": [...], "explanations": [...]}` where:
      - `patterns`: list of `{"pattern_type": str, "severity": "High"|"Medium"|"Low", "count": int, "description": str, "affected_test_ids": [str]}`
      - `explanations`: list of `{"test_id": str, "what_broke": str, "why_it_matters": str, "how_to_fix": str}`
    - Instructs the LLM to group similar failures and never include tokens, keys, or credential values.
  - [x] Create `src/tools/failure_analyzer.py` with `analyze_failures(failed_results: list[dict], llm=None) -> dict`:
    - If `failed_results` is empty, return `{"patterns": [], "explanations": [], "all_passed": True}`.
    - Build a JSON summary of failures (only safe fields: test_id, title, endpoint_method, endpoint_path, expected_status_code, actual_status_code, validation_errors — never actual_response_body or request headers).
    - Load prompt from `src/prompts/result_analysis.md` (strip the `# Result Analysis Prompt` header line).
    - Call the LLM (same `_build_llm()` pattern as `test_case_generator.py`): `ChatOpenAI(api_key=..., model=..., base_url=..., temperature=0)`.
    - Parse LLM JSON response; if parsing fails, return `{"patterns": [], "explanations": [], "parse_error": str(exc)}`.
    - Add `"all_passed": False` to the returned dict.
  - [x] Add unit tests in `tests/unit/test_failure_analyzer.py` (mock the LLM):
    - `test_analyze_failures_empty_returns_all_passed`
    - `test_analyze_failures_calls_llm_with_safe_fields_only`
    - `test_analyze_failures_returns_parsed_patterns_and_explanations`
    - `test_analyze_failures_handles_llm_parse_error_gracefully`

- [x] Task 2: Implement `analyze_results` node (AC: 1–6)
  - [x] Replace the stub in `src/nodes/analyze_results.py` with:
    - Guard: if `state.get("test_results") is None` → set `error_message = "No test results to analyze."`, set `pipeline_stage = "execute_tests"`, return.
    - Compute `failed_results = [r for r in state["test_results"] if not r.get("passed")]`.
    - Call `analyze_failures(failed_results)` from `src.tools.failure_analyzer`.
    - Set `state["failure_analysis"] = analysis_result`.
    - Set `state["pipeline_stage"] = "review_results"`.
    - Clear `state["error_message"] = None`.
  - [x] Import: `from src.tools.failure_analyzer import analyze_failures`.
  - [x] Add integration tests in `tests/integration/test_pipeline.py`:
    - `test_analyze_results_requires_test_results` — state without `test_results` → error_message set, stage stays `execute_tests`.
    - `test_analyze_results_populates_failure_analysis` — mock `analyze_failures`; assert `state["failure_analysis"]` set and `pipeline_stage == "review_results"`.
    - `test_analyze_results_all_passed_sets_flag` — mock returns `all_passed: True`; assert flag propagated.

- [x] Task 3: Update the `review_results` UI stage in `app.py` (AC: 1, 2, 3, 5)
  - [x] The current `review_results` stage likely has a stub. Locate the `elif current_stage == "review_results":` block (or add it after `execute_tests`) and replace/add:
    - If `failure_analysis.get("all_passed")`: show `st.success("All tests passed!")` with a celebration message.
    - Otherwise: show pattern groups using `st.metric` for count, expandable per-failure explanations with `what_broke`, `why_it_matters`, `how_to_fix`.
    - Never render `actual_response_body` raw — just reference it via test_id.
    - Show a "New Test Run" button that resets `test_results`, `failure_analysis`, `target_api_url` in state and reruns back to `execute_tests`.

## Dev Notes

### Previous Story Handoff (Story 4.2)

After Story 4-2, `state["test_results"]` contains enriched results with:
- `passed` (bool), `expected_status_code`, `validation_errors` — added by `validate_response`
- `actual_status_code`, `actual_response_body`, `error_message`, `attempt_count` — from Story 4-1

`state["failure_analysis"]` is `None` (set in `SataState` initial_state).

### LLM Pattern (Match Existing Tools)

Use the same `_build_llm()` pattern from `src/tools/test_case_generator.py`:

```python
def _build_llm():
    from langchain_openai import ChatOpenAI
    settings = get_settings()
    return ChatOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_CHAT_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
    )
```

The `llm` parameter (default None) allows injection in tests.

### Safe Fields for LLM Input

NEVER send to LLM:
- `actual_response_body` (may contain user data)
- Request headers (may contain auth tokens)
- `error_message` raw strings from network errors (may contain URLs)

SAFE to send:
- `test_id`, `test_title` (generated by Sata, not user data)
- `endpoint_method`, `endpoint_path` (from spec)
- `expected_status_code`, `actual_status_code`
- `validation_errors` list (generated by Sata's validator)

### failure_analysis State Contract

```python
state["failure_analysis"] = {
    "patterns": [
        {
            "pattern_type": "auth_failure",
            "severity": "High",
            "count": 3,
            "description": "All POST endpoints fail with 401...",
            "affected_test_ids": ["tc-1", "tc-2", "tc-3"],
        }
    ],
    "explanations": [
        {
            "test_id": "tc-1",
            "what_broke": "POST /users returned 401 Unauthorized",
            "why_it_matters": "Auth check is rejecting valid requests",
            "how_to_fix": "Verify Bearer token in API_BEARER_TOKEN is valid",
        }
    ],
    "all_passed": False,      # True when no failures
    # Optional:
    "parse_error": "...",     # Present only on LLM JSON parse failure
}
```

### Pipeline Stage Advance

Story 4-3 is the first story to advance `pipeline_stage` to `"review_results"`. After this, the `review_results` node will handle the final checkpoint.

### review_results node

`src/nodes/review_results.py` is a stub. Story 4-3 ONLY updates the **UI** for `review_results` in `app.py` — do NOT replace the node stub (that's for a future story).

### Architecture Compliance

- `src/tools/failure_analyzer.py` → may import from `src.core` and call LLM. No imports from `src.nodes` or `src.ui`.
- No credential values in LLM prompts or responses — never pass auth_headers to failure_analyzer.
- `failure_analyzer.py` follows the same `_build_llm()` deferred import pattern as other tools.

### Project Structure Notes

**Add:**
- `src/tools/failure_analyzer.py`
- `tests/unit/test_failure_analyzer.py`

**Modify:**
- `src/prompts/result_analysis.md` — replace placeholder with real prompt
- `src/nodes/analyze_results.py` — replace stub with real logic
- `app.py` — add/update `review_results` UI block
- `tests/integration/test_pipeline.py` — 3 new tests
- `_bmad-output/implementation-artifacts/4-3-...md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Do NOT modify:**
- `src/nodes/review_results.py` — stub stays as-is for now
- `src/core/state.py` — `failure_analysis: Optional[dict]` already exists
- `src/tools/http_executor.py`, `src/tools/response_validator.py`

### Testing Requirements

- `test_failure_analyzer.py` must mock `langchain_openai.ChatOpenAI` — no real LLM calls.
- `test_pipeline.py` integration tests must mock `analyze_failures`.
- Keep all 227 existing tests passing.

### Risks & Guardrails

- **Do NOT** implement the results dashboard (Story 5.1), drill-down view (Story 5.2), or report generation (Story 5.3) — those are separate epics.
- **Do NOT** implement all-pass/all-fail smart diagnosis — that is Story 4.4.
- **LLM parse failure is non-fatal** — return graceful fallback with `parse_error` key.
- **`actual_response_body` stays in state** but is never sent to the LLM.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Re-validated Story 4.3 behavior against the expanded results flow; 258 tests pass in the current regression run.
- `analyze_failures` sends only 7 safe fields to LLM — never response body, headers, or credentials.
- LLM JSON parse failures are non-fatal: `parse_error` key set, empty patterns/explanations returned.
- `review_results` UI shows severity-coloured pattern groups, per-failure expanders, and a "New Test Run" reset button.
- `analyze_results` node advances `pipeline_stage` to `"review_results"` — first node to do so.

### File List

- `src/prompts/result_analysis.md`
- `src/tools/failure_analyzer.py`
- `src/nodes/analyze_results.py`
- `app.py`
- `tests/unit/test_failure_analyzer.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/4-3-failure-analysis-and-developer-friendly-explanations.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-11: Re-validated Story 4.3 completion, checked remaining subtasks, and kept the story in `review`.
