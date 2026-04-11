"""Unit tests for src.tools.failure_analyzer — mocks LLM, no real calls."""

import json
from unittest.mock import MagicMock

from src.tools.failure_analyzer import (
    analyze_failures,
    diagnose_all_failed_results,
    suggest_next_test_scenarios,
)


def _make_failed_result(test_id="tc-1", actual=404, expected=200, errors=None):
    return {
        "test_id": test_id,
        "test_title": f"Test {test_id}",
        "endpoint_method": "GET",
        "endpoint_path": "/users",
        "actual_status_code": actual,
        "expected_status_code": expected,
        "actual_response_body": {"secret": "should not go to LLM"},
        "error_message": None,
        "attempt_count": 1,
        "passed": False,
        "validation_errors": errors or [f"Expected status {expected}, got {actual}"],
    }


# ── Empty / all-passed ────────────────────────────────────────────────────────


def test_analyze_failures_empty_returns_all_passed():
    result = analyze_failures([])
    assert result["all_passed"] is True
    assert result["all_failed"] is False
    assert result["patterns"] == []
    assert result["explanations"] == []


# ── LLM call safety ───────────────────────────────────────────────────────────


def test_analyze_failures_calls_llm_with_safe_fields_only():
    """actual_response_body must never be sent to the LLM."""
    failed = [_make_failed_result()]
    mock_llm = MagicMock()
    llm_response = MagicMock()
    llm_response.content = json.dumps(
        {
            "patterns": [],
            "explanations": [
                {
                    "test_id": "tc-1",
                    "what_broke": "x",
                    "why_it_matters": "y",
                    "how_to_fix": "z",
                }
            ],
        }
    )
    mock_llm.invoke.return_value = llm_response

    analyze_failures(failed, llm=mock_llm)

    assert mock_llm.invoke.called
    call_args = mock_llm.invoke.call_args
    prompt_text = str(call_args)
    # actual_response_body content must NOT appear
    assert "should not go to LLM" not in prompt_text


# ── Normal response parsing ───────────────────────────────────────────────────


def test_analyze_failures_returns_parsed_patterns_and_explanations():
    failed = [_make_failed_result()]
    mock_llm = MagicMock()
    llm_payload = {
        "patterns": [
            {
                "pattern_type": "status_mismatch",
                "severity": "High",
                "count": 1,
                "description": "GET /users returns 404",
                "affected_test_ids": ["tc-1"],
            }
        ],
        "explanations": [
            {
                "test_id": "tc-1",
                "what_broke": "GET /users returned 404",
                "why_it_matters": "Endpoint missing",
                "how_to_fix": "Check route registration",
            }
        ],
    }
    resp = MagicMock()
    resp.content = json.dumps(llm_payload)
    mock_llm.invoke.return_value = resp

    result = analyze_failures(failed, llm=mock_llm)

    assert result["all_passed"] is False
    assert result["all_failed"] is False
    assert len(result["patterns"]) == 1
    assert result["patterns"][0]["severity"] == "High"
    assert len(result["explanations"]) == 1
    assert result["explanations"][0]["test_id"] == "tc-1"


# ── Parse error handling ──────────────────────────────────────────────────────


def test_analyze_failures_handles_llm_parse_error_gracefully():
    failed = [_make_failed_result()]
    mock_llm = MagicMock()
    resp = MagicMock()
    resp.content = "not valid json {{{"
    mock_llm.invoke.return_value = resp

    result = analyze_failures(failed, llm=mock_llm)

    assert result["all_passed"] is False
    assert result["all_failed"] is False
    assert "parse_error" in result
    assert result["patterns"] == []
    assert result["explanations"] == []


# ── Multiple failures ─────────────────────────────────────────────────────────


def test_analyze_failures_passes_all_failed_test_ids():
    """All failed test IDs should appear in the prompt payload."""
    failed = [
        _make_failed_result("tc-1"),
        _make_failed_result("tc-2"),
    ]
    mock_llm = MagicMock()
    resp = MagicMock()
    resp.content = json.dumps({"patterns": [], "explanations": []})
    mock_llm.invoke.return_value = resp

    analyze_failures(failed, llm=mock_llm)

    prompt_text = str(mock_llm.invoke.call_args)
    assert "tc-1" in prompt_text
    assert "tc-2" in prompt_text


def test_suggest_next_test_scenarios_for_all_passed_run():
    test_results = [{"test_id": "tc-1", "passed": True}]
    parsed_api_model = {
        "auth": {"type": "bearer"},
        "endpoints": [{"method": "POST"}],
    }
    test_cases = [{"category": "happy_path"}]

    suggestions = suggest_next_test_scenarios(
        test_results,
        parsed_api_model,
        test_cases,
    )

    assert len(suggestions) == 3
    assert any("boundary" in suggestion.lower() for suggestion in suggestions)
    assert any("credential" in suggestion.lower() for suggestion in suggestions)


def test_diagnose_all_failed_results_prefers_auth_misconfiguration():
    diagnosis = diagnose_all_failed_results(
        [
            {
                "passed": False,
                "actual_status_code": 401,
                "validation_errors": ["Unauthorized"],
                "error_message": None,
            },
            {
                "passed": False,
                "actual_status_code": 403,
                "validation_errors": ["Forbidden"],
                "error_message": None,
            },
        ],
        {"auth": {"type": "bearer", "scheme": "Bearer", "in": "header"}},
    )

    assert diagnosis["category"] == "auth_misconfiguration"
    assert "Bearer" in diagnosis["message"]
    assert "secret" in diagnosis["message"].lower()


def test_diagnose_all_failed_results_detects_wrong_base_url():
    diagnosis = diagnose_all_failed_results(
        [
            {
                "passed": False,
                "actual_status_code": 404,
                "validation_errors": ["Expected status 200, got 404"],
                "error_message": None,
            }
        ],
        {"auth": None},
    )

    assert diagnosis["category"] == "wrong_base_url"


def test_diagnose_all_failed_results_detects_unreachable_api():
    diagnosis = diagnose_all_failed_results(
        [
            {
                "passed": False,
                "actual_status_code": None,
                "validation_errors": ["connection refused"],
                "error_message": "connection refused",
            }
        ],
        {"auth": None},
    )

    assert diagnosis["category"] == "api_unreachable"
