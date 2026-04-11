"""Deterministic response validation for test case pass/fail detection.

Canonical location: src.tools.response_validator
Non-strict schema matching: extra fields in response are always allowed.
No LLM calls, no network I/O.
"""

from typing import Optional


def validate_response(
    test_case: dict,
    result: dict,
    parsed_api_model: Optional[dict],
) -> dict:
    """Validate an HTTP result against the test case's expected values.

    Mutates and returns the result dict, adding:
    - ``passed`` (bool)
    - ``expected_status_code`` (int | None)
    - ``validation_errors`` (list[str])

    Args:
        test_case: Test case dict with at minimum ``expected`` and
                   ``endpoint_path`` / ``endpoint_method`` keys.
        result: Result dict from ``execute_single_test``. Mutated in place.
        parsed_api_model: The parsed API model from state, used for schema
                          lookup. May be None.

    Returns:
        The same result dict with validation fields added.
    """
    expected = test_case.get("expected") or {}
    expected_status_code = expected.get("status_code")
    actual_status_code = result.get("actual_status_code")
    actual_body = result.get("actual_response_body")
    network_error = result.get("error_message")

    validation_errors: list = []

    # ── Network error short-circuit ───────────────────────────────────────
    if actual_status_code is None:
        error_text = network_error or "Network error — no response received"
        validation_errors.append(error_text)
        result["passed"] = False
        result["expected_status_code"] = expected_status_code
        result["validation_errors"] = validation_errors
        return result

    # ── Status code check ─────────────────────────────────────────────────
    if expected_status_code is not None:
        status_passed = actual_status_code == expected_status_code
        if not status_passed:
            validation_errors.append(
                f"Expected status {expected_status_code}, got {actual_status_code}"
            )
    else:
        # No expected status defined — accept 2xx range
        status_passed = 200 <= actual_status_code <= 299
        if not status_passed:
            validation_errors.append(
                "No expected status code defined; actual "
                f"{actual_status_code} is not 2xx"
            )

    # ── Response body schema check ────────────────────────────────────────
    schema = _lookup_schema(
        parsed_api_model,
        test_case.get("endpoint_path", ""),
        test_case.get("endpoint_method", ""),
        str(expected_status_code or actual_status_code or ""),
    )

    schema_passed = True
    if isinstance(schema, dict) and "properties" in schema:
        required_fields = schema.get("required") or []
        if required_fields:
            if actual_body is None or actual_body == "" or actual_body == {}:
                validation_errors.append(
                    "Empty response body — expected schema not satisfied"
                )
                schema_passed = False
            elif isinstance(actual_body, dict):
                for field in required_fields:
                    if field not in actual_body:
                        validation_errors.append(f"Missing required field: '{field}'")
                        schema_passed = False

    result["passed"] = status_passed and schema_passed
    result["expected_status_code"] = expected_status_code
    result["validation_errors"] = validation_errors
    return result


def _lookup_schema(
    parsed_api_model: Optional[dict],
    endpoint_path: str,
    endpoint_method: str,
    status_key: str,
) -> Optional[object]:
    """Find the response schema for an endpoint + status code combination.

    Returns the schema value (dict, str, or None).
    """
    for ep in (parsed_api_model or {}).get("endpoints") or []:
        if ep.get("path") == endpoint_path and ep.get("method") == endpoint_method:
            return (ep.get("response_schemas") or {}).get(status_key)
    return None
