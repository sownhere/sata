"""Unit tests for src.tools.test_case_generator."""

import json

from src.tools.test_case_generator import (
    filter_test_cases_against_confirmed_spec,
    generate_test_cases_for_model,
)


class FakeLLM:
    """Minimal fake LLM that returns a fixed JSON payload."""

    def __init__(self, payload) -> None:
        self.payload = payload
        self.invocations = 0

    def invoke(self, _messages):
        self.invocations += 1
        if isinstance(self.payload, str):
            content = self.payload
        else:
            content = json.dumps(self.payload)
        return type("Response", (), {"content": content})()


class SequenceLLM:
    """LLM test double that yields configured outcomes per invocation."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.invocations = 0

    def invoke(self, _messages):
        self.invocations += 1
        if not self.outcomes:
            raise RuntimeError("No outcomes configured for SequenceLLM")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, str):
            content = outcome
        else:
            content = json.dumps(outcome)
        return type("Response", (), {"content": content})()


def _parsed_api_model(auth_required: bool) -> dict:
    return {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/users",
                "method": "POST",
                "operation_id": "createUser",
                "summary": "Create user",
                "parameters": [
                    {
                        "name": "trace_id",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": None,
                    }
                ],
                "request_body": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
                "response_schemas": {"201": {"type": "object"}},
                "auth_required": auth_required,
                "tags": ["users"],
            }
        ],
    }


def test_generate_test_cases_covers_required_categories_with_valid_priorities():
    llm = FakeLLM(
        {
            "test_cases": [
                {
                    "id": "tc-custom-happy",
                    "endpoint_path": "/users",
                    "endpoint_method": "POST",
                    "category": "happy_path",
                    "priority": "P1",
                    "title": "Create user succeeds",
                    "description": "Valid request returns 201.",
                    "expected": {"status_code": 201},
                }
            ]
        }
    )

    result = generate_test_cases_for_model(
        _parsed_api_model(auth_required=True), llm=llm
    )
    test_cases = result["test_cases"]

    categories = {case["category"] for case in test_cases}
    assert categories == {
        "happy_path",
        "missing_data",
        "invalid_format",
        "wrong_type",
        "auth_failure",
        "boundary",
        "duplicate",
        "method_not_allowed",
    }
    assert {case["priority"] for case in test_cases}.issubset({"P1", "P2", "P3"})
    assert result["failed_endpoints"] == []
    assert llm.invocations == 1


def test_generate_test_cases_skips_auth_failure_for_public_endpoint():
    llm = FakeLLM(
        {
            "test_cases": [
                {
                    "endpoint_path": "/users",
                    "endpoint_method": "POST",
                    "category": "auth_failure",
                    "priority": "P1",
                    "title": "Should be removed",
                    "description": "Endpoint is public.",
                }
            ]
        }
    )

    result = generate_test_cases_for_model(
        _parsed_api_model(auth_required=False), llm=llm
    )
    categories = {case["category"] for case in result["test_cases"]}

    assert "auth_failure" not in categories


def test_generate_test_cases_retries_once_after_transient_llm_failure():
    llm = SequenceLLM(
        [
            RuntimeError("timeout"),
            {
                "test_cases": [
                    {
                        "endpoint_path": "/users",
                        "endpoint_method": "POST",
                        "category": "happy_path",
                        "priority": "P1",
                        "title": "Create user succeeds",
                        "description": "Valid request returns 201.",
                        "expected": {"status_code": 201},
                    }
                ]
            },
        ]
    )

    result = generate_test_cases_for_model(
        _parsed_api_model(auth_required=False),
        llm=llm,
        retry_count=1,
    )

    assert result["failed_endpoints"] == []
    assert len(result["test_cases"]) >= 1
    assert llm.invocations == 2


def test_generate_test_cases_retries_at_least_once_even_when_retry_count_zero():
    llm = SequenceLLM(
        [
            RuntimeError("timeout"),
            {
                "test_cases": [
                    {
                        "endpoint_path": "/users",
                        "endpoint_method": "POST",
                        "category": "happy_path",
                        "priority": "P1",
                        "title": "Create user succeeds",
                        "description": "Valid request returns 201.",
                        "expected": {"status_code": 201},
                    }
                ]
            },
        ]
    )

    result = generate_test_cases_for_model(
        _parsed_api_model(auth_required=False),
        llm=llm,
        retry_count=0,
    )

    assert result["failed_endpoints"] == []
    assert len(result["test_cases"]) >= 1
    assert llm.invocations == 2


def test_filter_discards_unknown_endpoints_and_invalid_field_references():
    parsed_model = _parsed_api_model(auth_required=True)
    candidate_cases = [
        {
            "id": "tc-valid",
            "endpoint_path": "/users",
            "endpoint_method": "POST",
            "category": "missing_data",
            "priority": "P1",
            "title": "Missing required email",
            "description": "Email is required.",
            "field_refs": ["email"],
        },
        {
            "id": "tc-unknown-endpoint",
            "endpoint_path": "/missing",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "Unknown endpoint",
            "description": "Should be dropped.",
        },
        {
            "id": "tc-unknown-field",
            "endpoint_path": "/users",
            "endpoint_method": "POST",
            "category": "wrong_type",
            "priority": "P2",
            "title": "Unknown field reference",
            "description": "Should be dropped.",
            "field_refs": ["nonexistent_field"],
        },
    ]

    filtered = filter_test_cases_against_confirmed_spec(candidate_cases, parsed_model)

    assert len(filtered["accepted"]) == 1
    assert filtered["accepted"][0]["id"] == "tc-valid"
    assert {item["reason"] for item in filtered["dropped"]} == {
        "unknown_endpoint",
        "unknown_field_refs",
    }
