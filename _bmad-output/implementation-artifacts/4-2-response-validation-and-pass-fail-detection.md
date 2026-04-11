# Story 4.2: Response Validation & Pass/Fail Detection

Status: review

## Story

As a developer,
I want each test case's response to be automatically validated against the expected status code and response schema,
So that I get precise pass/fail results rather than just raw HTTP responses.

## Acceptance Criteria

1. **Given** an HTTP response is received for a test case **when** validation runs **then** the actual status code is compared to the expected status code in `test_case["expected"]["status_code"]`.

2. **Given** the actual status code and response body both match expectations **when** validation completes **then** the test result has `passed: True` and `validation_errors: []`.

3. **Given** the actual status code differs from expected **when** validation completes **then** the test result has `passed: False` and `validation_errors` contains an entry describing the mismatch (e.g., `"Expected status 200, got 404"`).

4. **Given** the API returns a valid response with unexpected extra fields **when** validation runs **then** the test passes — non-strict schema matching (extra fields allowed).

5. **Given** the API returns an empty body for a test case that expects one **when** validation runs **then** the result has `passed: False` and `validation_errors` contains `"Empty response body — expected schema not satisfied"`.

6. **Given** no expected status code is defined in `test_case["expected"]` **when** validation runs **then** the test passes if the status code is in 200–299 range, otherwise fails with `"No expected status code defined; actual {code} is not 2xx"`.

## Tasks / Subtasks

- [x] Task 1: Create `src/tools/response_validator.py` (AC: 1–6)
  - [ ] Add `validate_response(test_case: dict, result: dict, parsed_api_model: dict | None) -> dict` that takes a test case and an existing result dict from Story 4-1, and returns the same dict with `passed`, `expected_status_code`, and `validation_errors` added.
  - [ ] Logic:
    - Extract `expected_status_code = test_case.get("expected", {}).get("status_code")`.
    - If `actual_status_code` is `None` (network error): `passed = False`, `validation_errors = [result.get("error_message") or "Network error"]`.
    - Status code check: if `expected_status_code` is set, compare; otherwise check 2xx range.
    - Response body schema check: if `parsed_api_model` is set, look up `endpoint.response_schemas.get(str(expected_status_code or actual_status_code))` for the matching endpoint+method. If schema is a dict with a `"properties"` key, check that all `required` keys (if listed) are present in the actual body dict. Extra fields are allowed (non-strict).
    - If body is `None` or empty string but schema is non-trivial (has required fields): `passed = False`, `validation_errors += ["Empty response body — expected schema not satisfied"]`.
    - Combine status + schema results: `passed = status_passed and schema_passed`.
    - Always set `result["expected_status_code"] = expected_status_code`.
    - Always set `result["passed"] = passed`.
    - Always set `result["validation_errors"] = validation_errors` (list of strings, empty if passed).
    - Return the mutated result dict.
  - [ ] Add unit tests in `tests/unit/test_response_validator.py`:
    - `test_validate_response_status_match_passes`
    - `test_validate_response_status_mismatch_fails`
    - `test_validate_response_no_expected_status_2xx_passes`
    - `test_validate_response_no_expected_status_non_2xx_fails`
    - `test_validate_response_extra_fields_are_allowed`
    - `test_validate_response_missing_required_field_fails`
    - `test_validate_response_empty_body_when_schema_expected_fails`
    - `test_validate_response_network_error_fails`

- [x] Task 2: Integrate validation into `execute_tests` node (AC: 1–6)
  - [ ] In `src/nodes/execute_tests.py`, after calling `execute_single_test`, immediately call `validate_response(test_case, result, state.get("parsed_api_model"))` to enrich each result.
  - [ ] Import: `from src.tools.response_validator import validate_response`.
  - [ ] No changes to the `execute_tests` function signature or return shape — results in `state["test_results"]` now include `passed`, `expected_status_code`, `validation_errors`.
  - [ ] Update `tests/integration/test_pipeline.py`:
    - Update `test_execute_tests_populates_test_results` — add `passed` and `validation_errors` to the `fake_result` dict returned by the mock (so the test reflects real shape).
    - Add `test_execute_tests_results_have_passed_field` — stub with real mock that returns a result where `actual_status_code=200` and `expected={"status_code": 200}`, assert `result["test_results"][0]["passed"] is True`.

- [x] Task 3: Update `execute_tests` UI results display in `app.py` (AC: 2, 3)
  - [ ] In the `elif current_stage == "execute_tests":` block, when `state.get("test_results") is not None`:
    - Replace the current simple dataframe with one that includes a `passed` column.
    - Compute summary: `pass_count = sum(1 for r in results if r.get("passed"))`, `fail_count = len(results) - pass_count`.
    - Show `st.success` or `st.error` depending on overall pass rate.
    - Columns in dataframe: `passed`, `test_id`, `endpoint_method`, `endpoint_path`, `actual_status_code`, `expected_status_code`, `error_message`.
    - For failed tests: show a `st.expander` for `validation_errors` so developer can drill in.

