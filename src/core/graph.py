"""LangGraph pipeline builder and instrumentation for Sata.

Owns all graph-level constants, routing functions, visualization-trace
helpers, and the build_pipeline() factory.  Node *behaviour* lives in
src.nodes; this module only wires them together.

Pipeline flow:
  ingest_spec → parse_spec → detect_gaps → fill_gaps → review_spec
  → generate_tests → review_test_plan → execute_tests
  → analyze_results → review_results → END
"""

from typing import Optional

from langgraph.graph import END, StateGraph

from src.core.state import SataState
from src.nodes import (
    analyze_results,
    detect_gaps,
    execute_tests,
    fill_gaps,
    generate_tests,
    ingest_spec,
    parse_spec,
    review_results,
    review_spec,
    review_test_plan,
)

# ── Pipeline metadata ─────────────────────────────────────────────────────

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
        "role": (
            "Collect developer clarifications or manual conversational fallback input."
        ),
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
    ("review_results", END): "done",
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
    "ingest_spec": lambda state: _route_after_ingest(state),
    "parse_spec": lambda state: _route_after_parse(state),
    "detect_gaps": lambda state: _route_gaps(state),
    "review_spec": lambda state: _route_spec_review(state),
    "review_test_plan": lambda state: _route_test_plan(state),
    "review_results": lambda state: _route_results(state),
}

LINEAR_ROUTE_TARGETS = {
    "fill_gaps": "review_spec",
    "generate_tests": "review_test_plan",
    "execute_tests": "analyze_results",
    "analyze_results": "review_results",
}


# ── Routing functions ─────────────────────────────────────────────────────


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
    return "generate_tests" if state.get("spec_confirmed") else "ingest_spec"


def _route_test_plan(state: SataState) -> str:
    """Route: confirmed → execute_tests; rejected → generate_tests."""
    return "execute_tests" if state.get("test_plan_confirmed") else "generate_tests"


def _route_results(state: SataState) -> str:
    """Route: deeper analysis requested → analyze_results; done → END."""
    return END


# ── Visualization-trace instrumentation ──────────────────────────────────


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

    for node_name in PIPELINE_NODE_ORDER:
        builder.add_node(node_name, _make_instrumented_node(node_name))

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
