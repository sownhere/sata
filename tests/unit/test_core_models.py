"""Unit tests for src.core.models — Pydantic v2 data contracts."""

from src.core.models import ApiModel, AuthModel, EndpointModel, GapRecord

# ── Fixtures ──────────────────────────────────────────────────────────────────

CANONICAL_ENDPOINT = {
    "path": "/users",
    "method": "GET",
    "operation_id": "listUsers",
    "summary": "List users",
    "parameters": [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"},
            "description": None,
        }
    ],
    "request_body": None,
    "response_schemas": {"200": {"type": "array", "items": {}}},
    "auth_required": True,
    "tags": ["users"],
}

CANONICAL_AUTH = {
    "type": "bearer",
    "scheme": "Bearer",
    "in": "header",
    "name": "Authorization",
}

CANONICAL_GAP = {
    "id": "get-users-missing-response-schema",
    "endpoint_key": "GET /users",
    "path": "/users",
    "method": "GET",
    "gap_type": "missing_response_schema",
    "field": "response_schema",
    "question": "What does the 200 response return?",
    "input_type": "text",
    "options": None,
}


# ── EndpointModel ─────────────────────────────────────────────────────────────


def test_endpoint_model_validates_canonical_shape():
    endpoint = EndpointModel(**CANONICAL_ENDPOINT)
    assert endpoint.path == "/users"
    assert endpoint.method == "GET"
    assert endpoint.operation_id == "listUsers"
    assert endpoint.auth_required is True
    assert len(endpoint.parameters) == 1
    assert endpoint.tags == ["users"]


def test_endpoint_model_defaults_for_optional_fields():
    endpoint = EndpointModel(path="/health", method="GET")
    assert endpoint.operation_id == ""
    assert endpoint.summary == ""
    assert endpoint.parameters == []
    assert endpoint.request_body is None
    assert endpoint.response_schemas == {}
    assert endpoint.auth_required is False
    assert endpoint.tags == []


# ── AuthModel ─────────────────────────────────────────────────────────────────


def test_auth_model_validates_canonical_shape_with_in_alias():
    # The canonical dict uses "in" as the key — must work via alias
    auth = AuthModel(**CANONICAL_AUTH)
    assert auth.type == "bearer"
    assert auth.scheme == "Bearer"
    assert auth.location == "header"
    assert auth.name == "Authorization"


def test_auth_model_accepts_none_values():
    auth = AuthModel(type=None, scheme=None, name=None)
    assert auth.type is None
    assert auth.location is None


# ── ApiModel ──────────────────────────────────────────────────────────────────


def test_api_model_validates_full_canonical_parsed_model():
    data = {
        "title": "Petstore API",
        "version": "1.0.0",
        "endpoints": [CANONICAL_ENDPOINT],
        "auth": CANONICAL_AUTH,
    }
    model = ApiModel(**data)
    assert model.title == "Petstore API"
    assert model.version == "1.0.0"
    assert len(model.endpoints) == 1
    assert model.endpoints[0].path == "/users"
    assert model.auth is not None
    assert model.auth.type == "bearer"


def test_api_model_defaults_to_empty():
    model = ApiModel()
    assert model.title == ""
    assert model.endpoints == []
    assert model.auth is None


# ── GapRecord ─────────────────────────────────────────────────────────────────


def test_gap_record_validates_canonical_shape():
    gap = GapRecord(**CANONICAL_GAP)
    assert gap.id == "get-users-missing-response-schema"
    assert gap.endpoint_key == "GET /users"
    assert gap.gap_type == "missing_response_schema"
    assert gap.input_type == "text"
    assert gap.options is None


def test_gap_record_validates_with_options():
    gap = GapRecord(
        id="post-login-ambiguous-auth",
        endpoint_key="POST /login",
        path="/login",
        method="POST",
        gap_type="ambiguous_auth",
        field="auth_type",
        question="Which auth method does this endpoint use?",
        input_type="select",
        options=["bearer", "apiKey", "none"],
    )
    assert gap.options == ["bearer", "apiKey", "none"]
