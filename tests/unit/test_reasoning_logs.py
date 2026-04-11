"""Unit tests for reasoning-log grouping and sanitization."""

from src.core.observability import append_reasoning_log
from src.core.state import initial_state
from src.ui.components import group_reasoning_events


def test_append_reasoning_log_sanitizes_secret_like_fields():
    state = initial_state()

    append_reasoning_log(
        state,
        stage="execute_tests",
        event_type="tool_call",
        tool_name="http_executor.execute_single_test",
        reason="Dispatch request.",
        input_summary={"Authorization": "Bearer secret-token"},
    )

    event = state["reasoning_log"][0]
    assert event["input_summary"]["Authorization"] == "Bearer [REDACTED]"


def test_group_reasoning_events_preserves_stage_order_and_reasoning_events():
    events = [
        {"stage": "parse_spec", "event_type": "tool_call", "reason": "Parse"},
        {"stage": "execute_tests", "event_type": "reasoning", "reason": "Branch"},
        {"stage": "execute_tests", "event_type": "tool_call", "reason": "Execute"},
    ]

    grouped = group_reasoning_events(events)

    assert [stage for stage, _events in grouped] == ["parse_spec", "execute_tests"]
    assert grouped[1][1][0]["event_type"] == "reasoning"


def test_group_reasoning_events_preserves_chronology_across_reruns():
    """Re-runs must render as new stage blocks, not fold back into earlier ones."""
    state = initial_state()

    # First run: parse → execute → analyze
    append_reasoning_log(
        state, stage="parse_spec", event_type="tool_call", reason="Parse 1"
    )
    append_reasoning_log(
        state, stage="execute_tests", event_type="tool_call", reason="Execute 1"
    )
    append_reasoning_log(
        state, stage="analyze_results", event_type="reasoning", reason="Analyze 1"
    )
    # Re-run: execute → analyze again (iteration loop)
    append_reasoning_log(
        state, stage="execute_tests", event_type="tool_call", reason="Execute 2"
    )
    append_reasoning_log(
        state, stage="analyze_results", event_type="reasoning", reason="Analyze 2"
    )

    grouped = group_reasoning_events(state["reasoning_log"])
    stages = [stage for stage, _events in grouped]

    assert stages == [
        "parse_spec",
        "execute_tests",
        "analyze_results",
        "execute_tests",
        "analyze_results",
    ], (
        "Re-run events must appear as a new trailing block rather than being "
        "folded back into the original execute_tests group"
    )
    # The two execute_tests runs should carry distinct reasons in the right order.
    reasons_in_order = [
        event["reason"] for _stage, events in grouped for event in events
    ]
    assert reasons_in_order == [
        "Parse 1",
        "Execute 1",
        "Analyze 1",
        "Execute 2",
        "Analyze 2",
    ]
