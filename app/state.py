"""Shared pipeline state — single source of truth for all LangGraph nodes.

All nodes must import SataState from this module. Never define or redefine
state fields in individual node files.
"""

from typing import Optional
from typing_extensions import TypedDict


class SataState(TypedDict):
    # ── Ingestion ──────────────────────────────────────────────────────
    spec_source: Optional[str]  # "file" | "url" | "chat"
    raw_spec: Optional[str]  # Raw file/URL content string
    conversation_messages: Optional[
        list
    ]  # Chat transcript for manual/fallback ingestion
    conversation_question: Optional[
        str
    ]  # Pending follow-up question during chat ingestion

    # ── Parsing ────────────────────────────────────────────────────────
    parsed_api_model: Optional[dict]  # {endpoints: [...], auth: {...}}
    spec_confirmed: bool  # True after Checkpoint 1 confirm

    # ── Gaps ───────────────────────────────────────────────────────────
    detected_gaps: Optional[list]  # [{endpoint, field, question}, ...]
    gap_answers: Optional[dict]  # {question_id: answer}

    # ── Test Generation ────────────────────────────────────────────────
    test_cases: Optional[list]  # [{id, endpoint, category, priority, ...}]
    test_plan_confirmed: bool  # True after Checkpoint 2 confirm

    # ── Execution ──────────────────────────────────────────────────────
    test_results: Optional[list]  # [{test_id, passed, actual_status, ...}]

    # ── Analysis ───────────────────────────────────────────────────────
    failure_analysis: Optional[dict]  # {patterns: [...], explanations: [...]}

    # ── Pipeline Control ───────────────────────────────────────────────
    pipeline_stage: str  # Drives stage header in UI (UX-DR1)
    error_message: Optional[str]  # Displayed via st.error() when set
    iteration_count: int  # Anti-infinite-loop guard (NFR5)
    active_node: Optional[str]  # Current active pipeline node for visualization
    completed_nodes: list  # Completed pipeline nodes in execution order
    taken_edges: list  # Routed edges taken during execution
    selected_visual_node: Optional[str]  # UI-selected visualization node


def initial_state() -> SataState:
    """Return a fresh SataState with safe default values."""
    return SataState(
        spec_source=None,
        raw_spec=None,
        conversation_messages=None,
        conversation_question=None,
        parsed_api_model=None,
        spec_confirmed=False,
        detected_gaps=None,
        gap_answers=None,
        test_cases=None,
        test_plan_confirmed=False,
        test_results=None,
        failure_analysis=None,
        pipeline_stage="spec_ingestion",
        error_message=None,
        iteration_count=0,
        active_node=None,
        completed_nodes=[],
        taken_edges=[],
        selected_visual_node=None,
    )
