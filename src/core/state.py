"""Shared pipeline state — single source of truth for all LangGraph nodes.

Canonical location: src.core.state
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
    generated_test_cases: Optional[list]
    # Full generated plan before category filtering
    disabled_test_categories: Optional[list]  # Category keys excluded at Checkpoint 2
    test_cases: Optional[list]  # [{id, endpoint, category, priority, ...}]
    test_plan_confirmed: bool  # True after Checkpoint 2 confirm

    # ── Execution ──────────────────────────────────────────────────────
    target_api_url: Optional[str]  # Base URL of the target API under test
    test_results: Optional[list]  # [{test_id, passed, actual_status, ...}]

    # ── Analysis ───────────────────────────────────────────────────────
    failure_analysis: Optional[dict]  # {patterns: [...], explanations: [...]}
    generated_report: Optional[dict]  # {path, content, generated_at}

    # ── Pipeline Control ───────────────────────────────────────────────
    pipeline_stage: str  # Drives stage header in UI (UX-DR1)
    error_message: Optional[str]  # Displayed via st.error() when set
    iteration_count: int  # Anti-infinite-loop guard (NFR5)
    run_attempt: int  # Results iteration counter for re-test loops
    previous_run_summary: Optional[dict]  # Prior run snapshot for delta UI
    run_history: list  # Historical run summaries / scope metadata
    active_node: Optional[str]  # Current active pipeline node for visualization
    completed_nodes: list  # Completed pipeline nodes in execution order
    taken_edges: list  # Routed edges taken during execution
    selected_visual_node: Optional[str]  # UI-selected visualization node
    selected_test_id: Optional[str]  # Result detail drill-down selection
    results_filters: Optional[dict]  # Dashboard filter state
    scoped_run_selection: Optional[dict]  # Active scoped re-test selection
    reasoning_log: list  # Sanitized reasoning and tool-call events
    demo_context: Optional[dict]  # Demo mode catalog metadata


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
        generated_test_cases=None,
        disabled_test_categories=None,
        test_cases=None,
        test_plan_confirmed=False,
        target_api_url=None,
        test_results=None,
        failure_analysis=None,
        generated_report=None,
        pipeline_stage="spec_ingestion",
        error_message=None,
        iteration_count=0,
        run_attempt=0,
        previous_run_summary=None,
        run_history=[],
        active_node=None,
        completed_nodes=[],
        taken_edges=[],
        selected_visual_node=None,
        selected_test_id=None,
        results_filters=None,
        scoped_run_selection=None,
        reasoning_log=[],
        demo_context=None,
    )
