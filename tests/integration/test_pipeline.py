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
from src.nodes.generate_tests import generate_tests
from src.nodes.review_spec import prepare_rejection_for_reparse, review_spec
from src.nodes.review_test_plan import (
    prepare_rejection_for_test_regeneration,
    review_test_plan,
)

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


def test_record_route_transition_from_review_spec_uses_confirmation_state():
    confirmed_state = initial_state()
    confirmed_state["spec_confirmed"] = True

    confirmed_target = record_route_transition(confirmed_state, "review_spec")

    rejected_state = initial_state()
    rejected_state["spec_confirmed"] = False

    rejected_target = record_route_transition(rejected_state, "review_spec")

    assert confirmed_target == "generate_tests"
    assert rejected_target == "ingest_spec"


def test_generate_tests_populates_state_for_confirmed_spec(monkeypatch):
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
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
    }

    generated_cases = [
        {
            "id": "tc-get-users-happy-path-1",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "GET /users happy path",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]

    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "generate_test_cases_for_model",
        lambda parsed_model: {
            "test_cases": generated_cases,
            "failed_endpoints": [],
            "category_counts": {"happy_path": 1},
            "priority_counts": {"P1": 1},
        },
    )
    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "filter_test_cases_against_confirmed_spec",
        lambda test_cases, parsed_model: {"accepted": test_cases, "dropped": []},
    )

    result = generate_tests(state)

    assert result is state
    assert result["pipeline_stage"] == "generate_tests"
    assert result["test_cases"] == generated_cases
    assert result["error_message"] is None
    assert result["spec_confirmed"] is True
    assert result["test_plan_confirmed"] is False


def test_generate_tests_handles_partial_failures_after_retry(monkeypatch):
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [
            {"path": "/users", "method": "GET"},
            {"path": "/orders", "method": "POST"},
        ],
    }

    partial_cases = [
        {
            "id": "tc-get-users-happy-path-1",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "GET /users happy path",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]

    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "generate_test_cases_for_model",
        lambda parsed_model: {
            "test_cases": partial_cases,
            "failed_endpoints": [
                {
                    "path": "/orders",
                    "method": "POST",
                    "error": "timeout after retry",
                }
            ],
            "category_counts": {"happy_path": 1},
            "priority_counts": {"P1": 1},
        },
    )
    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "filter_test_cases_against_confirmed_spec",
        lambda test_cases, parsed_model: {
            "accepted": test_cases,
            "dropped": [{"reason": "unknown_endpoint", "test_case": {"id": "x"}}],
        },
    )

    result = generate_tests(state)

    assert result["pipeline_stage"] == "generate_tests"
    assert result["test_cases"] == partial_cases
    assert result["spec_confirmed"] is True
    assert result["test_plan_confirmed"] is False
    assert result["error_message"].startswith("Partial generation:")
    assert "1 endpoint(s) failed" in result["error_message"]


def test_generate_tests_preserves_previous_cases_when_generation_fails(monkeypatch):
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }
    state["test_cases"] = [
        {
            "id": "tc-previous",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "Previous case",
            "description": "Old but valid",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]

    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "generate_test_cases_for_model",
        lambda parsed_model: {
            "test_cases": [],
            "failed_endpoints": [
                {"path": "/users", "method": "GET", "error": "timeout after retry"}
            ],
            "category_counts": {},
            "priority_counts": {},
        },
    )
    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "filter_test_cases_against_confirmed_spec",
        lambda test_cases, parsed_model: {"accepted": [], "dropped": []},
    )

    result = generate_tests(state)

    assert result["test_cases"] == [
        {
            "id": "tc-previous",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "Previous case",
            "description": "Old but valid",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]
    assert result["error_message"].startswith("Partial generation:")


def test_generate_tests_preserves_previous_when_new_run_all_filtered(monkeypatch):
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }
    previous = [
        {
            "id": "tc-previous",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "Previous case",
            "description": "Old but valid",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]
    state["test_cases"] = list(previous)

    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "generate_test_cases_for_model",
        lambda parsed_model: {
            "test_cases": [{"id": "bad", "endpoint_path": "/nope"}],
            "failed_endpoints": [],
            "category_counts": {},
            "priority_counts": {},
        },
    )
    monkeypatch.setattr(
        sys.modules["src.nodes.generate_tests"],
        "filter_test_cases_against_confirmed_spec",
        lambda test_cases, parsed_model: {
            "accepted": [],
            "dropped": [{"reason": "invalid_test_case_shape"}],
        },
    )

    result = generate_tests(state)

    assert result["test_cases"] == previous
    assert result["error_message"].startswith(
        "Regeneration produced no valid test cases"
    )
    assert "discarded" in result["error_message"]


