"""Tests for conversational API model extraction."""

import json

import pytest

from app.utils.conversational_spec_builder import (
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
        "content": "I have GET /users and POST /users. GET returns a list. POST accepts name and returns 201 with a user object. No auth.",
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
