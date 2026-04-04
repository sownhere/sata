"""Tests for LangGraph pipeline behavior and graph wiring."""

import sys

from src.core.graph import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    _route_after_ingest,
    _route_after_parse,
    build_pipeline,
    record_route_transition,
    run_pipeline_node,
)
from src.core.state import initial_state
from src.nodes.detect_gaps import detect_gaps
from src.nodes.fill_gaps import fill_gaps
from src.nodes.review_spec import review_spec

EXPECTED_NODES = [
    "ingest_spec",
    "parse_spec",
    "detect_gaps",
    "fill_gaps",
    "review_spec",
    "generate_tests",
    "review_test_plan",
    "execute_tests",
    "analyze_results",
    "review_results",
]


def test_build_pipeline_returns_non_none():
    graph = build_pipeline()
    assert graph is not None


def test_pipeline_has_8_or_more_nodes():
    graph = build_pipeline()
    nodes = graph.get_graph().nodes
    # Exclude LangGraph's internal __start__ and __end__ nodes
    user_nodes = [n for n in nodes if not n.startswith("__")]
    assert len(user_nodes) >= 8, (
        f"Expected 8+ nodes, got {len(user_nodes)}: {user_nodes}"
    )


def test_pipeline_contains_all_expected_nodes():
    graph = build_pipeline()
    nodes = graph.get_graph().nodes
    for node_name in EXPECTED_NODES:
        assert node_name in nodes, f"Missing expected node: {node_name}"


def test_pipeline_has_entry_point():
    graph = build_pipeline()
    drawable = graph.get_graph()
    # Entry point maps to the first node
    assert "ingest_spec" in drawable.nodes


def test_pipeline_route_labels_cover_every_conditional_edge():
    graph = build_pipeline()
    conditional_edges = {
        (edge.source, edge.target)
        for edge in graph.get_graph().edges
        if edge.conditional
    }

    assert conditional_edges == set(CONDITIONAL_EDGE_LABELS)


def test_pipeline_route_labels_cover_every_linear_edge():
    graph = build_pipeline()
    linear_edges = {
        (edge.source, edge.target)
        for edge in graph.get_graph().edges
        if not edge.conditional
        and not edge.source.startswith("__")
        and not edge.target.startswith("__")
    }

    assert linear_edges == set(LINEAR_EDGE_LABELS)


def test_run_pipeline_node_marks_active_and_completed_state():
    state = initial_state()

    result = run_pipeline_node(
        state,
        "ingest_spec",
        handler=lambda current_state: current_state,
    )

    assert result is state
    assert state["active_node"] == "ingest_spec"
    assert state["completed_nodes"] == ["ingest_spec"]


def test_record_route_transition_sets_taken_edge_and_next_active_node():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }

    next_node = record_route_transition(state, "parse_spec")

    assert next_node == "detect_gaps"
    assert state["active_node"] == "detect_gaps"
    assert state["taken_edges"] == [{"source": "parse_spec", "target": "detect_gaps"}]


def test_detect_gaps_routes_to_fill_gaps_when_gaps_exist():
    state = initial_state()
    state["raw_spec"] = """
openapi: "3.0.0"
info:
  title: Gap API
  version: "1.0.0"
paths:
  /users:
    post:
      responses:
        "201":
          description: Created
components:
  securitySchemes:
    mysteryAuth:
      type: http
      scheme: digest
security:
  - mysteryAuth: []
"""
    state["parsed_api_model"] = {
        "title": "Gap API",
        "version": "1.0.0",
        "auth": {
            "type": "basic",
            "scheme": "digest",
            "in": "header",
            "name": "Authorization",
        },
        "endpoints": [
            {
                "path": "/users",
                "method": "POST",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": None,
                "response_schemas": {"201": "Created"},
                "auth_required": True,
                "tags": [],
            }
        ],
    }
    state["pipeline_stage"] = "spec_parsed"

    result = detect_gaps(state)

    assert result is state
    assert result["pipeline_stage"] == "fill_gaps"
    assert result["detected_gaps"]
    assert result["error_message"] is None