def test_generate_tests_requires_spec_confirmation():
    state = initial_state()
    state["spec_confirmed"] = False
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }

    result = generate_tests(state)

    assert result["pipeline_stage"] == "review_spec"
    assert "Confirm the API spec" in result["error_message"]
    assert result["test_plan_confirmed"] is False


def test_generate_tests_handles_missing_endpoints_gracefully():
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [],
    }

    result = generate_tests(state)

    assert result["pipeline_stage"] == "spec_ingestion"
    assert "no confirmed endpoints" in result["error_message"].lower()
    assert result["test_plan_confirmed"] is False


def test_review_test_plan_initializes_generated_cases_and_stage():
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "generate_tests"
    state["test_cases"] = [
        {
            "id": "tc-happy",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]

    result = review_test_plan(state)

    assert result is state
    assert result["pipeline_stage"] == "review_test_plan"
    assert result["spec_confirmed"] is True
    assert result["test_plan_confirmed"] is False
    assert result["generated_test_cases"] == result["test_cases"]
    assert result["disabled_test_categories"] == []


def test_review_test_plan_disables_categories_from_execution_plan():
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_test_plan"
    state["generated_test_cases"] = [
        {
            "id": "tc-happy",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        },
        {
            "id": "tc-boundary",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P2",
            "title": "Delete user",
            "description": "Deletes one user",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": ["id"],
        },
    ]
    state["disabled_test_categories"] = ["boundary"]
    state["test_cases"] = list(state["generated_test_cases"])

    result = review_test_plan(state)

    assert result["pipeline_stage"] == "review_test_plan"
    assert [case["id"] for case in result["test_cases"]] == ["tc-happy"]
    assert [case["id"] for case in result["generated_test_cases"]] == [
        "tc-happy",
        "tc-boundary",
    ]
    assert result["disabled_test_categories"] == ["boundary"]


def test_review_test_plan_restores_cases_when_category_reenabled():
    state = initial_state()
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_test_plan"
    state["generated_test_cases"] = [
        {
            "id": "tc-happy",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        },
        {
            "id": "tc-boundary",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P2",
            "title": "Delete user",
            "description": "Deletes one user",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": ["id"],
        },
    ]
    state["disabled_test_categories"] = []
    state["test_cases"] = [
        {
            "id": "tc-happy",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]

    result = review_test_plan(state)

    assert [case["id"] for case in result["test_cases"]] == [
        "tc-happy",
        "tc-boundary",
    ]


def test_prepare_rejection_for_test_regeneration_clears_test_plan_state():
    state = initial_state()
    state["spec_confirmed"] = True
    state["parsed_api_model"] = {"title": "Test API", "endpoints": [{"path": "/x"}]}
    state["gap_answers"] = {"gap-1": "answer"}
    state["pipeline_stage"] = "review_test_plan"
    state["generated_test_cases"] = [{"id": "tc-1"}]
    state["disabled_test_categories"] = ["boundary"]
    state["test_cases"] = [{"id": "tc-1"}]
    state["test_plan_confirmed"] = False
    state["error_message"] = "some prior error"

    result = prepare_rejection_for_test_regeneration(state)

    assert result is state
    assert result["generated_test_cases"] is None
    assert result["disabled_test_categories"] is None
    assert result["test_cases"] is None
    assert result["test_plan_confirmed"] is False
    assert result["pipeline_stage"] == "generate_tests"
    assert result["error_message"] is None


def test_prepare_rejection_for_test_regeneration_preserves_spec_state():
    state = initial_state()
    state["spec_confirmed"] = True
    state["raw_spec"] = "openapi: 3.0.0"
    state["spec_source"] = "upload"
    state["parsed_api_model"] = {"title": "Test API", "endpoints": [{"path": "/x"}]}
    state["detected_gaps"] = [{"id": "gap-1"}]
    state["gap_answers"] = {"gap-1": "answer"}
    state["generated_test_cases"] = [{"id": "tc-1"}]
    state["test_cases"] = [{"id": "tc-1"}]

    result = prepare_rejection_for_test_regeneration(state)

    assert result["spec_confirmed"] is True
    assert result["raw_spec"] == "openapi: 3.0.0"
    assert result["spec_source"] == "upload"
    assert result["parsed_api_model"] == {
        "title": "Test API",
        "endpoints": [{"path": "/x"}],
    }
    assert result["detected_gaps"] == [{"id": "gap-1"}]
    assert result["gap_answers"] == {"gap-1": "answer"}


def test_prepare_rejection_for_reparse_preserves_raw_spec_and_clears_review_state():
    state = initial_state()
    state["spec_source"] = "url"
    state["raw_spec"] = "openapi: 3.0.0"
    state["spec_confirmed"] = True
    state["pipeline_stage"] = "review_spec"
    state["parsed_api_model"] = {"title": "Users API", "endpoints": [{"path": "/x"}]}
    state["detected_gaps"] = [{"id": "gap-1"}]
    state["gap_answers"] = {"gap-1": "answer"}
    state["test_cases"] = [{"id": "should-stay-untouched"}]

    result = prepare_rejection_for_reparse(state)

    assert result is state
    assert result["spec_source"] == "url"
    assert result["raw_spec"] == "openapi: 3.0.0"
    assert result["pipeline_stage"] == "spec_ingestion"
    assert result["spec_confirmed"] is False
    assert result["parsed_api_model"] is None
    assert result["detected_gaps"] is None
    assert result["gap_answers"] is None
    assert result["test_cases"] == [{"id": "should-stay-untouched"}]


def test_execute_tests_requires_test_plan_confirmed():
    from src.nodes.execute_tests import execute_tests

    state = initial_state()
    state["test_plan_confirmed"] = False
    state["target_api_url"] = "https://api.example.com"
    state["test_cases"] = [{"id": "tc-1"}]

    result = execute_tests(state)

    assert result["pipeline_stage"] == "execute_tests"
    assert result["error_message"] is not None
    assert result["test_results"] is None


def test_execute_tests_requires_target_api_url():
    from src.nodes.execute_tests import execute_tests

    state = initial_state()
    state["test_plan_confirmed"] = True
    state["target_api_url"] = None
    state["test_cases"] = [{"id": "tc-1"}]

    result = execute_tests(state)

    assert result["pipeline_stage"] == "execute_tests"
    assert result["error_message"] is not None
    assert "URL" in result["error_message"]


def test_execute_tests_populates_test_results():
    import importlib
    from unittest.mock import patch

    execute_tests_module = importlib.import_module("src.nodes.execute_tests")
    from src.nodes.execute_tests import execute_tests

    fake_result = {
        "test_id": "tc-1",
        "test_title": "Get users",
        "endpoint_method": "GET",
        "endpoint_path": "/users",
        "actual_status_code": 200,
        "actual_response_body": {"users": []},
        "error_message": None,
        "attempt_count": 1,
    }

    state = initial_state()
    state["test_plan_confirmed"] = True
    state["target_api_url"] = "https://api.example.com"
    state["test_cases"] = [
        {
            "id": "tc-1",
            "title": "Get users",
            "endpoint_method": "GET",
            "endpoint_path": "/users",
        }
    ]

    with patch.object(
        execute_tests_module, "execute_single_test", return_value=fake_result
    ):
        result = execute_tests(state)

    assert result["test_results"] is not None
    assert len(result["test_results"]) == 1
    assert result["test_results"][0]["test_id"] == "tc-1"
    assert result["test_results"][0]["actual_status_code"] == 200
    assert "passed" in result["test_results"][0]
    assert "validation_errors" in result["test_results"][0]
    assert result["error_message"] is None
    assert result["pipeline_stage"] == "execute_tests"


def test_execute_tests_results_have_passed_field():
    import importlib
    from unittest.mock import patch

    execute_tests_module = importlib.import_module("src.nodes.execute_tests")
    from src.nodes.execute_tests import execute_tests

    fake_result = {
        "test_id": "tc-1",
        "test_title": "Get users",
        "endpoint_method": "GET",
        "endpoint_path": "/users",
        "actual_status_code": 200,
        "actual_response_body": {"users": []},
        "error_message": None,
        "attempt_count": 1,
    }

    state = initial_state()
    state["test_plan_confirmed"] = True
    state["target_api_url"] = "https://api.example.com"
    state["test_cases"] = [
        {
            "id": "tc-1",
            "title": "Get users",
            "endpoint_method": "GET",
            "endpoint_path": "/users",
            "expected": {"status_code": 200},
        }
    ]

    with patch.object(
        execute_tests_module, "execute_single_test", return_value=fake_result
    ):
        result = execute_tests(state)

    res = result["test_results"][0]
    assert res["passed"] is True
    assert res["expected_status_code"] == 200
    assert res["validation_errors"] == []


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

    assert result["pipeline_stage"] == "review_spec"
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


def test_fill_gaps_updates_parsed_api_model_for_missing_success_response_answer():
    """AC3: fill_gaps must persist a missing_success_response answer into
    parsed_api_model so downstream nodes see the user-provided schema."""
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
                "auth_required": False,
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
            "field": "response_schemas.2xx",
            "question": "What does a successful response return?",
            "input_type": "text_area",
            "options": None,
        }
    ]
    state["gap_answers"] = {
        "post-users-missing-success-response": "Returns the created user object."
    }
    state["pipeline_stage"] = "fill_gaps"

    result = fill_gaps(state)

    assert result["pipeline_stage"] == "review_spec"
    assert result["detected_gaps"] == []
    endpoint = result["parsed_api_model"]["endpoints"][0]
    assert endpoint["response_schemas"]["200"] == "Returns the created user object."


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


