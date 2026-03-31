"""Tests for app.utils.spec_parser — OpenAPI/Swagger parsing logic.

Covers: valid JSON parse, valid YAML parse, malformed input, missing paths key,
missing openapi field, non-3.x version, multiple endpoints, auth extraction.
"""

import json
import pytest

from app.utils.spec_parser import parse_openapi_spec


# ── Fixtures ────────────────────────────────────────────────────────────────

MINIMAL_OPENAPI_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
)

MINIMAL_OPENAPI_YAML = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      responses:
        "200":
          description: OK
"""

MULTI_ENDPOINT_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Multi API", "version": "2.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                },
            },
            "/users/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "getUser",
                    "responses": {"200": {"description": "OK"}},
                },
            },
        },
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
        },
        "security": [{"bearerAuth": []}],
    }
)

API_KEY_AUTH_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Key API", "version": "1.0.0"},
        "paths": {"/data": {"get": {"responses": {"200": {"description": "OK"}}}}},
        "components": {
            "securitySchemes": {
                "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        },
    }
)


# ── Tests: Valid parsing ────────────────────────────────────────────────────


class TestValidParsing:
    def test_parse_valid_json(self):
        """AC 1: Valid OpenAPI 3.0 JSON file parses correctly."""
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)

        assert result["title"] == "Test API"
        assert result["version"] == "1.0.0"
        assert len(result["endpoints"]) == 1

        ep = result["endpoints"][0]
        assert ep["path"] == "/users"
        assert ep["method"] == "GET"
        assert ep["operation_id"] == "listUsers"
        assert ep["summary"] == "List users"
        assert len(ep["parameters"]) == 1
        assert ep["parameters"][0]["name"] == "limit"
        assert ep["parameters"][0]["in"] == "query"
        assert ep["parameters"][0]["required"] is False
        assert ep["request_body"] is None
        assert ep["tags"] == []

    def test_parse_valid_yaml(self):
        """AC 2: Valid OpenAPI 3.0 YAML file parses correctly."""
        result = parse_openapi_spec(MINIMAL_OPENAPI_YAML)

        assert result["title"] == "Test API"
        assert result["version"] == "1.0.0"
        assert len(result["endpoints"]) == 1

        ep = result["endpoints"][0]
        assert ep["path"] == "/users"
        assert ep["method"] == "GET"
        assert ep["operation_id"] == "listUsers"

    def test_multi_endpoint_extraction(self):
        """Validates multiple endpoints across multiple paths and methods."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)

        assert result["title"] == "Multi API"
        assert len(result["endpoints"]) == 3

        methods = {ep["method"] for ep in result["endpoints"]}
        assert methods == {"GET", "POST"}

        paths = {ep["path"] for ep in result["endpoints"]}
        assert paths == {"/users", "/users/{id}"}

    def test_request_body_extraction(self):
        """Validates request body schema is extracted from POST."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)
        post_ep = [ep for ep in result["endpoints"] if ep["method"] == "POST"][0]

        assert post_ep["request_body"] is not None
        assert post_ep["request_body"]["type"] == "object"

    def test_response_schema_extraction(self):
        """Validates response schemas are extracted by status code."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)
        post_ep = [ep for ep in result["endpoints"] if ep["method"] == "POST"][0]

        assert "201" in post_ep["response_schemas"]
        assert post_ep["response_schemas"]["201"]["type"] == "object"

    def test_path_params_inherited(self):
        """Path-level parameters are inherited by operations."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)
        get_user = [ep for ep in result["endpoints"] if ep["path"] == "/users/{id}"][0]

        assert len(get_user["parameters"]) == 1
        assert get_user["parameters"][0]["name"] == "id"
        assert get_user["parameters"][0]["in"] == "path"
        assert get_user["parameters"][0]["required"] is True


# ── Tests: Auth extraction ──────────────────────────────────────────────────


class TestAuthExtraction:
    def test_bearer_auth(self):
        """Validates bearer auth extraction from securitySchemes."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)

        assert result["auth"]["type"] == "bearer"
        assert result["auth"]["scheme"] == "bearer"
        assert result["auth"]["in"] == "header"
        assert result["auth"]["name"] == "Authorization"

    def test_api_key_auth(self):
        """Validates API key auth extraction from securitySchemes."""
        result = parse_openapi_spec(API_KEY_AUTH_JSON)

        assert result["auth"]["type"] == "api_key"
        assert result["auth"]["scheme"] is None
        assert result["auth"]["in"] == "header"
        assert result["auth"]["name"] == "X-API-Key"

    def test_no_auth(self):
        """Validates fallback when no securitySchemes present."""
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)

        assert result["auth"]["type"] is None
        assert result["auth"]["scheme"] is None

    def test_auth_required_flag_with_global_security(self):
        """Endpoints inherit global security → auth_required=True."""
        result = parse_openapi_spec(MULTI_ENDPOINT_JSON)
        for ep in result["endpoints"]:
            assert ep["auth_required"] is True

    def test_auth_required_flag_without_security(self):
        """Endpoints without security → auth_required=False."""
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)
        for ep in result["endpoints"]:
            assert ep["auth_required"] is False


