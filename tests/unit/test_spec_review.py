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
