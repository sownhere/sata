"""Unit tests for src.tools.http_executor — mocks httpx.request, no network calls."""

from typing import Union
from unittest.mock import MagicMock, patch

import httpx

from src.tools.http_executor import (
    build_request_url,
    execute_single_test,
    get_auth_headers,
)

# ── get_auth_headers ──────────────────────────────────────────────────────────


def test_get_auth_headers_bearer_returns_authorization_header(monkeypatch):
    monkeypatch.setenv("API_BEARER_TOKEN", "my-secret-token")
    auth_config = {"type": "bearer", "name": "Authorization"}
    headers = get_auth_headers(auth_config)
    assert headers == {"Authorization": "Bearer my-secret-token"}


def test_get_auth_headers_bearer_missing_env_returns_empty(monkeypatch):
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    auth_config = {"type": "bearer"}
    headers = get_auth_headers(auth_config)
    assert headers == {}


def test_get_auth_headers_apikey_header_returns_correct_header(monkeypatch):
    monkeypatch.setenv("API_KEY", "abc-key-123")
    auth_config = {"type": "apiKey", "location": "header", "name": "X-Api-Key"}
    headers = get_auth_headers(auth_config)
    assert headers == {"X-Api-Key": "abc-key-123"}


def test_get_auth_headers_apikey_alias_in_field(monkeypatch):
    """AuthModel may serialize location as 'in' when by_alias=True."""
    monkeypatch.setenv("API_KEY", "my-key")
    auth_config = {"type": "apiKey", "in": "header", "name": "X-Custom-Key"}
    headers = get_auth_headers(auth_config)
    assert headers == {"X-Custom-Key": "my-key"}


def test_get_auth_headers_apikey_query_param_returns_empty(monkeypatch):
    """Query-param apiKey is not supported in 4.1 — returns empty dict."""
    monkeypatch.setenv("API_KEY", "qp-key")
    auth_config = {"type": "apiKey", "location": "query", "name": "api_key"}
    headers = get_auth_headers(auth_config)
    assert headers == {}


def test_get_auth_headers_none_config_returns_empty():
    assert get_auth_headers(None) == {}


def test_get_auth_headers_unknown_type_returns_empty():
    assert get_auth_headers({"type": "oauth2"}) == {}


# ── build_request_url ─────────────────────────────────────────────────────────


def test_build_request_url_basic():
    url = build_request_url("https://api.example.com", "/users")
    assert url == "https://api.example.com/users"


def test_build_request_url_strips_trailing_slash():
    url = build_request_url("https://api.example.com/", "/users")
    assert url == "https://api.example.com/users"


def test_build_request_url_substitutes_path_params():
    url = build_request_url(
        "https://api.example.com",
        "/users/{id}/posts/{post_id}",
        {"id": "42", "post_id": "99"},
    )
    assert url == "https://api.example.com/users/42/posts/99"


def test_build_request_url_no_path_params_leaves_placeholders():
    url = build_request_url("https://api.example.com", "/items/{item_id}")
    assert url == "https://api.example.com/items/{item_id}"


def test_build_request_url_path_without_leading_slash():
    url = build_request_url("https://api.example.com", "health")
    assert url == "https://api.example.com/health"


# ── execute_single_test ───────────────────────────────────────────────────────


def _make_response(
    status_code: int, body: Union[dict, str], content_type: str = "application/json"
):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"content-type": content_type}
    if content_type == "application/json":
        mock_resp.json.return_value = body
    else:
        mock_resp.text = body
    return mock_resp


def test_execute_single_test_success_json_body():
    test_case = {
        "id": "tc-1",
        "title": "Get users",
        "endpoint_method": "GET",
        "endpoint_path": "/users",
    }
    mock_resp = _make_response(200, {"users": []})

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        result = execute_single_test(test_case, "https://api.test", {}, 30, 1)

    assert result["actual_status_code"] == 200
    assert result["actual_response_body"] == {"users": []}
    assert result["request_url"] == "https://api.test/users"
    assert result["request_headers"] == {}
    assert result["response_headers"]["content-type"] == "application/json"
    assert result["error_message"] is None
    assert result["attempt_count"] == 1
    assert result["test_id"] == "tc-1"
    assert result["test_title"] == "Get users"
    mock_req.assert_called_once()


