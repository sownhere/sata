"""Tests for deterministic spec gap detection heuristics."""

import json

from src.tools.gap_detector import detect_spec_gaps
from src.tools.spec_parser import parse_openapi_spec

GAP_SPEC_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Gap API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "summary": "Create user",
                    "security": [],
                    "responses": {"201": {"description": ""}},
                }
            },
            "/public-info": {
                "get": {
                    "summary": "Public info",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "404": {"description": "Not Found"},
                    },
                }
            },
            "/admin": {
                "get": {
                    "summary": "Admin info",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {"mysteryAuth": {"type": "http", "scheme": "digest"}}
        },
        "security": [{"mysteryAuth": []}],
    }
)

NO_GAP_SPEC_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "No Gap API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "summary": "Create user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"email": {"type": "string"}},
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "string"}},
                                    }
                                }
                            },
                        },
                        "400": {"description": "Bad Request"},
                    },
                    "security": [],
                }
            }
        },
    }
)


def test_detects_representative_gaps_with_stable_ids():
    parsed_model = parse_openapi_spec(GAP_SPEC_JSON)

    gaps = detect_spec_gaps(GAP_SPEC_JSON, parsed_model)

    gap_ids = {gap["id"] for gap in gaps}
    assert gap_ids == {
        "post-users-missing-success-response",
        "post-users-missing-request-body",
        "post-users-missing-error-responses",
        "get-admin-auth-ambiguity",
    }

    auth_gap = next(gap for gap in gaps if gap["id"] == "get-admin-auth-ambiguity")
    assert auth_gap["endpoint_key"] == "GET /admin"
    assert auth_gap["input_type"] == "select"
    assert auth_gap["options"] == [
        "bearer",
        "basic",
        "api_key",
        "oauth2",
        "openIdConnect",
        "none",
    ]


def test_explicitly_public_endpoint_does_not_raise_auth_gap():
    parsed_model = parse_openapi_spec(GAP_SPEC_JSON)

    gaps = detect_spec_gaps(GAP_SPEC_JSON, parsed_model)

    assert all(gap["endpoint_key"] != "GET /public-info" for gap in gaps)


def test_no_actionable_gaps_returns_empty_list():
    parsed_model = parse_openapi_spec(NO_GAP_SPEC_JSON)

    gaps = detect_spec_gaps(NO_GAP_SPEC_JSON, parsed_model)

    assert gaps == []


def test_documented_no_content_success_response_is_not_flagged_as_missing():
    raw_spec = json.dumps(
        {
            "openapi": "3.0.0",
            "info": {"title": "No Content API", "version": "1.0.0"},
            "paths": {
                "/health": {
                    "delete": {
                        "responses": {
                            "204": {"description": "No Content"},
                            "400": {"description": "Bad Request"},
                        },
                        "security": [],
                    }
                }
            },
        }
    )

    parsed_model = parse_openapi_spec(raw_spec)
    gaps = detect_spec_gaps(raw_spec, parsed_model)

    assert all(gap["gap_type"] != "missing_success_response" for gap in gaps)
