"""review_test_plan pipeline node — Story 3.2/3.3 implementation."""

from src.core.state import SataState


def prepare_rejection_for_test_regeneration(state: SataState) -> SataState:
    """Clear test-plan artifacts while preserving the confirmed spec.

    Mirrors prepare_rejection_for_reparse from review_spec. Called by app.py
    when the developer rejects the test plan at Checkpoint 2.
    """
    state["generated_test_cases"] = None
    state["disabled_test_categories"] = None
    state["test_cases"] = None
    state["test_plan_confirmed"] = False
    state["error_message"] = None
    state["pipeline_stage"] = "generate_tests"
    return state


def review_test_plan(state: SataState) -> SataState:
    """Prepare Checkpoint 2 state without mutating the full generated plan."""
    if not state.get("spec_confirmed"):
        state["pipeline_stage"] = "review_spec"
        state["error_message"] = "Confirm the API spec before reviewing the test plan."
        state["test_plan_confirmed"] = False
        return state

    if (
        state.get("pipeline_stage") == "generate_tests"
        or state.get("generated_test_cases") is None
    ):
        state["generated_test_cases"] = list(state.get("test_cases") or [])
        state["disabled_test_categories"] = []

    generated_test_cases = list(state.get("generated_test_cases") or [])
    disabled_test_categories = {
        str(category).strip()
        for category in (state.get("disabled_test_categories") or [])
        if str(category).strip()
    }

    state["test_cases"] = [
        test_case
        for test_case in generated_test_cases
        if str(test_case.get("category") or "").strip() not in disabled_test_categories
    ]
    state["disabled_test_categories"] = sorted(disabled_test_categories)
    state["pipeline_stage"] = "review_test_plan"
    state["test_plan_confirmed"] = False
    return state
