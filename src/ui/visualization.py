"""Helpers for rendering the pipeline visualization.

Canonical location: src.ui.visualization
(Migrated from app/utils/pipeline_visualization.py — no logic changes.)
"""

from src.core.graph import (
    CONDITIONAL_EDGE_LABELS,
    LINEAR_EDGE_LABELS,
    PIPELINE_NODE_METADATA,
    PIPELINE_NODE_ORDER,
    PIPELINE_STAGE_TO_NODE,
)


def get_node_detail(node_name: str) -> dict:
    """Return the display metadata for a pipeline node."""
    return PIPELINE_NODE_METADATA[node_name]


def get_default_visual_node(state: dict) -> str:
    """Choose the best node for the detail panel when none is explicitly selected."""
    if state.get("active_node") in PIPELINE_NODE_METADATA:
        return state["active_node"]
    if state.get("selected_visual_node") in PIPELINE_NODE_METADATA:
        return state["selected_visual_node"]
    stage_node = PIPELINE_STAGE_TO_NODE.get(state.get("pipeline_stage"))
    if stage_node in PIPELINE_NODE_METADATA:
        return stage_node
    return PIPELINE_NODE_ORDER[0]


def build_visualization_model(state: dict) -> dict:
    """Return a testable node/edge model for the pipeline diagram."""
    active_node = state.get("active_node")
    completed_nodes = set(state.get("completed_nodes") or [])
    taken_edges = {
        (edge["source"], edge["target"]) for edge in (state.get("taken_edges") or [])
    }

    nodes = []
    for node_name in PIPELINE_NODE_ORDER:
        metadata = PIPELINE_NODE_METADATA[node_name]
        if node_name == active_node:
            status = "active"
        elif node_name in completed_nodes:
            status = "completed"
        else:
            status = "pending"

        nodes.append(
            {
                "id": node_name,
                "label": metadata["label"],
                "role": metadata["role"],
                "status": status,
                "tooltip": metadata["role"],
            }
        )

    edges = []
    for source, target in CONDITIONAL_EDGE_LABELS:
        edges.append(
            {
                "source": source,
                "target": target,
                "label": CONDITIONAL_EDGE_LABELS[(source, target)],
                "is_conditional": True,
                "status": "taken" if (source, target) in taken_edges else "untaken",
            }
        )

    for source, target in LINEAR_EDGE_LABELS:
        edges.append(
            {
                "source": source,
                "target": target,
                "label": LINEAR_EDGE_LABELS[(source, target)],
                "is_conditional": False,
                "status": "taken" if (source, target) in taken_edges else "default",
            }
        )

    return {"nodes": nodes, "edges": edges}


def build_pipeline_graph_dot(state: dict) -> str:
    """Render the current pipeline visualization as DOT for Streamlit."""
    model = build_visualization_model(state)
    lines = [
        "digraph sata_pipeline {",
        "  rankdir=LR;",
        "  splines=true;",
        "  nodesep=0.45;",
        "  ranksep=0.8;",
        '  graph [bgcolor="white"];',
        '  node [shape=box, style="rounded,filled",'
        ' fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=10, arrowsize=0.8];',
    ]

    for node in model["nodes"]:
        style = _node_style(node["status"])
        lines.append(
            "  {id} [{attrs}];".format(
                id=node["id"],
                attrs=", ".join(
                    [
                        f"label={_dot_quote(node['label'])}",
                        f"tooltip={_dot_quote(node['tooltip'])}",
                        f"fillcolor={_dot_quote(style['fillcolor'])}",
                        f"color={_dot_quote(style['color'])}",
                        f"fontcolor={_dot_quote(style['fontcolor'])}",
                        f"penwidth={style['penwidth']}",
                    ]
                ),
            )
        )

    for edge in model["edges"]:
        style = _edge_style(edge["status"], edge["is_conditional"])
        lines.append(
            "  {source} -> {target} [{attrs}];".format(
                source=edge["source"],
                target=edge["target"],
                attrs=", ".join(
                    [
                        f"label={_dot_quote(edge['label'])}",
                        f"color={_dot_quote(style['color'])}",
                        f"fontcolor={_dot_quote(style['fontcolor'])}",
                        f"style={_dot_quote(style['style'])}",
                        f"penwidth={style['penwidth']}",
                    ]
                ),
            )
        )

    lines.append("}")
    return "\n".join(lines)


def _node_style(status: str) -> dict:
    if status == "active":
        return {
            "fillcolor": "#FEF3C7",
            "color": "#D97706",
            "fontcolor": "#92400E",
            "penwidth": "2.6",
        }
    if status == "completed":
        return {
            "fillcolor": "#DCFCE7",
            "color": "#15803D",
            "fontcolor": "#166534",
            "penwidth": "2.2",
        }
    return {
        "fillcolor": "#F8FAFC",
        "color": "#94A3B8",
        "fontcolor": "#334155",
        "penwidth": "1.3",
    }


def _edge_style(status: str, is_conditional: bool) -> dict:
    if status == "taken":
        return {
            "color": "#2563EB",
            "fontcolor": "#1D4ED8",
            "style": "bold",
            "penwidth": "2.4",
        }
    if is_conditional:
        return {
            "color": "#94A3B8",
            "fontcolor": "#64748B",
            "style": "dashed",
            "penwidth": "1.4",
        }
    return {
        "color": "#475569",
        "fontcolor": "#475569",
        "style": "solid",
        "penwidth": "1.6",
    }


def _dot_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
