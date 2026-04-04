"""detect_gaps pipeline node — identifies missing or ambiguous spec fields."""

from src.core.state import SataState
from src.tools.gap_detector import detect_spec_gaps


def detect_gaps(state: SataState) -> SataState:
    """Identify missing or ambiguous spec fields and stage targeted questions."""
    raw_spec = state.get("raw_spec")
    parsed_api_model = state.get("parsed_api_model")
    if not raw_spec or not parsed_api_model:
        state["error_message"] = "Cannot detect gaps before a spec is parsed."
        state["detected_gaps"] = None
        state["pipeline_stage"] = "spec_ingestion"
        return state

    try:
        gaps = detect_spec_gaps(raw_spec, parsed_api_model)
        existing_answers = state.get("gap_answers") or {}
        gap_ids = {gap["id"] for gap in gaps}
        state["gap_answers"] = {
            gap_id: answer
            for gap_id, answer in existing_answers.items()
            if gap_id in gap_ids
        }
        state["detected_gaps"] = gaps
        state["error_message"] = None
        state["pipeline_stage"] = "fill_gaps" if gaps else "review_spec"
    except Exception:
        state["error_message"] = (
            "Could not analyze the parsed spec for clarification gaps."
        )
        state["detected_gaps"] = None
        state["pipeline_stage"] = "spec_parsed"
    return state
