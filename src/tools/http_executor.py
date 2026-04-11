"""Deterministic HTTP execution tools for test case dispatch.

Canonical location: src.tools.http_executor
Reads auth credentials from os.environ only — never as function parameters.
No LLM calls, no side-effects beyond network I/O.
"""

import os
from typing import Optional

import httpx

from src.tools.redaction import redact_headers


def get_auth_headers(auth_config: Optional[dict]) -> dict:
    """Build auth headers from env credentials based on auth_config.

    Reads credentials from os.environ only (API_BEARER_TOKEN, API_KEY).
    Never accepts credentials as parameters (security boundary).

    Args:
        auth_config: Serialized AuthModel dict from parsed_api_model["auth"].
                     Supports keys "type", "name", "location" or "in".

    Returns:
        Dict of headers to merge into the request. Empty dict if no creds
        are configured or auth_config is None/unrecognised.
    """
    if not auth_config:
        return {}

    auth_type = (auth_config.get("type") or "").lower()

    if auth_type == "bearer":
        token = os.environ.get("API_BEARER_TOKEN", "").strip()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    if auth_type == "apikey":
        # location field may be serialised as "location" or "in" depending on
        # whether model_dump() was called with by_alias=True.
        location = (auth_config.get("location") or auth_config.get("in") or "").lower()
        name = (auth_config.get("name") or "").strip()

        if location != "header":
            # Query-param apiKey is a known gap — see deferred-work.md
            # ("code review of 4-1-http-test-execution-with-auth-and-retry").
            # Requests against specs that declare `in: query` currently go
            # out unauthenticated rather than fall back noisily; revisit
            # when we plumb auth into request-building.
            return {}

        api_key = os.environ.get("API_KEY", "").strip()
        if not api_key or not name:
            return {}
        return {name: api_key}

    return {}


def build_request_url(
    base_url: str,
    endpoint_path: str,
    path_params: Optional[dict] = None,
) -> str:
    """Build a full request URL by joining base_url and endpoint_path.

    Strips trailing slash from base_url, ensures leading slash on path,
    then substitutes {param} placeholders from path_params.

    Args:
        base_url: Root URL of the target API (e.g. "https://api.example.com").
        endpoint_path: Path template (e.g. "/users/{id}").
        path_params: Dict of placeholder values (e.g. {"id": "123"}).

    Returns:
        Full URL string with placeholders replaced where possible.
    """
    base = base_url.rstrip("/")
    path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"

    url = base + path

    if path_params:
        for key, value in path_params.items():
            url = url.replace(f"{{{key}}}", str(value))

    return url


def execute_single_test(
    test_case: dict,
    base_url: str,
    auth_headers: dict,
    timeout: int,
    retry_count: int,
) -> dict:
    """Execute a single test case as an HTTP request.

    Builds the full URL, merges headers, sends the request via httpx, and
    returns a result dict. Retries once on httpx.RequestError if retry_count >= 1.

    Args:
        test_case: Dict with at minimum "id", "title", "endpoint_method",
                   "endpoint_path", and optional "request_overrides".
        base_url: Root URL of the target API.
        auth_headers: Pre-built auth headers from get_auth_headers().
        timeout: Per-request timeout in seconds.
        retry_count: Number of retries on network error (0 = no retry).

    Returns:
        Result dict with keys: test_id, test_title, endpoint_method,
        endpoint_path, request_url, request_headers, request_body,
        request_query_params, response_headers, actual_status_code,
        actual_response_body, error_message, attempt_count.
    """
    test_id = test_case.get("id", "")
    test_title = test_case.get("title", "")
    method = (test_case.get("endpoint_method") or "GET").upper()
    endpoint_path = test_case.get("endpoint_path", "/")

    overrides = test_case.get("request_overrides") or {}
    path_params = overrides.get("path_params") or {}
    body = overrides.get("body") or {}
    query_params = overrides.get("query_params") or {}
    extra_headers = overrides.get("headers") or {}

    url = build_request_url(base_url, endpoint_path, path_params)
    merged_headers = {**auth_headers, **extra_headers}
    safe_request_headers = redact_headers(merged_headers)

    max_attempts = 1 + (retry_count if retry_count >= 1 else 0)
    last_error: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = httpx.request(
                method=method,
                url=url,
                headers=merged_headers,
                json=body if body else None,
                params=query_params if query_params else None,
                timeout=timeout,
            )
            is_json = "application/json" in response.headers.get("content-type", "")
            if is_json:
                try:
                    actual_body = response.json()
                except Exception:
                    actual_body = response.text[:2000]
            else:
                actual_body = response.text[:2000]

            return {
                "test_id": test_id,
                "test_title": test_title,
                "endpoint_method": method,
                "endpoint_path": endpoint_path,
                "request_url": url,
                "request_headers": safe_request_headers,
                "request_body": body if body else None,
                "request_query_params": query_params if query_params else None,
                "response_headers": redact_headers(dict(response.headers)),
                "actual_status_code": response.status_code,
                "actual_response_body": actual_body,
                "error_message": None,
                "attempt_count": attempt,
            }

        except httpx.RequestError as exc:
            last_error = str(exc)
            if attempt >= max_attempts:
                break
            # else retry

    return {
        "test_id": test_id,
        "test_title": test_title,
        "endpoint_method": method,
        "endpoint_path": endpoint_path,
        "request_url": url,
        "request_headers": safe_request_headers,
        "request_body": body if body else None,
        "request_query_params": query_params if query_params else None,
        "response_headers": {},
        "actual_status_code": None,
        "actual_response_body": None,
        "error_message": last_error,
        "attempt_count": max_attempts,
    }
