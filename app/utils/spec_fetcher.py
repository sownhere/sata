# Backward-compatibility shim — canonical source is src.tools.spec_fetcher
# All new code should import from src.tools.spec_fetcher directly.
# This shim will be removed in Story 7.6.
# NOTE: _OPENER is re-exported explicitly so monkeypatch targets still work.
from src.tools.spec_fetcher import (  # noqa: F401
    _OPENER,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    fetch_spec_from_url,
)
