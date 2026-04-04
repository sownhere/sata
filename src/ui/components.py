"""Shared Streamlit widget helpers for the Sata UI layer.

Canonical location: src.ui.components
Extracted from app.py — presentation helpers only, no pipeline orchestration.
"""

import streamlit as st

from src.core.graph import PIPELINE_NODE_ORDER
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
