"""Unit tests for shared redaction helpers."""

from src.tools.redaction import redact_headers, sanitize_value


def test_redact_headers_masks_common_secret_headers_case_insensitively():
    headers = {
        "Authorization": "Bearer top-secret",
        "x-api-key": "abc123",
        "Accept": "application/json",
    }

    redacted = redact_headers(headers)

    assert redacted["Authorization"] == "Bearer [REDACTED]"
    assert redacted["x-api-key"] == "[REDACTED]"
    assert redacted["Accept"] == "application/json"


def test_sanitize_value_masks_nested_secret_like_fields():
    payload = {
        "token": "secret-token",
        "profile": {
            "name": "Alice",
            "apiKey": "another-secret",
        },
    }

    sanitized = sanitize_value(payload)

    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["profile"]["apiKey"] == "[REDACTED]"
    assert sanitized["profile"]["name"] == "Alice"