def test_detect_gaps_routes_to_review_spec_when_no_gaps_exist():
    state = initial_state()
    state["raw_spec"] = """
openapi: "3.0.0"
info:
  title: Complete API
  version: "1.0.0"
paths:
  /users:
    post:
      security: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema:
                type: object
        "400":
          description: Bad Request
"""
    state["parsed_api_model"] = {
        "title": "Complete API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/users",
                "method": "POST",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": {"type": "object"},
                "response_schemas": {"201": {"type": "object"}, "400": "Bad Request"},
                "auth_required": False,
                "tags": [],
            }
        ],
    }
    state["pipeline_stage"] = "spec_parsed"

    result = detect_gaps(state)

    assert result["pipeline_stage"] == "review_spec"
    assert result["detected_gaps"] == []
    assert result["error_message"] is None


def test_fill_gaps_removes_answered_gaps_and_preserves_unanswered():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Gap API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/users",
                "method": "POST",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": None,
                "response_schemas": {},
                "auth_required": True,
                "tags": [],
            }
        ],
    }
    state["detected_gaps"] = [
        {
            "id": "post-users-missing-success-response",
            "endpoint_key": "POST /users",
            "path": "/users",
            "method": "POST",
            "gap_type": "missing_success_response",
            "field": "response_schemas.201",
            "question": "What does a 201 response return?",
            "input_type": "text_area",
            "options": None,
        },
        {
            "id": "post-users-auth-ambiguity",
            "endpoint_key": "POST /users",
            "path": "/users",
            "method": "POST",
            "gap_type": "auth_ambiguity",
            "field": "auth.type",
            "question": "Which auth type does this endpoint use?",
            "input_type": "select",
            "options": ["bearer", "none"],
        },
    ]
    state["gap_answers"] = {
        "post-users-missing-success-response": "Returns the created user.",
    }
    state["pipeline_stage"] = "fill_gaps"

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "fill_gaps"
    assert (
        result["gap_answers"]["post-users-missing-success-response"]
        == "Returns the created user."
    )
    assert [gap["id"] for gap in result["detected_gaps"]] == [
        "post-users-auth-ambiguity"
    ]


def test_fill_gaps_updates_state_for_deterministic_auth_answers():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Gap API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/admin",
                "method": "GET",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": None,
                "response_schemas": {"200": {"type": "object"}},
                "auth_required": True,
                "tags": [],
            }
        ],
    }
    state["detected_gaps"] = [
        {
            "id": "get-admin-auth-ambiguity",
            "endpoint_key": "GET /admin",
            "path": "/admin",
            "method": "GET",
            "gap_type": "auth_ambiguity",
            "field": "auth.type",
            "question": "Which auth type does this endpoint use?",
            "input_type": "select",
            "options": [
                "bearer",
                "basic",
                "api_key",
                "oauth2",
                "openIdConnect",
                "none",
            ],
        }
    ]
    state["gap_answers"] = {"get-admin-auth-ambiguity": "bearer"}
    state["pipeline_stage"] = "fill_gaps"

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "review_spec"
    assert result["detected_gaps"] == []
    assert result["parsed_api_model"]["auth"]["type"] == "bearer"
    assert result["parsed_api_model"]["auth"]["scheme"] == "Bearer"
    assert result["parsed_api_model"]["auth"]["in"] == "header"
    assert result["parsed_api_model"]["auth"]["name"] == "Authorization"


