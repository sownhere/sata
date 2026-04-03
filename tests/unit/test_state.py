"""Tests for SataState TypedDict definition (AC: 2)."""

from src.core.state import SataState, initial_state


def test_sata_state_can_be_instantiated_with_defaults():
    state: SataState = {
        "spec_source": None,
        "raw_spec": None,
        "conversation_messages": None,
        "conversation_question": None,
        "parsed_api_model": None,
        "spec_confirmed": False,
        "detected_gaps": None,
        "gap_answers": None,
        "test_cases": None,
        "test_plan_confirmed": False,
        "test_results": None,
        "failure_analysis": None,
        "pipeline_stage": "spec_ingestion",
        "error_message": None,
        "iteration_count": 0,
        "active_node": None,
        "completed_nodes": [],
        "taken_edges": [],
        "selected_visual_node": None,
    }
    assert state["pipeline_stage"] == "spec_ingestion"
    assert state["spec_confirmed"] is False
    assert state["test_plan_confirmed"] is False
    assert state["iteration_count"] == 0


def test_sata_state_has_all_required_keys():
    required_keys = [
        "spec_source",
        "raw_spec",
        "conversation_messages",
        "conversation_question",
        "parsed_api_model",
        "spec_confirmed",
        "detected_gaps",
        "gap_answers",
        "test_cases",
        "test_plan_confirmed",
        "test_results",
        "failure_analysis",
        "pipeline_stage",
        "error_message",
        "iteration_count",
        "active_node",
        "completed_nodes",
        "taken_edges",
        "selected_visual_node",
    ]
    annotations = SataState.__annotations__
    for key in required_keys:
        assert key in annotations, f"SataState missing required field: {key}"


def test_sata_state_pipeline_stage_accepts_string():
    state: SataState = {
        "spec_source": None,
        "raw_spec": None,
        "conversation_messages": None,
        "conversation_question": None,
        "parsed_api_model": None,
        "spec_confirmed": False,
        "detected_gaps": None,
        "gap_answers": None,
        "test_cases": None,
        "test_plan_confirmed": False,
        "test_results": None,
        "failure_analysis": None,
        "pipeline_stage": "review_spec",
        "error_message": None,
        "iteration_count": 0,
        "active_node": None,
        "completed_nodes": [],
        "taken_edges": [],
        "selected_visual_node": None,
    }
    assert state["pipeline_stage"] == "review_spec"


def test_sata_state_iteration_count_is_integer():
    state: SataState = {
        "spec_source": None,
        "raw_spec": None,
        "conversation_messages": None,
        "conversation_question": None,
        "parsed_api_model": None,
        "spec_confirmed": False,
        "detected_gaps": None,
        "gap_answers": None,
        "test_cases": None,
        "test_plan_confirmed": False,
        "test_results": None,
        "failure_analysis": None,
        "pipeline_stage": "spec_ingestion",
        "error_message": None,
        "iteration_count": 5,
        "active_node": None,
        "completed_nodes": [],
        "taken_edges": [],
        "selected_visual_node": None,
    }
    assert isinstance(state["iteration_count"], int)
    assert state["iteration_count"] == 5


def test_initial_state_sets_visualization_defaults():
    state = initial_state()

    assert state["active_node"] is None
    assert state["completed_nodes"] == []
    assert state["taken_edges"] == []
    assert state["selected_visual_node"] is None
