"""Backward-compatibility shim — canonical source is src.core.state.

All new code should import from src.core.state directly.
This shim will be removed once all consumers are updated (Story 7.6).
"""

from src.core.state import SataState, initial_state  # noqa: F401