def test_analyze_results_requires_test_results():
    from src.nodes.analyze_results import analyze_results

    state = initial_state()
    state["test_results"] = None

    result = analyze_results(state)

    assert result["error_message"] is not None
    assert result["pipeline_stage"] == "execute_tests"
    assert result["failure_analysis"] is None


def test_analyze_results_populates_failure_analysis():
    import importlib
    from unittest.mock import patch

    analyze_results_module = importlib.import_module("src.nodes.analyze_results")
    from src.nodes.analyze_results import analyze_results

    fake_analysis = {
        "patterns": [
            {
                "pattern_type": "status_mismatch",
                "severity": "High",
                "count": 1,
                "description": "404 on GET /users",
                "affected_test_ids": ["tc-1"],
            }
        ],
        "explanations": [
            {
                "test_id": "tc-1",
                "what_broke": "404",
                "why_it_matters": "x",
                "how_to_fix": "y",
            }
        ],
        "all_passed": False,
    }

    state = initial_state()
    state["test_results"] = [
        {
            "test_id": "tc-1",
            "passed": False,
            "actual_status_code": 404,
            "expected_status_code": 200,
            "validation_errors": ["Expected 200, got 404"],
        }
    ]

    with patch.object(
        analyze_results_module, "analyze_failures", return_value=fake_analysis
    ):
        result = analyze_results(state)

    assert result["failure_analysis"] is not None
    assert result["failure_analysis"]["all_passed"] is False
    assert result["failure_analysis"]["all_failed"] is True
    assert result["pipeline_stage"] == "review_results"
    assert result["error_message"] is None
    assert len(result["reasoning_log"]) >= 2


