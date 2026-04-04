"""Pure helpers for mutating the canonical parsed API model (no Streamlit)."""

from __future__ import annotations

import copy
from typing import Any


def update_endpoint_field(
    parsed_api_model: dict,
    endpoint_index: int,
    field: str,
    value: Any,
) -> dict:
    """Return a new model dict with one endpoint field updated; never mutates input."""
    out = copy.deepcopy(parsed_api_model)
    endpoints = out.get("endpoints")
    if not isinstance(endpoints, list):
        return out
    if endpoint_index < 0 or endpoint_index >= len(endpoints):
        return out
    ep = endpoints[endpoint_index]
    if not isinstance(ep, dict):
        return out
    ep[field] = value
    return out


def add_endpoint(parsed_api_model: dict, new_endpoint: dict) -> dict:
    """Append ``new_endpoint`` to ``endpoints``; validate ``path`` and ``method``."""
    if not isinstance(new_endpoint, dict):
        raise ValueError("new_endpoint must be a dict")
    path = new_endpoint.get("path")
    method = new_endpoint.get("method")
    if path is None or str(path).strip() == "":
        raise ValueError("path is required")
    if method is None or str(method).strip() == "":
        raise ValueError("method is required")

    out = copy.deepcopy(parsed_api_model)
    endpoints = out.get("endpoints")
    if not isinstance(endpoints, list):
        out["endpoints"] = []
        endpoints = out["endpoints"]
    endpoints.append(copy.deepcopy(new_endpoint))
    return out


def remove_endpoint(parsed_api_model: dict, endpoint_index: int) -> dict:
    """Return a new model without the endpoint at index (no-op if invalid)."""
    out = copy.deepcopy(parsed_api_model)
    endpoints = out.get("endpoints")
    if not isinstance(endpoints, list):
        return out
    if endpoint_index < 0 or endpoint_index >= len(endpoints):
        return out
    out["endpoints"] = endpoints[:endpoint_index] + endpoints[endpoint_index + 1 :]
    return out
