"""Unit tests for src.tools.response_validator — deterministic, no network calls."""

from src.tools.response_validator import validate_response


def _make_result(status_code, body=None, error=None):
    return {
        "test_id": "tc-1",
        "test_title": "Test",
        "endpoint_method": "GET",
        "endpoint_path": "/users",
        "actual_status_code": status_code,
        "actual_response_body": body,
        "error_message": error,
        "attempt_count": 1,
    }


def _make_test_case(expected_status=None, path="/users", method="GET"):
    tc = {
        "id": "tc-1",
        "title": "Test",
        "endpoint_path": path,
        "endpoint_method": method,
        "expected": {},
    }
    if expected_status is not None:
        tc["expected"]["status_code"] = expected_status
    return tc


# ── Status code checks ────────────────────────────────────────────────────────


def test_validate_response_status_match_passes():
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, {"users": []})
    out = validate_response(tc, result, None)
    assert out["passed"] is True
    assert out["expected_status_code"] == 200
    assert out["validation_errors"] == []


def test_validate_response_status_mismatch_fails():
    tc = _make_test_case(expected_status=200)
    result = _make_result(404)
    out = validate_response(tc, result, None)
    assert out["passed"] is False
    assert out["expected_status_code"] == 200
    assert any("404" in e for e in out["validation_errors"])
    assert any("200" in e for e in out["validation_errors"])


def test_validate_response_no_expected_status_2xx_passes():
    tc = _make_test_case()  # no expected status
    result = _make_result(201, {"id": "x"})
    out = validate_response(tc, result, None)
    assert out["passed"] is True
    assert out["expected_status_code"] is None


def test_validate_response_no_expected_status_non_2xx_fails():
    tc = _make_test_case()
    result = _make_result(500)
    out = validate_response(tc, result, None)
    assert out["passed"] is False
    assert any("500" in e for e in out["validation_errors"])


# ── Network error ─────────────────────────────────────────────────────────────


def test_validate_response_network_error_fails():
    tc = _make_test_case(expected_status=200)
    result = _make_result(None, error="connection refused")
    out = validate_response(tc, result, None)
    assert out["passed"] is False
    assert any("connection" in e.lower() for e in out["validation_errors"])


# ── Schema validation ─────────────────────────────────────────────────────────

_MODEL_WITH_SCHEMA = {
    "endpoints": [
        {
            "path": "/users",
            "method": "GET",
            "response_schemas": {
                "200": {
                    "properties": {"id": {}, "name": {}},
                    "required": ["id", "name"],
                }
            },
        }
    ]
}

_MODEL_STRING_SCHEMA = {
    "endpoints": [
        {
            "path": "/users",
            "method": "GET",
            "response_schemas": {"200": "Returns a user object."},
        }
    ]
}


def test_validate_response_extra_fields_are_allowed():
    """Non-strict: extra fields in response do not fail the test."""
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, {"id": "1", "name": "Alice", "extra": "ignored"})
    out = validate_response(tc, result, _MODEL_WITH_SCHEMA)
    assert out["passed"] is True
    assert out["validation_errors"] == []


def test_validate_response_missing_required_field_fails():
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, {"id": "1"})  # missing "name"
    out = validate_response(tc, result, _MODEL_WITH_SCHEMA)
    assert out["passed"] is False
    assert any("name" in e for e in out["validation_errors"])


def test_validate_response_empty_body_when_schema_expected_fails():
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, None)
    out = validate_response(tc, result, _MODEL_WITH_SCHEMA)
    assert out["passed"] is False
    assert any("Empty response body" in e for e in out["validation_errors"])


def test_validate_response_string_schema_skips_body_validation():
    """String schemas can't be structurally validated — body check is skipped."""
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, "plain text response")
    out = validate_response(tc, result, _MODEL_STRING_SCHEMA)
    assert out["passed"] is True
    assert out["validation_errors"] == []


def test_validate_response_no_schema_in_model_passes_on_status_match():
    model = {"endpoints": [{"path": "/users", "method": "GET", "response_schemas": {}}]}
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, None)
    out = validate_response(tc, result, model)
    assert out["passed"] is True


def test_validate_response_returns_same_dict():
    """validate_response should return the mutated result dict (same object)."""
    tc = _make_test_case(expected_status=200)
    result = _make_result(200, {})
    out = validate_response(tc, result, None)
    assert out is result
