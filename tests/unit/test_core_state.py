"""Unit tests for src.core.state — SataState TypedDict and initial_state()."""

from src.core.state import SataState, initial_state


def test_sata_state_importable_from_src_core():
    state: SataState = {
        "spec_source": None,
        "raw_spec": None,
        "conversation_messages": None,
        "conversation_question": None,
        "parsed_api_model": None,
        "spec_confirmed": False,
        "detected_gaps": None,
        "gap_answers": None,
        "generated_test_cases": None,
        "disabled_test_categories": None,
        "test_cases": None,
        "test_plan_confirmed": False,
        "target_api_url": None,
        "test_results": None,
        "failure_analysis": None,
        "generated_report": None,
        "pipeline_stage": "spec_ingestion",
        "error_message": None,
        "iteration_count": 0,
        "run_attempt": 0,
        "previous_run_summary": None,
        "run_history": [],
        "active_node": None,
        "completed_nodes": [],
        "taken_edges": [],
        "selected_visual_node": None,
        "selected_test_id": None,
        "results_filters": None,
        "scoped_run_selection": None,
        "reasoning_log": [],
        "demo_context": None,
    }
    assert state["pipeline_stage"] == "spec_ingestion"
    assert state["spec_confirmed"] is False


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
        "generated_test_cases",
        "disabled_test_categories",
        "test_cases",
        "test_plan_confirmed",
        "target_api_url",
        "test_results",
        "failure_analysis",
        "generated_report",
        "pipeline_stage",
        "error_message",
        "iteration_count",
        "run_attempt",
        "previous_run_summary",
        "run_history",
        "active_node",
        "completed_nodes",
        "taken_edges",
        "selected_visual_node",
        "selected_test_id",
        "results_filters",
        "scoped_run_selection",
        "reasoning_log",
        "demo_context",
    ]
    annotations = SataState.__annotations__
    for key in required_keys:
        assert key in annotations, f"SataState missing required field: {key}"


def test_initial_state_returns_correct_defaults():
    state = initial_state()
    assert state["pipeline_stage"] == "spec_ingestion"
    assert state["spec_confirmed"] is False
    assert state["generated_test_cases"] is None
    assert state["disabled_test_categories"] is None
    assert state["test_plan_confirmed"] is False
    assert state["iteration_count"] == 0
    assert state["generated_report"] is None
    assert state["run_attempt"] == 0
    assert state["previous_run_summary"] is None
    assert state["run_history"] == []
    assert state["active_node"] is None
    assert state["completed_nodes"] == []
    assert state["taken_edges"] == []
    assert state["selected_visual_node"] is None
    assert state["selected_test_id"] is None
    assert state["results_filters"] is None
    assert state["scoped_run_selection"] is None
    assert state["reasoning_log"] == []
    assert state["demo_context"] is None
    assert state["parsed_api_model"] is None
    assert state["target_api_url"] is None
    assert state["error_message"] is None