# ── Tests: Error handling ───────────────────────────────────────────────────


class TestErrorHandling:
    def test_malformed_json(self):
        """AC 3: Malformed input raises ValueError with descriptive message."""
        with pytest.raises(ValueError, match="Could not parse file as JSON or YAML"):
            parse_openapi_spec("{not valid json or yaml !!!")

    def test_plain_text(self):
        """AC 3: Plain text raises ValueError."""
        with pytest.raises(ValueError, match="not a valid OpenAPI spec"):
            parse_openapi_spec("just some plain text")

    def test_missing_openapi_field(self):
        """AC 3: Missing 'openapi' field raises ValueError."""
        spec = json.dumps({"info": {"title": "Test", "version": "1.0.0"}, "paths": {}})
        with pytest.raises(ValueError, match="missing 'openapi' version field"):
            parse_openapi_spec(spec)

    def test_missing_paths_key(self):
        """AC 3: Missing 'paths' key raises ValueError."""
        spec = json.dumps(
            {"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0.0"}}
        )
        with pytest.raises(ValueError, match="no 'paths'"):
            parse_openapi_spec(spec)

    def test_non_3x_version(self):
        """AC 3: Non-3.x version raises ValueError."""
        spec = json.dumps(
            {
                "openapi": "2.0",
                "info": {"title": "Test", "version": "1.0.0"},
                "paths": {},
            }
        )
        with pytest.raises(ValueError, match="Only OpenAPI 3.x is supported"):
            parse_openapi_spec(spec)

    def test_empty_string(self):
        """AC 3: Empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_openapi_spec("")

    def test_yaml_non_mapping(self):
        """AC 3: YAML that parses to a list, not dict, raises ValueError."""
        with pytest.raises(ValueError, match="not a valid OpenAPI spec"):
            parse_openapi_spec("- item1\n- item2\n- item3")


# ── Tests: Canonical schema compliance ──────────────────────────────────────


class TestCanonicalSchema:
    """Verify output matches the parsed_api_model canonical schema exactly."""

    def test_top_level_keys(self):
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)
        assert set(result.keys()) == {"endpoints", "auth", "title", "version"}

    def test_endpoint_keys(self):
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)
        ep = result["endpoints"][0]
        expected_keys = {
            "path",
            "method",
            "operation_id",
            "summary",
            "parameters",
            "request_body",
            "response_schemas",
            "auth_required",
            "tags",
        }
        assert set(ep.keys()) == expected_keys

    def test_parameter_keys(self):
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)
        param = result["endpoints"][0]["parameters"][0]
        expected_keys = {"name", "in", "required", "schema", "description"}
        assert set(param.keys()) == expected_keys

    def test_auth_keys(self):
        result = parse_openapi_spec(MINIMAL_OPENAPI_JSON)
        expected_keys = {"type", "scheme", "in", "name"}
        assert set(result["auth"].keys()) == expected_keys
