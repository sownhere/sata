"""Deterministic formatting helpers for the Spec Review checkpoint.

Canonical location: src.ui.spec_review
(Migrated from app/utils/spec_review.py — no logic changes.)
"""

from typing import Any, Optional


def get_stage_display_label(stage: str) -> str:
    """Return the user-facing label for a pipeline stage key."""
    normalized = str(stage or "initial")
    if normalized == "review_spec":
        return "Spec Review"
    return normalized.replace("_", " ").title()


def build_endpoint_summary_rows(parsed_api_model: dict) -> list[dict]:
    """Flatten the canonical parsed model into concise summary rows."""
    endpoints = parsed_api_model.get("endpoints")
    if not isinstance(endpoints, list):
        return []

    auth = parsed_api_model.get("auth")
    top_level_auth = auth if isinstance(auth, dict) else {}

    rows = []
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue
        rows.append(
            {
                "method": str(endpoint.get("method") or "-"),
                "path": str(endpoint.get("path") or "-"),
                "operation_id": str(endpoint.get("operation_id") or "-"),
                "summary": str(endpoint.get("summary") or "-"),
                "parameters": _parameter_count_summary(endpoint.get("parameters")),
                "request_body": _request_body_summary(endpoint.get("request_body")),
                "responses": _responses_summary(endpoint.get("response_schemas")),
                "auth": _auth_label(
                    bool(endpoint.get("auth_required")), top_level_auth
                ),
            }
        )
    return rows


def build_endpoint_detail_view(
    endpoint: dict, *, top_level_auth: Optional[dict] = None
) -> dict:
    """Format one endpoint into deterministic detail fields for the review UI."""
    if not isinstance(endpoint, dict):
        return {}
    auth_dict = top_level_auth if isinstance(top_level_auth, dict) else {}
    parameters = _parameter_rows(endpoint.get("parameters"))
    return {
        "heading": (
            f"{str(endpoint.get('method') or '-')} {str(endpoint.get('path') or '-')}"
        ),
        "operation_id": str(endpoint.get("operation_id") or "-"),
        "summary": str(endpoint.get("summary") or "No summary provided"),
        "parameter_summary": f"{len(parameters)} parameter(s)"
        if parameters
        else "No parameters",
        "parameters": parameters,
        "request_body_summary": _request_body_summary(endpoint.get("request_body")),
        "responses": _response_rows(endpoint.get("response_schemas")),
        "auth": _auth_label(bool(endpoint.get("auth_required")), auth_dict),
        "tags": _tags_summary(endpoint.get("tags")),
    }


def _parameter_count_summary(parameters: Any) -> str:
    if isinstance(parameters, list):
        return f"{len(parameters)} parameter(s)"
    return "0 parameter(s)"


def _parameter_rows(parameters: Any) -> list[dict]:
    if not isinstance(parameters, list):
        return []

    rows = []
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        rows.append(
            {
                "name": str(parameter.get("name") or "-"),
                "location": str(parameter.get("in") or "-"),
                "type": _schema_summary(
                    parameter.get("schema"), empty_fallback="unknown"
                ),
                "required": "Yes" if parameter.get("required") else "No",
            }
        )
    return rows


def _request_body_summary(request_body: Any) -> str:
    if not request_body:  # None or empty dict/list
        return "No request body"
    return _schema_summary(request_body)


def _responses_summary(response_schemas: Any) -> str:
    rows = _response_rows(response_schemas)
    if not rows:
        return "No responses documented"
    return "; ".join(f"{row['status_code']}: {row['summary']}" for row in rows)


def _response_rows(response_schemas: Any) -> list[dict]:
    if not isinstance(response_schemas, dict) or not response_schemas:
        return []

    rows = []
    for status_code in sorted(response_schemas.keys(), key=lambda value: str(value)):
        rows.append(
            {
                "status_code": str(status_code),
                "summary": _schema_summary(response_schemas.get(status_code)),
            }
        )
    return rows


def _auth_label(auth_required: bool, auth: dict) -> str:
    if not auth_required:
        return "Not required"
    if isinstance(auth, dict) and any(auth.values()):
        return "Required"
    return "Required (details unavailable)"


def _tags_summary(tags: Any) -> str:
    if isinstance(tags, list) and tags:
        return ", ".join(str(tag) for tag in tags)
    return "No tags"


def _schema_summary(schema: Any, empty_fallback: str = "Schema defined") -> str:
    if schema is None:
        return empty_fallback
    if isinstance(schema, str):
        value = schema.strip()
        return value or empty_fallback
    if not isinstance(schema, dict):
        return str(schema)
    if not schema:
        return empty_fallback
    if "$ref" in schema:
        ref = str(schema["$ref"])
        return ref.rsplit("/", 1)[-1] or empty_fallback
    if schema.get("type") == "array":
        item_summary = _schema_summary(schema.get("items"), empty_fallback="item")
        return f"array<{item_summary}>"
    if schema.get("type"):
        return str(schema["type"])
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return empty_fallback
