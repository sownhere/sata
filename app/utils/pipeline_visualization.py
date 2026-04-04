# Backward-compatibility shim — canonical source is src.ui.visualization
# All new code should import from src.ui.visualization directly.
# This shim will be removed in Story 7.6.
from src.ui.visualization import (  # noqa: F401
    build_pipeline_graph_dot,
    build_visualization_model,
    get_default_visual_node,
    get_node_detail,
)