def test_execute_single_test_non_json_body_truncated():
    test_case = {
        "id": "tc-2",
        "title": "Get health",
        "endpoint_method": "GET",
        "endpoint_path": "/health",
    }
    mock_resp = _make_response(200, "OK", content_type="text/plain")
    mock_resp.text = "OK"

    with patch("httpx.request", return_value=mock_resp):
        result = execute_single_test(test_case, "https://api.test", {}, 30, 1)

    assert result["actual_status_code"] == 200
    assert result["actual_response_body"] == "OK"


def test_execute_single_test_retry_on_request_error():
    test_case = {
        "id": "tc-3",
        "title": "Failing test",
        "endpoint_method": "POST",
        "endpoint_path": "/submit",
    }
    mock_resp = _make_response(201, {"created": True})

    with patch(
        "httpx.request",
        side_effect=[httpx.RequestError("connection failed"), mock_resp],
    ) as mock_req:
        result = execute_single_test(test_case, "https://api.test", {}, 30, 1)

    assert result["actual_status_code"] == 201
    assert result["attempt_count"] == 2
    assert result["error_message"] is None
    assert mock_req.call_count == 2


def test_execute_single_test_no_retry_when_retry_count_zero():
    test_case = {
        "id": "tc-4",
        "title": "No retry",
        "endpoint_method": "GET",
        "endpoint_path": "/x",
    }
    with patch(
        "httpx.request",
        side_effect=httpx.RequestError("network error"),
    ) as mock_req:
        result = execute_single_test(test_case, "https://api.test", {}, 30, 0)

    assert result["actual_status_code"] is None
    assert result["attempt_count"] == 1
    assert "network error" in result["error_message"]
    assert mock_req.call_count == 1


def test_execute_single_test_exhausted_retries_returns_error():
    test_case = {
        "id": "tc-5",
        "title": "Always fails",
        "endpoint_method": "GET",
        "endpoint_path": "/fail",
    }
    with patch(
        "httpx.request",
        side_effect=httpx.RequestError("timeout"),
    ) as mock_req:
        result = execute_single_test(test_case, "https://api.test", {}, 30, 1)

    assert result["actual_status_code"] is None
    assert result["attempt_count"] == 2
    assert result["error_message"] is not None
    assert mock_req.call_count == 2


def test_execute_single_test_merges_auth_and_extra_headers():
    test_case = {
        "id": "tc-6",
        "title": "With headers",
        "endpoint_method": "GET",
        "endpoint_path": "/data",
        "request_overrides": {"headers": {"Accept": "application/json"}},
    }
    mock_resp = _make_response(200, {})

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        execute_single_test(
            test_case, "https://api.test", {"Authorization": "Bearer tok"}, 30, 1
        )

    call_kwargs = mock_req.call_args
    sent_headers = (
        call_kwargs.kwargs.get("headers") or call_kwargs.args[2]
        if len(call_kwargs.args) > 2
        else call_kwargs.kwargs["headers"]
    )
    assert "Authorization" in sent_headers
    assert "Accept" in sent_headers


def test_execute_single_test_stores_redacted_request_headers():
    test_case = {
        "id": "tc-8",
        "title": "Secret header",
        "endpoint_method": "GET",
        "endpoint_path": "/secure",
        "request_overrides": {"headers": {"X-API-Key": "override-secret"}},
    }
    mock_resp = _make_response(200, {})

    with patch("httpx.request", return_value=mock_resp):
        result = execute_single_test(
            test_case,
            "https://api.test",
            {"Authorization": "Bearer tok"},
            30,
            1,
        )

    assert result["request_headers"]["Authorization"] == "Bearer [REDACTED]"
    assert result["request_headers"]["X-API-Key"] == "[REDACTED]"


def test_execute_single_test_passes_query_params():
    test_case = {
        "id": "tc-7",
        "title": "Query params",
        "endpoint_method": "GET",
        "endpoint_path": "/items",
        "request_overrides": {"query_params": {"filter": "active"}},
    }
    mock_resp = _make_response(200, [])

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        execute_single_test(test_case, "https://api.test", {}, 30, 1)

    call_kwargs = mock_req.call_args
    assert call_kwargs.kwargs.get("params") == {"filter": "active"}
