# Backward-compatibility shim — canonical source is src.tools.gap_detector
# All new code should import from src.tools.gap_detector directly.
# This shim will be removed in Story 7.6.
from src.tools.gap_detector import (  # noqa: F401
    AUTH_OPTIONS,
    COMMON_ERROR_STATUS_CODES,
    WRITE_METHODS,
    detect_spec_gaps,
)
