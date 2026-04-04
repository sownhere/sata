# Backward-compatibility shim — canonical source is src.tools.conversational_builder
# All new code should import from src.tools.conversational_builder directly.
# This shim will be removed in Story 7.6.
from src.tools.conversational_builder import (  # noqa: F401
    EXPECTED_AUTH_KEYS,
    EXPECTED_ENDPOINT_KEYS,
    EXPECTED_TOP_LEVEL_KEYS,
    extract_api_model_from_conversation,
)
