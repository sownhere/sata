"""Tests for the review_spec pipeline node in app/pipeline.py."""

from src.core.state import initial_state
from src.nodes.review_spec import review_spec


def test_review_spec_sets_stage_when_endpoints_exist():
    state = initial_state()
    state["error_message"] = "stale error"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/users",
                "method": "GET",
                "operation_id": "listUsers",
                "summary": "List users",
                "parameters": [],
                "request_body": None,
                "response_schemas": {"200": {"type": "array"}},
                "auth_required": False,
                "tags": [],
            }
        ],
    }

    result = review_spec(state)

    assert result is state
    assert result["pipeline_stage"] == "review_spec"
    assert result["error_message"] is None


def test_review_spec_returns_to_ingestion_when_no_endpoints_exist():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Empty API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [],
    }
    state["pipeline_stage"] = "review_spec"

    result = review_spec(state)

    assert result["pipeline_stage"] == "spec_ingestion"
    assert result["spec_confirmed"] is False
    assert "no endpoints" in result["error_message"].lower()


def test_review_spec_handles_missing_or_malformed_models_gracefully():
    state = initial_state()
    state["parsed_api_model"] = {"title": "Broken API", "endpoints": "not-a-list"}
    state["pipeline_stage"] = "review_spec"

    result = review_spec(state)

    assert result["pipeline_stage"] == "spec_ingestion"
    assert result["spec_confirmed"] is False
    assert result["error_message"] is not None
