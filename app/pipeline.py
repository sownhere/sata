"""LangGraph pipeline skeleton for Sata.

Defines all 10 named nodes and wires 6 conditional routing paths.
Each story in Epic 1–6 replaces a stub with real implementation.

Node execution order:
  ingest_spec → parse_spec → detect_gaps → fill_gaps → review_spec
  → generate_tests → review_test_plan → execute_tests
  → analyze_results → review_results → END
"""

from typing import Optional

from langgraph.graph import END, StateGraph

from app.state import SataState
from app.utils.conversational_spec_builder import extract_api_model_from_conversation
from app.utils.spec_gap_detector import detect_spec_gaps
from app.utils.spec_parser import parse_openapi_spec

PIPELINE_NODE_ORDER = [
    "ingest_spec",
    "parse_spec",
    "detect_gaps",
    "fill_gaps",
    "review_spec",
    "generate_tests",
    "review_test_plan",
    "execute_tests",
    "analyze_results",
    "review_results",
]

PIPELINE_NODE_METADATA = {
    "ingest_spec": {
        "label": "File or URL Import",
        "role": "Entry point for file, URL, or chat-based spec intake.",
    },
    "parse_spec": {
        "label": "Parse Spec",
        "role": "Parse raw OpenAPI or Swagger content into the canonical API model.",
    },
    "detect_gaps": {
        "label": "Detect Gaps",
        "role": "Identify missing, ambiguous, or under-specified API details.",
    },
    "fill_gaps": {
        "label": "Fill Gaps",
        "role": "Collect developer clarifications or manual conversational fallback input.",
    },
    "review_spec": {
        "label": "Review Spec",
        "role": "Human checkpoint for confirming the parsed API model.",
    },
    "generate_tests": {
        "label": "Generate Tests",
        "role": "Produce categorized API test cases from the confirmed spec.",
    },
    "review_test_plan": {
        "label": "Review Test Plan",
        "role": "Human checkpoint for approving or revising the generated test plan.",
    },
    "execute_tests": {
        "label": "Execute Tests",
        "role": "Run HTTP test requests with auth and retry safeguards.",
    },
    "analyze_results": {
        "label": "Analyze Results",
        "role": "Summarize failures, detect defect patterns, and explain outcomes.",
    },
    "review_results": {
        "label": "Review Results",
        "role": "Present outcomes and support deeper-analysis or re-test loops.",
    },
}

CONDITIONAL_EDGE_LABELS = {
    ("ingest_spec", "parse_spec"): "file or URL import",
    ("ingest_spec", "fill_gaps"): "manual chat mode",
    ("parse_spec", "detect_gaps"): "endpoints found",
    ("parse_spec", "fill_gaps"): "zero endpoints fallback",
    ("detect_gaps", "fill_gaps"): "gaps detected",
    ("detect_gaps", "review_spec"): "no gaps",
    ("review_spec", "generate_tests"): "confirmed",
    ("review_spec", "ingest_spec"): "rejected",
    ("review_test_plan", "execute_tests"): "approved",
    ("review_test_plan", "generate_tests"): "revise plan",
    ("review_results", "analyze_results"): "deeper analysis",
}

LINEAR_EDGE_LABELS = {
    ("fill_gaps", "review_spec"): "clarifications complete",
    ("generate_tests", "review_test_plan"): "plan generated",
    ("execute_tests", "analyze_results"): "execution complete",
    ("analyze_results", "review_results"): "analysis ready",
}

PIPELINE_STAGE_TO_NODE = {
    "spec_ingestion": "ingest_spec",
    "spec_parsed": "parse_spec",
    "fill_gaps": "fill_gaps",
    "review_spec": "review_spec",
    "generate_tests": "generate_tests",
    "review_test_plan": "review_test_plan",
    "execute_tests": "execute_tests",
    "analyze_results": "analyze_results",
    "review_results": "review_results",
}


# ── Node implementations ───────────────────────────────────────────────────


def ingest_spec(state: SataState) -> SataState:
    """Receive spec source selection and keep the app at ingestion stage."""
    state["pipeline_stage"] = "spec_ingestion"
    return state


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
            "Unexpected error parsing spec. Please check your file format and try again."
        )
        state["parsed_api_model"] = None
        state["pipeline_stage"] = "spec_ingestion"
    return state


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
        state["pipeline_stage"] = "spec_parsed"
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
    return state


