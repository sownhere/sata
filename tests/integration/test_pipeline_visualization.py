"""Tests for Story 6.2 pipeline visualization helpers."""

from src.core.graph import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    record_route_transition,
    run_pipeline_node,
)
from src.core.state import initial_state
from src.ui.visualization import (
    build_pipeline_graph_dot,
    build_visualization_model,
    get_default_visual_node,
    get_node_detail,
)


def test_visualization_model_includes_all_expected_user_nodes():
    state = initial_state()

    model = build_visualization_model(state)
    node_ids = [node["id"] for node in model["nodes"]]

    assert node_ids == [
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


def test_visualization_model_labels_every_routed_edge():
    labeled_edges = {**CONDITIONAL_EDGE_LABELS, **LINEAR_EDGE_LABELS}

    assert labeled_edges[("ingest_spec", "parse_spec")] == "file or URL import"
    assert labeled_edges[("ingest_spec", "fill_gaps")] == "manual chat mode"
    assert labeled_edges[("parse_spec", "fill_gaps")] == "zero endpoints fallback"
    assert labeled_edges[("parse_spec", "detect_gaps")] == "endpoints found"
    assert labeled_edges[("detect_gaps", "review_spec")] == "no gaps"
    assert labeled_edges[("detect_gaps", "fill_gaps")] == "gaps detected"
    assert labeled_edges[("review_spec", "generate_tests")] == "confirmed"
    assert labeled_edges[("review_spec", "ingest_spec")] == "rejected"
    assert labeled_edges[("review_test_plan", "execute_tests")] == "approved"
    assert labeled_edges[("review_test_plan", "generate_tests")] == "revise plan"
    assert labeled_edges[("review_results", "analyze_results")] == "deeper analysis"
    assert labeled_edges[("fill_gaps", "review_spec")] == "clarifications complete"


def test_visualization_model_marks_active_completed_and_taken_path_states():
    state = initial_state()
    state["parsed_api_model"] = {
        "title": "Users API",
        "version": "1.0.0",
        "auth": {"type": None, "scheme": None, "in": None, "name": None},
        "endpoints": [{"path": "/users", "method": "GET"}],
    }
    state["raw_spec"] = "openapi: 3.0.0"

    run_pipeline_node(state, "parse_spec", handler=lambda current_state: current_state)
    next_node = record_route_transition(state, "parse_spec")
    assert next_node == "detect_gaps"
    state["completed_nodes"].append("detect_gaps")
    record_route_transition(state, "detect_gaps", target_override="review_spec")

    model = build_visualization_model(state)
    node_status = {node["id"]: node["status"] for node in model["nodes"]}
    edge_status = {
        (edge["source"], edge["target"]): edge["status"] for edge in model["edges"]
    }

    assert node_status["parse_spec"] == "completed"
    assert node_status["detect_gaps"] == "completed"
    assert node_status["review_spec"] == "active"
    assert node_status["generate_tests"] == "pending"
    assert edge_status[("parse_spec", "detect_gaps")] == "taken"
    assert edge_status[("detect_gaps", "review_spec")] == "taken"
    assert edge_status[("detect_gaps", "fill_gaps")] == "untaken"


def test_build_pipeline_graph_dot_contains_labels_and_tooltips():
    state = initial_state()
    dot = build_pipeline_graph_dot(state)

    assert "ingest_spec" in dot
    assert 'label="File or URL Import"' in dot
    assert 'tooltip="Entry point for file, URL, or chat-based spec intake."' in dot
    assert 'label="manual chat mode"' in dot
    assert 'label="clarifications complete"' in dot


def test_get_default_visual_node_prefers_active_node_then_stage():
    state = initial_state()
    state["pipeline_stage"] = "review_spec"
    assert get_default_visual_node(state) == "review_spec"

    state["active_node"] = "detect_gaps"
    assert get_default_visual_node(state) == "detect_gaps"


def test_get_node_detail_returns_role_metadata():
    detail = get_node_detail("execute_tests")

    assert detail["label"] == "Execute Tests"
    assert "auth" in detail["role"].lower()
