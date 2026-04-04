"""fill_gaps node — applies clarification answers or conversational extraction."""

from typing import Optional

from src.core.state import SataState
from src.tools.conversational_builder import extract_api_model_from_conversation


def fill_gaps(state: SataState) -> SataState:
    """Apply structured clarification answers and advance once gaps are resolved."""
    if _is_conversational_mode(state):
        conversation_messages = state.get("conversation_messages") or []
        if not conversation_messages:
            state["error_message"] = (
                "Start by describing at least one endpoint before continuing."
            )
            state["pipeline_stage"] = "fill_gaps"
            return state

        iteration_count = (state.get("iteration_count") or 0) + 1
        state["iteration_count"] = iteration_count
        if iteration_count > 10:
            state["error_message"] = (
                "Could not build a complete API model after several exchanges."
                " Please restart and try describing your endpoints more concisely."
            )
            state["pipeline_stage"] = "spec_ingestion"
            return state

        try:
            result = extract_api_model_from_conversation(conversation_messages)
        except ValueError as exc:
            state["error_message"] = str(exc)
            state["pipeline_stage"] = "fill_gaps"
            return state
        except Exception:
            state["error_message"] = (
                "Could not interpret the API description. Please try again."
            )
            state["pipeline_stage"] = "fill_gaps"
            return state

        if result["status"] == "needs_more_info":
            state["conversation_question"] = result["question"]
            state["error_message"] = None
            state["parsed_api_model"] = None
            state["pipeline_stage"] = "fill_gaps"
            return state

        state["parsed_api_model"] = result["api_model"]
        state["conversation_question"] = None
        state["detected_gaps"] = None
        state["gap_answers"] = None
        state["error_message"] = None
        state["pipeline_stage"] = "review_spec"
        return state

    detected_gaps = state.get("detected_gaps") or []
    if not detected_gaps:
        state["pipeline_stage"] = "review_spec"
        state["error_message"] = None
        return state

    answers = dict(state.get("gap_answers") or {})
    unresolved_gaps = []
    parsed_api_model = state.get("parsed_api_model") or {}

    for gap in detected_gaps:
        answer = answers.get(gap["id"])
        if not _is_actionable_answer(gap, answer):
            unresolved_gaps.append(gap)
            continue
        _apply_gap_answer(parsed_api_model, gap, answer)

    state["parsed_api_model"] = parsed_api_model
    state["gap_answers"] = answers
    state["detected_gaps"] = unresolved_gaps
    state["error_message"] = None
    state["pipeline_stage"] = "review_spec" if not unresolved_gaps else "fill_gaps"
    return state


# ── Private helpers (used only by fill_gaps) ──────────────────────────────


def _is_conversational_mode(state: SataState) -> bool:
    if state.get("spec_source") == "chat":
        return True
    parsed_api_model = state.get("parsed_api_model") or {}
    endpoints = parsed_api_model.get("endpoints")
    return (
        bool(parsed_api_model) and isinstance(endpoints, list) and len(endpoints) == 0
    )


def _is_actionable_answer(gap: dict, answer) -> bool:
    input_type = gap.get("input_type")
    if input_type in {"text", "text_input", "text_area"}:
        return isinstance(answer, str) and bool(answer.strip())
    if input_type == "multiselect":
        return isinstance(answer, list) and bool(answer)
    if input_type == "select":
        return isinstance(answer, str) and bool(answer.strip())
    return answer is not None


def _apply_gap_answer(parsed_api_model: dict, gap: dict, answer) -> None:
    if gap.get("gap_type") == "missing_success_response":
        endpoint = _find_endpoint(parsed_api_model, gap)
        if endpoint is not None:
            response_schemas = endpoint.setdefault("response_schemas", {})
            if not response_schemas.get("200"):
                response_schemas["200"] = str(answer)
        return

    if gap.get("gap_type") == "missing_request_body":
        endpoint = _find_endpoint(parsed_api_model, gap)
        if endpoint is not None and not endpoint.get("request_body"):
            endpoint["request_body"] = str(answer)
        return

    if gap.get("gap_type") == "auth_ambiguity":
        target_answer = str(answer)
        for endpoint in parsed_api_model.get("endpoints", []):
            if endpoint.get("path") == gap.get("path") and endpoint.get(
                "method"
            ) == gap.get("method"):
                endpoint["auth_required"] = target_answer != "none"
        _apply_global_auth_if_unambiguous(parsed_api_model, target_answer)
        return

    if gap.get("gap_type") == "missing_error_responses" and isinstance(answer, list):
        endpoint = _find_endpoint(parsed_api_model, gap)
        if endpoint is None:
            return
        response_schemas = endpoint.setdefault("response_schemas", {})
        for status_code in answer:
            response_schemas.setdefault(
                str(status_code), "Documented by user during gap clarification."
            )


def _find_endpoint(parsed_api_model: dict, gap: dict) -> Optional[dict]:
    for endpoint in parsed_api_model.get("endpoints", []):
        if endpoint.get("path") == gap.get("path") and endpoint.get(
            "method"
        ) == gap.get("method"):
            return endpoint
    return None


def _auth_state_from_answer(answer: str) -> dict:
    if answer == "bearer":
        return {
            "type": "bearer",
            "scheme": "Bearer",
            "in": "header",
            "name": "Authorization",
        }
    if answer == "basic":
        return {
            "type": "basic",
            "scheme": "Basic",
            "in": "header",
            "name": "Authorization",
        }
    if answer == "api_key":
        return {"type": "api_key", "scheme": None, "in": "header", "name": "X-API-Key"}
    if answer == "oauth2":
        return {"type": "oauth2", "scheme": None, "in": None, "name": None}
    if answer == "openIdConnect":
        return {"type": "openIdConnect", "scheme": None, "in": None, "name": None}
    return {"type": None, "scheme": None, "in": None, "name": None}


def _apply_global_auth_if_unambiguous(parsed_api_model: dict, answer: str) -> None:
    if answer == "none":
        return  # Public endpoint — don't alter global auth config
    auth_required_endpoints = [
        ep for ep in parsed_api_model.get("endpoints", []) if ep.get("auth_required")
    ]
    if len(auth_required_endpoints) == 1:
        auth = parsed_api_model.setdefault("auth", {})
        auth.clear()
        auth.update(_auth_state_from_answer(answer))