def generate_tests(state: SataState) -> SataState:
    """Stub: LLM generates test cases across 6+ defect categories."""
    return state


def review_test_plan(state: SataState) -> SataState:
    """Stub: Checkpoint 2 — waits for human test plan approval."""
    return state


def execute_tests(state: SataState) -> SataState:
    """Stub: HTTP test execution with auth + basic retry logic."""
    return state


def analyze_results(state: SataState) -> SataState:
    """Stub: defect pattern analysis + developer-friendly explanations."""
    return state


def review_results(state: SataState) -> SataState:
    """Stub: Checkpoint 3 — re-test loop entry point."""
    return state


# ── Routing helpers ────────────────────────────────────────────────────────


def _route_after_ingest(state: SataState) -> str:
    """Route: file/URL spec → parse_spec; chat mode → fill_gaps."""
    return "fill_gaps" if state.get("spec_source") == "chat" else "parse_spec"


def _route_after_parse(state: SataState) -> str:
    """Route: zero endpoints found → fill_gaps; otherwise → detect_gaps."""
    parsed_api_model = state.get("parsed_api_model") or {}
    endpoints = parsed_api_model.get("endpoints") or []
    has_zero_endpoints = (
        isinstance(endpoints, list) and len(endpoints) == 0 and bool(parsed_api_model)
    )
    return "fill_gaps" if has_zero_endpoints else "detect_gaps"


def _route_gaps(state: SataState) -> str:
    """Route: gaps detected → fill_gaps; no gaps → review_spec."""
    return "fill_gaps" if state.get("detected_gaps") else "review_spec"


def _route_spec_review(state: SataState) -> str:
    """Route: confirmed → generate_tests; rejected → ingest_spec."""
    return "generate_tests"


def _route_test_plan(state: SataState) -> str:
    """Route: confirmed → execute_tests; rejected → generate_tests."""
    return "execute_tests"


def _route_results(state: SataState) -> str:
    """Route: deeper analysis requested → analyze_results; done → END."""
    return "analyze_results"


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
    auth_required_endpoints = [
        endpoint
        for endpoint in parsed_api_model.get("endpoints", [])
        if endpoint.get("auth_required")
    ]
    auth = parsed_api_model.setdefault("auth", {})

    if answer == "none":
        if not auth_required_endpoints:
            auth.clear()
            auth.update(_auth_state_from_answer("none"))
        return

    if len(auth_required_endpoints) == 1:
        auth.clear()
        auth.update(_auth_state_from_answer(answer))


def _is_conversational_mode(state: SataState) -> bool:
    if state.get("spec_source") == "chat":
        return True

    parsed_api_model = state.get("parsed_api_model") or {}
    endpoints = parsed_api_model.get("endpoints")
    return (
        bool(parsed_api_model) and isinstance(endpoints, list) and len(endpoints) == 0
    )


NODE_HANDLERS = {
    "ingest_spec": ingest_spec,
    "parse_spec": parse_spec,
    "detect_gaps": detect_gaps,
    "fill_gaps": fill_gaps,
    "review_spec": review_spec,
    "generate_tests": generate_tests,
    "review_test_plan": review_test_plan,
    "execute_tests": execute_tests,
    "analyze_results": analyze_results,
    "review_results": review_results,
}

ROUTE_HANDLERS = {
    "ingest_spec": _route_after_ingest,
    "parse_spec": _route_after_parse,
    "detect_gaps": _route_gaps,
    "review_spec": _route_spec_review,
    "review_test_plan": _route_test_plan,
    "review_results": _route_results,
}

LINEAR_ROUTE_TARGETS = {
    "fill_gaps": "review_spec",
    "generate_tests": "review_test_plan",
    "execute_tests": "analyze_results",
    "analyze_results": "review_results",
}


def reset_visualization_trace(state: SataState) -> SataState:
    """Clear visualization-only execution history for a new run."""
    state["active_node"] = None
    state["completed_nodes"] = []
    state["taken_edges"] = []
    state["selected_visual_node"] = None
    return state


