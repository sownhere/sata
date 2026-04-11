"""Shared Streamlit widget helpers for the Sata UI layer.

Canonical location: src.ui.components
Extracted from app.py — presentation helpers only, no pipeline orchestration.
"""

from __future__ import annotations

import streamlit as st

from src.core.graph import PIPELINE_NODE_ORDER
from src.tools.redaction import sanitize_value
from src.ui.visualization import (
    build_pipeline_graph_dot,
    get_default_visual_node,
    get_node_detail,
)


def render_gap_input(gap: dict, current_answer):
    """Render the appropriate Streamlit input widget for a gap question."""
    key = f"gap-answer-{gap['id']}"
    input_type = gap.get("input_type")
    if input_type == "select":
        widget_options = [""] + list(gap.get("options") or [])
        try:
            index = (
                widget_options.index(current_answer)
                if current_answer in widget_options
                else 0
            )
        except ValueError:
            index = 0
        return st.selectbox(
            gap["question"], options=widget_options, index=index, key=key
        )
    if input_type == "multiselect":
        return st.multiselect(
            gap["question"],
            options=list(gap.get("options") or []),
            default=current_answer or [],
            key=key,
        )
    if input_type == "text_input":
        return st.text_input(gap["question"], value=current_answer or "", key=key)
    return st.text_area(gap["question"], value=current_answer or "", key=key)


def has_ui_answer(answer) -> bool:
    """Return True if a gap answer widget has a non-empty user-provided value."""
    if isinstance(answer, str):
        return bool(answer.strip())
    if isinstance(answer, list):
        return bool(answer)
    return answer is not None


def format_gap_answer(answer) -> str:
    """Format a gap answer value for display in the UI."""
    if isinstance(answer, list):
        return ", ".join(str(item) for item in answer)
    return str(answer)


def render_pipeline_visualization(current_state):
    """Render the collapsible pipeline visualization expander."""
    with st.expander("Developer: Pipeline Visualization", expanded=True):
        st.caption(
            "Observe the current pipeline node, the completed path,"
            " and the routing branches available from each stage."
        )
        st.graphviz_chart(
            build_pipeline_graph_dot(current_state), use_container_width=True
        )
        st.caption(
            "Legend: active = amber, completed = green, taken path = bold blue,"
            " untaken conditional path = dashed gray."
        )

        default_node = get_default_visual_node(current_state)
        selected_index = PIPELINE_NODE_ORDER.index(default_node)
        selected_node = st.selectbox(
            "Inspect node",
            options=PIPELINE_NODE_ORDER,
            index=selected_index,
            format_func=lambda node_name: get_node_detail(node_name)["label"],
            key="pipeline-visual-node-selector",
        )
        current_state["selected_visual_node"] = selected_node

        node_detail = get_node_detail(selected_node)
        st.markdown(f"**{node_detail['label']}**")
        st.write(node_detail["role"])

        if current_state.get("active_node") == selected_node:
            st.info("This node is currently active in the visualization.")
        elif selected_node in (current_state.get("completed_nodes") or []):
            st.success("This node has completed in the current recorded run.")
        else:
            st.caption("This node has not been reached in the current recorded run.")

        taken_edges = current_state.get("taken_edges") or []
        if taken_edges:
            last_edge = taken_edges[-1]
            src = last_edge["source"]
            tgt = last_edge["target"]
            st.caption(f"Most recent transition: `{src}` → `{tgt}`")


def _sorted_reasoning_events(events: list[dict] | None) -> list[dict]:
    """Return events sorted by insertion order, sanitized, in chronological order."""
    ordered = sorted(
        list(events or []),
        key=lambda event: (
            int(event.get("order") or 0),
            str(event.get("timestamp") or ""),
        ),
    )
    return [sanitize_value(event) for event in ordered]


def group_reasoning_events(events: list[dict] | None) -> list[tuple[str, list[dict]]]:
    """Group reasoning-log events into contiguous stage runs, preserving chronology.

    Unlike a stage-keyed dict (which would fold re-run events back into an
    earlier stage block), this groups only *consecutive* events that share a
    stage so cross-stage re-runs render in strict chronological order.
    """
    grouped: list[tuple[str, list[dict]]] = []
    for event in _sorted_reasoning_events(events):
        stage = str(event.get("stage") or "unknown")
        if grouped and grouped[-1][0] == stage:
            grouped[-1][1].append(event)
        else:
            grouped.append((stage, [event]))
    return grouped


def render_reasoning_log_panel(current_state):
    """Render a chronological reasoning-log panel for developer transparency."""
    with st.expander("Developer: Reasoning Logs", expanded=False):
        grouped = group_reasoning_events(current_state.get("reasoning_log") or [])
        if not grouped:
            st.caption("No reasoning or tool-call events have been recorded yet.")
            return

        for stage, events in grouped:
            stage_label = stage.replace("_", " ").title()
            st.markdown(f"**{stage_label}**")
            for event in events:
                event_type = str(event.get("event_type") or "reasoning")
                badge = {
                    "tool_call": "Tool Call",
                    "reasoning": "Reasoning",
                    "system_event": "System Event",
                }.get(event_type, event_type.replace("_", " ").title())
                tool_name = event.get("tool_name")
                heading = f"{badge}: {tool_name}" if tool_name else badge
                st.markdown(f"- **{heading}**")
                st.caption(str(event.get("reason") or ""))
                if event.get("input_summary"):
                    st.json(event["input_summary"], expanded=False)
                elif event.get("details"):
                    st.json(event["details"], expanded=False)
