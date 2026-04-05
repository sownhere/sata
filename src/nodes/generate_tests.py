"""generate_tests pipeline node — Story 3.1 implementation."""

from src.core.state import SataState
from src.tools.test_case_generator import (
    filter_test_cases_against_confirmed_spec,
    generate_test_cases_for_model,
)


def generate_tests(state: SataState) -> SataState:
    """Generate and validate test cases from a confirmed API spec."""
    if not state.get("spec_confirmed"):
        state["pipeline_stage"] = "review_spec"
        state["error_message"] = "Confirm the API spec before generating a test plan."
        state["test_plan_confirmed"] = False
        return state

    parsed_api_model = state.get("parsed_api_model") or {}
    endpoints = parsed_api_model.get("endpoints") or []
    if not isinstance(endpoints, list) or len(endpoints) == 0:
        state["pipeline_stage"] = "spec_ingestion"
        state["error_message"] = (
            "Cannot generate tests because no confirmed endpoints are available."
        )
        state["test_plan_confirmed"] = False
        return state

    previous_cases = list(state.get("test_cases") or [])
    generation = generate_test_cases_for_model(parsed_api_model)
    filtered = filter_test_cases_against_confirmed_spec(
        generation["test_cases"], parsed_api_model
    )

    accepted_cases = filtered["accepted"]
    dropped_cases = filtered["dropped"]
    failed_endpoints = generation["failed_endpoints"]

    if accepted_cases:
        state["test_cases"] = accepted_cases
    elif previous_cases:
        # Keep last plan if this run produced nothing usable (endpoint failures,
        # all cases filtered, etc.).
        state["test_cases"] = previous_cases
    else:
        state["test_cases"] = []

    state["pipeline_stage"] = "generate_tests"
    state["test_plan_confirmed"] = False

    if failed_endpoints:
        state["error_message"] = (
            "Partial generation: "
            f"{len(state.get('test_cases') or [])} case(s) ready, "
            f"{len(failed_endpoints)} endpoint(s) failed after retry."
            + (
                f" {len(dropped_cases)} invalid case(s) were discarded."
                if dropped_cases
                else ""
            )
        )
    elif not accepted_cases:
        if previous_cases:
            state["error_message"] = (
                "Regeneration produced no valid test cases; "
                "showing the previous test plan."
                + (
                    f" {len(dropped_cases)} invalid case(s) were discarded."
                    if dropped_cases
                    else ""
                )
            )
        else:
            state["error_message"] = (
                "No valid test cases were generated from the confirmed spec."
            )
    else:
        state["error_message"] = None

    return state