def test_fill_gaps_does_not_overwrite_global_auth_for_mixed_endpoint_auth():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Mixed Auth API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {
                "path": "/admin",
                "method": "GET",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": None,
                "response_schemas": {"200": {"type": "object"}},
                "auth_required": True,
                "tags": [],
            },
            {
                "path": "/reports",
                "method": "GET",
                "operation_id": None,
                "summary": None,
                "parameters": [],
                "request_body": None,
                "response_schemas": {"200": {"type": "object"}},
                "auth_required": True,
                "tags": [],
            },
        ],
    }
    state["detected_gaps"] = [
        {
            "id": "get-admin-auth-ambiguity",
            "endpoint_key": "GET /admin",
            "path": "/admin",
            "method": "GET",
            "gap_type": "auth_ambiguity",
            "field": "auth.type",
            "question": "Which auth type does this endpoint use?",
            "input_type": "select",
            "options": [
                "bearer",
                "basic",
                "api_key",
                "oauth2",
                "openIdConnect",
                "none",
            ],
        }
    ]
    state["gap_answers"] = {"get-admin-auth-ambiguity": "bearer"}
    state["pipeline_stage"] = "fill_gaps"

    result = fill_gaps(state)

    assert result["parsed_api_model"]["auth"] == {
        "type": None,
        "scheme": None,
        "in": None,
        "name": None,
    }
    assert result["parsed_api_model"]["endpoints"][0]["auth_required"] is True
    assert result["parsed_api_model"]["endpoints"][1]["auth_required"] is True


def test_detect_gaps_handles_missing_context_gracefully():
    state = initial_state()
    state["pipeline_stage"] = "spec_parsed"
    state["parsed_api_model"] = None

    result = detect_gaps(state)

    assert result["pipeline_stage"] == "spec_ingestion"
    assert result["detected_gaps"] is None
    assert result["error_message"] == "Cannot detect gaps before a spec is parsed."


def test_route_after_ingest_uses_fill_gaps_for_manual_chat_mode():
    state = initial_state()
    state["spec_source"] = "chat"

    assert _route_after_ingest(state) == "fill_gaps"


def test_route_after_ingest_uses_parse_for_non_chat_sources():
    for source in ("file", "url", None):
        state = initial_state()
        state["spec_source"] = source

        assert _route_after_ingest(state) == "parse_spec"


def test_route_after_parse_uses_fill_gaps_for_zero_endpoint_models():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Empty API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [],
    }

    assert _route_after_parse(state) == "fill_gaps"


def test_route_after_parse_uses_detect_gaps_for_non_empty_models():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }

    assert _route_after_parse(state) == "detect_gaps"


def test_route_after_parse_does_not_turn_parse_errors_into_fallback():
    state = initial_state()
    state["parsed_api_model"] = None
    state["error_message"] = "Not an OpenAPI spec"

    assert _route_after_parse(state) == "detect_gaps"


def test_fill_gaps_extracts_api_model_for_manual_conversation(monkeypatch):
    state = initial_state()
    state["spec_source"] = "chat"
    state["conversation_messages"] = [
        {"role": "assistant", "content": "Describe your API."},
        {"role": "user", "content": "I have GET /users that returns 200."},
    ]
    state["pipeline_stage"] = "fill_gaps"

    monkeypatch.setattr(
        sys.modules["src.nodes.fill_gaps"],
        "extract_api_model_from_conversation",
        lambda messages: {
            "status": "complete",
            "api_model": {
                "title": "Users API",
                "version": "unknown",
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
            },
        },
    )

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "spec_parsed"
    assert result["parsed_api_model"]["title"] == "Users API"
    assert result["conversation_question"] is None


def test_fill_gaps_records_follow_up_question_for_manual_conversation(monkeypatch):
    state = initial_state()
    state["spec_source"] = "chat"
    state["conversation_messages"] = [
        {"role": "assistant", "content": "Describe your API."},
        {"role": "user", "content": "I have POST /users."},
    ]
    state["pipeline_stage"] = "fill_gaps"

    monkeypatch.setattr(
        sys.modules["src.nodes.fill_gaps"],
        "extract_api_model_from_conversation",
        lambda messages: {
            "status": "needs_more_info",
            "question": "What does POST /users return on success?",
        },
    )

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "fill_gaps"
    assert result["conversation_question"] == "What does POST /users return on success?"
    assert result["parsed_api_model"] is None


def test_review_spec_is_not_a_passthrough_stub_for_empty_models():
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
    assert result["error_message"] is not None
