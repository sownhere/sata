"""parse_spec pipeline node — parses raw OpenAPI/Swagger spec."""

from src.core.state import SataState
from src.tools.spec_parser import parse_openapi_spec


def parse_spec(state: SataState) -> SataState:
    """Parse OpenAPI/Swagger spec from state["raw_spec"].

    On success: populate parsed_api_model and advance pipeline_stage.
    On failure: set error_message, clear parsed_api_model, and never raise.
    """
    raw = state.get("raw_spec")
    if not raw:
        state["error_message"] = "No spec content found. Please upload a file."
        state["parsed_api_model"] = None
        return state
    try:
        model = parse_openapi_spec(raw)
        state["parsed_api_model"] = model
        state["pipeline_stage"] = "spec_parsed"
        state["error_message"] = None
    except ValueError as exc:
        state["error_message"] = str(exc)
        state["parsed_api_model"] = None
        state["pipeline_stage"] = "spec_ingestion"
    except Exception:
        state["error_message"] = (
            "Unexpected error parsing spec."
            " Please check your file format and try again."
        )
        state["parsed_api_model"] = None
        state["pipeline_stage"] = "spec_ingestion"
    return state
