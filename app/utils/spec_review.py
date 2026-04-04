# Backward-compatibility shim — canonical source is src.ui.spec_review
# All new code should import from src.ui.spec_review directly.
# This shim will be removed in Story 7.6.
from src.ui.spec_review import (  # noqa: F401
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    get_stage_display_label,
)
