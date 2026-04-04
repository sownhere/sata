# Backward-compatibility shim — canonical source is src.tools.spec_parser
# All new code should import from src.tools.spec_parser directly.
# This shim will be removed in Story 7.6.
from src.tools.spec_parser import parse_openapi_spec  # noqa: F401
