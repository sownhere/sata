"""Backward-compatibility shim — canonical source is src.core.config.

All new code should import from src.core.config directly.
This shim will be removed once all consumers are updated (Story 7.6).
"""

from src.core.config import REQUIRED_ENV_VARS, load_env, validate_env  # noqa: F401
