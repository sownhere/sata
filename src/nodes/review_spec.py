"""review_spec pipeline node — Checkpoint 1 guardrail."""

from src.core.state import SataState


def prepare_rejection_for_reparse(state: SataState) -> SataState:
    """Clear review-only artifacts while preserving the original ingestion input."""
    state["spec_confirmed"] = False
    state["parsed_api_model"] = None
    state["detected_gaps"] = None
    state["gap_answers"] = None
    state["error_message"] = None
    state["pipeline_stage"] = "spec_ingestion"
    return state


def review_spec(state: SataState) -> SataState:
    """Checkpoint 1 guardrail: only review specs that contain endpoints."""
    parsed_api_model = state.get("parsed_api_model") or {}
    endpoints = parsed_api_model.get("endpoints")
    if not isinstance(endpoints, list) or len(endpoints) == 0:
        state["error_message"] = "Cannot review a spec with no endpoints captured yet."
        state["pipeline_stage"] = "spec_ingestion"
        state["spec_confirmed"] = False
        return state

    state["error_message"] = None
    state["pipeline_stage"] = "review_spec"
    # Reset so a prior confirmation cannot bypass the checkpoint on re-import.
    state["spec_confirmed"] = False
    return state
