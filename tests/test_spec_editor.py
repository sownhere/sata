"""Unit tests for app.utils.spec_editor (offline, no Streamlit)."""

import copy

import pytest

from app.utils.spec_editor import add_endpoint, remove_endpoint, update_endpoint_field


def _sample_model() -> dict:
    return {
        "endpoints": [
            {
                "path": "/pets",
                "method": "GET",
                "operation_id": "listPets",
                "summary": "List",
                "parameters": [],
                "request_body": None,
                "response_schemas": {},
                "auth_required": False,
                "tags": [],
            },
            {
                "path": "/pets/{id}",
                "method": "GET",
                "operation_id": "getPet",
                "summary": "Get one",
                "parameters": [],
                "request_body": None,
                "response_schemas": {},
                "auth_required": False,
                "tags": ["pet"],
            },
        ],
        "title": "Petstore",
        "version": "1",
        "auth": {},
    }


def test_update_endpoint_field_changes_field_and_isolation() -> None:
    model = _sample_model()
    result = update_endpoint_field(model, 0, "summary", "Updated")

    assert result is not model
    assert model["endpoints"][0]["summary"] == "List"
    assert result["endpoints"][0]["summary"] == "Updated"
    assert result["endpoints"][1] == model["endpoints"][1]
    assert result["endpoints"][1] is not model["endpoints"][1]


def test_update_endpoint_field_invalid_index_no_change() -> None:
    model = _sample_model()
    original_eps = copy.deepcopy(model["endpoints"])
    result = update_endpoint_field(model, 99, "summary", "X")
    assert result["endpoints"] == original_eps


def test_update_endpoint_field_negative_index_no_change() -> None:
    model = _sample_model()
    original_eps = copy.deepcopy(model["endpoints"])
    result = update_endpoint_field(model, -1, "summary", "X")
    assert result["endpoints"] == original_eps


def test_add_endpoint_appends_and_preserves_existing() -> None:
    model = _sample_model()
    new_ep = {
        "path": "/new",
        "method": "POST",
        "operation_id": "n",
        "summary": "",
        "parameters": [],
        "request_body": None,
        "response_schemas": {},
        "auth_required": False,
        "tags": [],
    }
    result = add_endpoint(model, new_ep)

    assert len(result["endpoints"]) == 3
    assert result["endpoints"][-1]["path"] == "/new"
    assert model["endpoints"] == _sample_model()["endpoints"]


@pytest.mark.parametrize(
    ("payload", "msg"),
    [
        ({"method": "GET"}, "path"),
        ({"path": "/x"}, "method"),
        ({}, "path"),
    ],
)
def test_add_endpoint_raises_on_missing_required(payload: dict, msg: str) -> None:
    model = _sample_model()
    with pytest.raises(ValueError, match=msg):
        add_endpoint(model, payload)


def test_add_endpoint_rejects_whitespace_path_or_method() -> None:
    model = _sample_model()
    with pytest.raises(ValueError, match="path"):
        add_endpoint(model, {"path": "   ", "method": "GET"})
    with pytest.raises(ValueError, match="method"):
        add_endpoint(model, {"path": "/ok", "method": "  "})


def test_remove_endpoint_by_index() -> None:
    model = _sample_model()
    result = remove_endpoint(model, 0)

    assert len(result["endpoints"]) == 1
    assert result["endpoints"][0]["path"] == "/pets/{id}"
    assert len(model["endpoints"]) == 2


def test_remove_endpoint_out_of_range_noop() -> None:
    model = _sample_model()
    result = remove_endpoint(model, 10)
    assert result["endpoints"] == model["endpoints"]
    assert result is not model
