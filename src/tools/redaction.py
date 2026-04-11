"""Shared redaction helpers for results, reports, and observability logs."""

from __future__ import annotations

from collections.abc import Mapping

REDACTED_VALUE = "[REDACTED]"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "apikey",
    "x-api-key",
    "token",
    "secret",
    "password",
    "cookie",
    "set-cookie",
    "session",
    "private_key",
    "access_key",
)


def is_sensitive_key(key: object) -> bool:
    """Return True when a mapping key looks secret-bearing."""
    normalized = str(key or "").strip().lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_header_value(header_name: object, value: object) -> str:
    """Return a display-safe header value."""
    text = str(value or "")
    if not text:
        return text

    header = str(header_name or "").strip().lower()
    if header == "authorization":
        scheme, _, _ = text.partition(" ")
        return f"{scheme} {REDACTED_VALUE}".strip()
    if is_sensitive_key(header_name):
        return REDACTED_VALUE
    return text


def redact_headers(headers: Mapping | None) -> dict:
    """Return a copy of headers with sensitive values masked."""
    safe_headers: dict = {}
    for key, value in (headers or {}).items():
        safe_headers[str(key)] = redact_header_value(key, value)
    return safe_headers


def sanitize_value(value: object, key: object | None = None) -> object:
    """Recursively sanitize secret-like fields in a serializable value."""
    if key is not None and is_sensitive_key(key):
        return redact_header_value(key, value)

    if isinstance(value, Mapping):
        return {
            str(child_key): sanitize_value(child_value, child_key)
            for child_key, child_value in value.items()
        }

    if isinstance(value, list):
        return [sanitize_value(item) for item in value]

    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]

    return value