def run_pipeline_node(
    state: SataState,
    node_name: str,
    handler=None,
) -> SataState:
    """Run a node while updating visualization state consistently."""
    prior_active = state.get("active_node")
    if (
        prior_active
        and prior_active != node_name
        and (prior_active, node_name) in LINEAR_EDGE_LABELS
    ):
        _append_taken_edge(state, prior_active, node_name)

    state["active_node"] = node_name
    if not state.get("selected_visual_node"):
        state["selected_visual_node"] = node_name

    node_handler = handler or NODE_HANDLERS[node_name]
    result = node_handler(state)

    completed_nodes = list(result.get("completed_nodes") or [])
    if node_name not in completed_nodes:
        completed_nodes.append(node_name)
    result["completed_nodes"] = completed_nodes
    result["active_node"] = node_name
    if not result.get("selected_visual_node"):
        result["selected_visual_node"] = node_name
    return result


def record_route_transition(
    state: SataState,
    source_node: str,
    target_override: Optional[str] = None,
):
    """Record the next pipeline transition and make the target node active."""
    target = target_override or _resolve_route_target(state, source_node)
    if target in (None, END):
        state["active_node"] = None
        return target

    _append_taken_edge(state, source_node, target)
    state["active_node"] = target
    if not state.get("selected_visual_node"):
        state["selected_visual_node"] = target
    return target


def _append_taken_edge(state: SataState, source: str, target: str) -> None:
    taken_edges = list(state.get("taken_edges") or [])
    taken_edges.append({"source": source, "target": target})
    state["taken_edges"] = taken_edges


def _resolve_route_target(state: SataState, source_node: str):
    if source_node in ROUTE_HANDLERS:
        return ROUTE_HANDLERS[source_node](state)
    return LINEAR_ROUTE_TARGETS.get(source_node)


def _make_instrumented_node(node_name: str):
    def _runner(state: SataState) -> SataState:
        return run_pipeline_node(state, node_name)

    _runner.__name__ = f"run_{node_name}"
    return _runner


def _make_recording_router(source_node: str):
    def _router(state: SataState):
        target = _resolve_route_target(state, source_node)
        return record_route_transition(state, source_node, target_override=target)

    _router.__name__ = f"route_{source_node}"
    return _router


# ── Graph builder ─────────────────────────────────────────────────────────


def build_pipeline():
    """Build and compile the full Sata LangGraph pipeline."""
    builder = StateGraph(SataState)

    builder.add_node("ingest_spec", _make_instrumented_node("ingest_spec"))
    builder.add_node("parse_spec", _make_instrumented_node("parse_spec"))
    builder.add_node("detect_gaps", _make_instrumented_node("detect_gaps"))
    builder.add_node("fill_gaps", _make_instrumented_node("fill_gaps"))
    builder.add_node("review_spec", _make_instrumented_node("review_spec"))
    builder.add_node("generate_tests", _make_instrumented_node("generate_tests"))
    builder.add_node("review_test_plan", _make_instrumented_node("review_test_plan"))
    builder.add_node("execute_tests", _make_instrumented_node("execute_tests"))
    builder.add_node("analyze_results", _make_instrumented_node("analyze_results"))
    builder.add_node("review_results", _make_instrumented_node("review_results"))

    builder.set_entry_point("ingest_spec")

    builder.add_conditional_edges(
        "ingest_spec",
        _make_recording_router("ingest_spec"),
        {"parse_spec": "parse_spec", "fill_gaps": "fill_gaps"},
    )
    builder.add_conditional_edges(
        "parse_spec",
        _make_recording_router("parse_spec"),
        {"detect_gaps": "detect_gaps", "fill_gaps": "fill_gaps"},
    )
    builder.add_conditional_edges(
        "detect_gaps",
        _make_recording_router("detect_gaps"),
        {"fill_gaps": "fill_gaps", "review_spec": "review_spec"},
    )
    builder.add_conditional_edges(
        "review_spec",
        _make_recording_router("review_spec"),
        {"generate_tests": "generate_tests", "ingest_spec": "ingest_spec"},
    )
    builder.add_conditional_edges(
        "review_test_plan",
        _make_recording_router("review_test_plan"),
        {"execute_tests": "execute_tests", "generate_tests": "generate_tests"},
    )
    builder.add_conditional_edges(
        "review_results",
        _make_recording_router("review_results"),
        {"analyze_results": "analyze_results", END: END},
    )

    builder.add_edge("fill_gaps", "review_spec")
    builder.add_edge("generate_tests", "review_test_plan")
    builder.add_edge("execute_tests", "analyze_results")
    builder.add_edge("analyze_results", "review_results")

    return builder.compile()
