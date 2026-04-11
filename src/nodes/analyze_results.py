"""analyze_results pipeline node — LLM-powered failure pattern analysis."""

from src.core.observability import append_reasoning_log
from src.core.state import SataState
from src.tools.failure_analyzer import (
    analyze_failures,
    diagnose_all_failed_results,
    suggest_next_test_scenarios,
)


def analyze_results(state: SataState) -> SataState:
    """Analyze test results, group failures into patterns, generate explanations.

    Guard: requires state["test_results"] to be set (not None).
    On success: populates state["failure_analysis"] and advances pipeline_stage
    to "review_results".
    """
    if state.get("test_results") is None:
        append_reasoning_log(
            state,
            stage="analyze_results",
            event_type="reasoning",
            reason="Skipped analysis because execution results are missing.",
            details={"has_test_results": False},
        )
        state["error_message"] = "No test results to analyze."
        state["pipeline_stage"] = "execute_tests"
        return state

    test_results = list(state.get("test_results") or [])
    failed_results = [result for result in test_results if not result.get("passed")]
    total_results = len(test_results)
    all_passed = total_results > 0 and len(failed_results) == 0
    all_failed = total_results > 0 and len(failed_results) == total_results

    append_reasoning_log(
        state,
        stage="analyze_results",
        event_type="tool_call",
        tool_name="failure_analyzer.analyze_failures",
        reason="Generate grouped failure patterns and developer-friendly explanations.",
        input_summary={
            "total_results": total_results,
            "failed_results": len(failed_results),
            "all_passed": all_passed,
            "all_failed": all_failed,
        },
    )
    analysis = analyze_failures(failed_results)
    analysis["all_passed"] = all_passed
    analysis["all_failed"] = all_failed
    analysis["next_test_suggestions"] = suggest_next_test_scenarios(
        test_results,
        state.get("parsed_api_model"),
        state.get("test_cases"),
    )
    analysis["smart_diagnosis"] = diagnose_all_failed_results(
        test_results,
        state.get("parsed_api_model"),
    )

    branch_reason = "Mixed pass/fail results detected."
    if all_passed:
        branch_reason = "All enabled tests passed; generated deeper-test suggestions."
    elif all_failed:
        branch_reason = "All enabled tests failed; attached a systemic diagnosis."
    append_reasoning_log(
        state,
        stage="analyze_results",
        event_type="reasoning",
        reason=branch_reason,
        details={
            "next_test_suggestions": len(analysis.get("next_test_suggestions") or []),
            "smart_diagnosis": (analysis.get("smart_diagnosis") or {}).get("category"),
        },
    )

    state["failure_analysis"] = analysis
    state["error_message"] = None
    state["pipeline_stage"] = "review_results"
    return state