## Dev Notes

### Previous Story Handoff (Story 4.1)

After Story 4-1:
- `state["test_results"]` is a list of dicts with: `test_id`, `test_title`, `endpoint_method`, `endpoint_path`, `actual_status_code`, `actual_response_body`, `error_message`, `attempt_count`.
- Story 4-1 dev note: "Story 4.2 extends this with: `expected_status_code`, `passed`, `validation_errors`."

### response_validator Contract

`validate_response` mutates and returns the result dict in-place:

```python
# Input: result dict from execute_single_test
{
    "test_id": "tc-1",
    "actual_status_code": 200,
    "actual_response_body": {"users": [...]},
    "error_message": None,
    "attempt_count": 1,
    ...
}

# Output: same dict extended
{
    ...,
    "expected_status_code": 200,      # from test_case["expected"]["status_code"]
    "passed": True,
    "validation_errors": [],
}
```

### TestCaseModel.expected Format

LLM generates `expected` as a dict with at minimum `status_code`:
```python
{"status_code": 200}
```
It may also contain a `"response_schema"` key in future but Story 4.2 only uses `status_code` and the `parsed_api_model["endpoints"]` schema lookup.

### Response Schema Lookup

To find the expected schema for a test case:
```python
endpoint_schemas = {}
for ep in (parsed_api_model or {}).get("endpoints") or []:
    if ep.get("path") == test_case["endpoint_path"] and ep.get("method") == test_case["endpoint_method"]:
        endpoint_schemas = ep.get("response_schemas") or {}
        break

schema_key = str(expected_status_code or actual_status_code or "")
schema = endpoint_schemas.get(schema_key)
```

Schema values in `response_schemas` can be:
- A string (description) → no structural check possible, skip validation
- A dict with `"properties"` key → validate required fields
- None or missing → no structural check

Required fields check (non-strict):
```python
if isinstance(schema, dict) and "properties" in schema:
    required = schema.get("required") or []
    actual_keys = set((actual_body or {}).keys()) if isinstance(actual_body, dict) else set()
    for req_field in required:
        if req_field not in actual_keys:
            validation_errors.append(f"Missing required field: '{req_field}'")
```

### Architecture Compliance

- `src/tools/response_validator.py` → may import from `src.core` only. No imports from `src.nodes` or `src.ui`.
- No LLM calls in this story — fully deterministic validation.
- No credential display — `validate_response` never touches auth headers.

### Project Structure Notes

**Add:**
- `src/tools/response_validator.py`
- `tests/unit/test_response_validator.py`

**Modify:**
- `src/nodes/execute_tests.py` — integrate `validate_response` call
- `app.py` — update execute_tests UI display (pass/fail columns, pass rate)
- `tests/integration/test_pipeline.py` — update/add tests
- `_bmad-output/implementation-artifacts/4-2-...md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Do NOT modify:**
- `src/core/models.py` — no model changes needed
- `src/tools/http_executor.py` — validation is separate from execution
- `src/core/state.py` — no new state fields needed; `test_results` entries are extended in-place

### Testing Requirements

- All tests deterministic and offline — no network calls.
- Keep all 215 existing tests passing.
- `test_response_validator.py` uses plain dicts, no mocking needed.

### Risks & Guardrails

- **Do NOT add** `analyze_results`, failure pattern detection, or LLM explanations — those are Story 4.3.
- **Do NOT modify** `test_results` dict keys from Story 4-1 — only ADD `passed`, `expected_status_code`, `validation_errors`.
- **Tolerate missing `expected`** — if `test_case["expected"]` is empty or absent, default to 2xx check.
- **Schema validation is non-strict** — extra fields in response never cause failure.
- **String schemas** (like `"Returns the user object"`) should be treated as no schema → skip body validation.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Ruff E501 on long f-string in app.py expander loop — split to intermediate variable.

### Completion Notes List

- 227 tests passing (up from 215).
- `validate_response` mutates result dict in-place and returns it.
- Non-strict: extra fields in body never fail; only missing `required` fields fail.
- String schemas (narrative descriptions from gap fill) are skipped for body validation.
- UI now shows pass/fail counts, colour-coded header, enriched dataframe with `expected_status_code`, and expandable validation error details.

### File List

- `src/tools/response_validator.py`
- `src/nodes/execute_tests.py`
- `app.py`
- `tests/unit/test_response_validator.py`
- `tests/integration/test_pipeline.py`
- `_bmad-output/implementation-artifacts/4-2-response-validation-and-pass-fail-detection.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log
