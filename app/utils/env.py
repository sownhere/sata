"""Startup environment variable validation.

Separates .env file loading from environment inspection so that
``validate_env`` remains a pure ``os.environ`` query and is testable
without side-effects from a locally present ``.env`` file.

Typical startup sequence::

    load_env()          # populate os.environ from .env (once, at startup)
    missing = validate_env()  # pure check — safe to call in tests
    if missing:
        ...
"""

import os
from dotenv import load_dotenv

REQUIRED_ENV_VARS = ["LLM_API_KEY", "LLM_CHAT_MODEL", "LLM_BASE_URL"]


def load_env() -> None:
    """Load variables from a .env file into os.environ (no-op if already set).

    Uses ``override=False`` so that variables already present in the process
    environment (including those manipulated by ``monkeypatch`` in tests) are
    never overwritten.
    """
    load_dotenv(override=False)


def validate_env() -> list[str]:
    """Return a list of missing required environment variable names.

    This function is a *pure* os.environ inspector — it does **not** load any
    ``.env`` file.  Call ``load_env()`` beforehand at application startup if
    you need ``.env`` support.
    """
    return [var for var in REQUIRED_ENV_VARS if not os.environ.get(var, "").strip()]
