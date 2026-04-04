"""Tests for conversational API model extraction."""

import json

import pytest

from src.nodes.fill_gaps import fill_gaps
from src.tools.conversational_builder import (
    extract_api_model_from_conversation,
)


class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return type("Response", (), {"content": self.content})()


VALID_CONVERSATION = [
    {
        "role": "assistant",
        "content": "Describe your API endpoints, inputs, outputs, and auth.",
    },
    {
        "role": "user",
        "content": (
            "I have GET /users and POST /users. GET returns a list."
            " POST accepts name and returns 201 with a user object. No auth."
        ),
    },
]


def test_complete_response_returns_canonical_api_model():
    llm = FakeLLM(
        json.dumps(
            {
                "status": "complete",
                "api_model": {
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
                    "auth": {"type": None, "scheme": None, "in": None, "name": None},
                    "title": "Users API",
                    "version": "unknown",
                },
            }
        )
    )

    result = extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)

    assert result["status"] == "complete"
    assert result["api_model"]["title"] == "Users API"
    assert result["api_model"]["endpoints"][0]["method"] == "GET"
    assert llm.last_messages is not None


def test_needs_more_info_response_returns_follow_up_question():
    llm = FakeLLM(
        json.dumps(
            {
                "status": "needs_more_info",
                "question": "What does POST /users return on success?",
            }
        )
    )

    result = extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)

    assert result == {
        "status": "needs_more_info",
        "question": "What does POST /users return on success?",
    }


def test_invalid_json_response_raises_value_error():
    llm = FakeLLM("not json")

    with pytest.raises(ValueError, match="valid JSON"):
        extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)


def test_complete_response_with_wrong_shape_raises_value_error():
    llm = FakeLLM(
        json.dumps(
            {
                "status": "complete",
                "api_model": {
                    "endpoints": [],
                    "auth": {"type": None, "scheme": None, "in": None, "name": None},
                    "title": "Users API",
                    "version": "unknown",
                },
            }
        )
    )

    with pytest.raises(ValueError, match="at least one endpoint"):
        extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)


def test_missing_question_for_needs_more_info_raises_value_error():
    llm = FakeLLM(json.dumps({"status": "needs_more_info"}))

    with pytest.raises(ValueError, match="follow-up question"):
        extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)


def test_extra_top_level_keys_in_llm_response_are_accepted():
    """Extra keys from LLM output should not raise ValueError (subset check)."""
    llm = FakeLLM(
        json.dumps(
            {
                "status": "complete",
                "api_model": {
                    "endpoints": [
                        {
                            "path": "/items",
                            "method": "GET",
                            "operation_id": "listItems",
                            "summary": "List items",
                            "parameters": [],
                            "request_body": None,
                            "response_schemas": {"200": {"type": "array"}},
                            "auth_required": False,
                            "tags": [],
                            "extra_endpoint_key": "ignored",
                        }
                    ],
                    "auth": {"type": None, "scheme": None, "in": None, "name": None},
                    "title": "Items API",
                    "version": "1.0",
                    "extra_top_level_key": "ignored",
                },
            }
        )
    )

    result = extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)

    assert result["status"] == "complete"
    assert result["api_model"]["title"] == "Items API"


def test_empty_response_schemas_accepted_for_204_only_endpoint():
    """Empty response_schemas dict is valid for 204-only/body-less endpoints."""
    llm = FakeLLM(
        json.dumps(
            {
                "status": "complete",
                "api_model": {
                    "endpoints": [
                        {
                            "path": "/items/{id}",
                            "method": "DELETE",
                            "operation_id": "deleteItem",
                            "summary": "Delete an item",
                            "parameters": [],
                            "request_body": None,
                            "response_schemas": {},
                            "auth_required": True,
                            "tags": [],
                        }
                    ],
                    "auth": {
                        "type": "bearer",
                        "scheme": "Bearer",
                        "in": "header",
                        "name": "Authorization",
                    },
                    "title": "Items API",
                    "version": "1.0",
                },
            }
        )
    )

    result = extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)

    assert result["status"] == "complete"
    assert result["api_model"]["endpoints"][0]["response_schemas"] == {}


def test_code_fenced_json_is_correctly_parsed():
    """JSON wrapped in ```json...``` markdown fences must be parsed successfully."""
    payload = {
        "status": "needs_more_info",
        "question": "What HTTP method does /orders use?",
    }
    fenced = f"```json\n{json.dumps(payload)}\n```"
    llm = FakeLLM(fenced)

    result = extract_api_model_from_conversation(VALID_CONVERSATION, llm=llm)

    assert result == {
        "status": "needs_more_info",
        "question": "What HTTP method does /orders use?",
    }


def test_iteration_limit_in_fill_gaps_returns_error_and_resets_stage():
    """fill_gaps must return an error and reset to spec_ingestion after 10 turns."""
    state = {
        "spec_source": "chat",
        "conversation_messages": [
            {"role": "user", "content": "I have some endpoints."}
        ],
        "iteration_count": 10,
        "pipeline_stage": "fill_gaps",
        "error_message": None,
        "parsed_api_model": None,
        "conversation_question": None,
        "detected_gaps": None,
        "gap_answers": None,
    }

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "spec_ingestion"
    assert result["error_message"] is not None
    assert "restart" in result["error_message"].lower()