def test_analyze_results_all_passed_sets_flag():
    import importlib
    from unittest.mock import patch

    analyze_results_module = importlib.import_module("src.nodes.analyze_results")
    from src.nodes.analyze_results import analyze_results

    fake_analysis = {"patterns": [], "explanations": [], "all_passed": True}

    state = initial_state()
    state["test_results"] = [
        {
            "test_id": "tc-1",
            "passed": True,
            "actual_status_code": 200,
            "expected_status_code": 200,
            "validation_errors": [],
        }
    ]

    with patch.object(
        analyze_results_module, "analyze_failures", return_value=fake_analysis
    ):
        result = analyze_results(state)

    assert result["failure_analysis"]["all_passed"] is True
    assert result["failure_analysis"]["all_failed"] is False
    assert result["failure_analysis"]["next_test_suggestions"]
    assert result["pipeline_stage"] == "review_results"


def test_analyze_results_all_failed_attaches_smart_diagnosis():
    import importlib
    from unittest.mock import patch

    analyze_results_module = importlib.import_module("src.nodes.analyze_results")
    from src.nodes.analyze_results import analyze_results

    state = initial_state()
    state["parsed_api_model"] = {
        "auth": {"type": "bearer", "scheme": "Bearer", "in": "header"},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }
    state["test_results"] = [
        {
            "test_id": "tc-1",
            "passed": False,
            "actual_status_code": 401,
            "expected_status_code": 200,
            "validation_errors": ["Unauthorized"],
            "error_message": None,
        }
    ]

    with patch.object(
        analyze_results_module,
        "analyze_failures",
        return_value={
            "patterns": [],
            "explanations": [],
            "all_passed": False,
        },
    ):
        result = analyze_results(state)

    assert result["failure_analysis"]["all_failed"] is True
    assert (
        result["failure_analysis"]["smart_diagnosis"]["category"]
        == "auth_misconfiguration"
    )
    assert result["pipeline_stage"] == "review_results"


def test_demo_mode_sample_still_requires_manual_checkpoints():
    from src.nodes.parse_spec import parse_spec
    from src.tools.demo_catalog import get_demo_sample

    state = initial_state()
    state["spec_source"] = "demo"
    state["raw_spec"] = get_demo_sample("petstore")["raw_spec"]

    result = parse_spec(state)

    assert result["pipeline_stage"] == "spec_parsed"
    assert result["spec_confirmed"] is False
    assert result["test_plan_confirmed"] is False
