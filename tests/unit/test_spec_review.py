"""Tests for deterministic Spec Review formatting helpers."""

from src.ui.spec_review import (
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    get_stage_display_label,
)


def test_get_stage_display_label_uses_explicit_mapping_for_review_spec():
    assert get_stage_display_label("review_spec") == "Spec Review"
    assert get_stage_display_label("fill_gaps") == "Fill Gaps"


def test_build_endpoint_summary_rows_returns_concise_display_values():
    parsed_api_model = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {
            "type": "bearer",
            "scheme": "Bearer",
            "in": "header",
            "name": "Authorization",
        },
        "endpoints": [
            {
                "path": "/users/{id}",
                "method": "PUT",
                "operation_id": "updateUser",
                "summary": "Update user",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": None,
                    },
                    {
                        "name": "expand",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "boolean"},
                        "description": None,
                    },
                ],
                "request_body": {"type": "object"},
                "response_schemas": {"200": {"type": "object"}, "400": "Bad Request"},
                "auth_required": True,
                "tags": ["users"],
            }
        ],
    }

    rows = build_endpoint_summary_rows(parsed_api_model)

    assert rows == [
        {
            "method": "PUT",
            "path": "/users/{id}",
            "operation_id": "updateUser",
            "summary": "Update user",
            "parameters": "2 parameter(s)",
            "request_body": "object",
            "responses": "200: object; 400: Bad Request",
            "auth": "Required",
        }
    ]


def test_build_endpoint_detail_view_handles_empty_and_string_values():
    endpoint = {
        "path": "/health",
        "method": "GET",
        "operation_id": None,
        "summary": None,
        "parameters": [],
        "request_body": None,
        "response_schemas": {"200": "OK"},
        "auth_required": False,
        "tags": [],
    }

    detail = build_endpoint_detail_view(endpoint)

    assert detail["heading"] == "GET /health"
    assert detail["parameters"] == []
    assert detail["parameter_summary"] == "No parameters"
    assert detail["request_body_summary"] == "No request body"
    assert detail["responses"] == [{"status_code": "200", "summary": "OK"}]
    assert detail["auth"] == "Not required"
    assert detail["tags"] == "No tags"


def test_build_endpoint_detail_view_returns_empty_dict_for_none_input():
    assert build_endpoint_detail_view(None) == {}


def test_build_endpoint_detail_view_uses_top_level_auth_when_provided():
    endpoint = {
        "path": "/secure",
        "method": "POST",
        "operation_id": "createItem",
        "summary": "Create item",
        "parameters": [],
        "request_body": None,
        "response_schemas": {"201": {"type": "object"}},
        "auth_required": True,
        "tags": [],
    }
    top_level_auth = {
        "type": "bearer",
        "scheme": "Bearer",
        "in": "header",
        "name": "Authorization",
    }

    detail = build_endpoint_detail_view(endpoint, top_level_auth=top_level_auth)

    assert detail["auth"] == "Required"


def test_build_endpoint_detail_view_without_top_level_auth_shows_unavailable():
    endpoint = {
        "path": "/secure",
        "method": "GET",
        "operation_id": "getItem",
        "summary": "Get item",
        "parameters": [],
        "request_body": None,
        "response_schemas": {"200": {"type": "object"}},
        "auth_required": True,
        "tags": [],
    }

    detail = build_endpoint_detail_view(endpoint)  # no top_level_auth

    assert detail["auth"] == "Required (details unavailable)"


def test_build_endpoint_detail_view_none_operation_id_and_summary_fallback():
    endpoint = {
        "path": "/anon",
        "method": "DELETE",
        "operation_id": None,
        "summary": None,
        "parameters": [],
        "request_body": None,
        "response_schemas": None,
        "auth_required": False,
        "tags": [],
    }

    detail = build_endpoint_detail_view(endpoint)

    assert detail["operation_id"] == "-"
    assert detail["summary"] == "No summary provided"
    assert detail["responses"] == []


def test_build_endpoint_detail_view_absent_response_schemas_key():
    """Endpoint dict with no response_schemas key at all must not raise."""
    endpoint = {
        "path": "/minimal",
        "method": "GET",
        "operation_id": "minimal",
        "summary": "Minimal",
        "parameters": [],
        "request_body": None,
        # response_schemas intentionally absent
        "auth_required": False,
        "tags": [],
    }

    detail = build_endpoint_detail_view(endpoint)

    assert detail["responses"] == []


def test_request_body_summary_returns_no_request_body_for_empty_dict():
    from src.ui.spec_review import _request_body_summary

    assert _request_body_summary({}) == "No request body"
    assert _request_body_summary(None) == "No request body"
    assert _request_body_summary({"type": "object"}) == "object"
