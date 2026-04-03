"""Utilities for fetching remote OpenAPI specs.

Canonical location: src.tools.spec_fetcher
Security note: never log fetched response bodies or include them in
user-facing error messages.
"""

import ipaddress
import socket
from urllib import error, parse
from urllib import request as _urllib_request

DEFAULT_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB


class _NoRedirectHandler(_urllib_request.HTTPRedirectHandler):
    """Raise ValueError instead of following HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError(
            f"URL redirected (HTTP {code}). Please provide the final spec URL directly."
        )


# Opener with redirect-following disabled; exposed at module level for test patching.
_OPENER = _urllib_request.build_opener(_NoRedirectHandler())


def fetch_spec_from_url(url: str) -> str:
    """Fetch raw spec text from a public HTTP(S) URL.

    Raises:
        ValueError: if the URL is invalid, targets a private address, is
        unreachable, times out, redirects, or returns a non-200 response.
    """
    parsed = parse.urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Please enter a valid public http:// or https:// URL for the spec."
        )

    if _is_private_host(parsed.hostname or ""):
        raise ValueError(
            "URL must point to a public server."
            " Private and internal addresses are not allowed."
        )

    req = _urllib_request.Request(
        url,
        headers={
            "User-Agent": "sata-spec-fetcher/1.0",
            "Accept": "application/json, application/yaml, text/yaml, */*",
        },
    )

    try:
        with _OPENER.open(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", None)
            if status is not None and status != 200:
                raise ValueError(
                    f"Could not fetch the spec URL. Server returned status {status}."
                )
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        raise ValueError(
            f"Could not fetch the spec URL. Server returned status {exc.code}."
        ) from exc
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            raise ValueError(
                "Could not reach URL - the request timed out."
                " Check the address or your connection."
            ) from exc
        raise ValueError(
            "Could not reach URL - check the address or your connection."
        ) from exc
    except OSError as exc:
        raise ValueError(
            "Could not reach URL - check the address or your connection."
        ) from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(
            "The spec URL returned a response that is too large to process"
            " (limit: 10 MB)."
        )

    return body.decode("utf-8", errors="replace")


# ── Internal helpers ────────────────────────────────────────────────────────


def _is_private_host(hostname: str) -> bool:
    """Return True if hostname is localhost or a private/reserved IP address."""
    if not hostname:
        return True
    if hostname.lower().rstrip(".") in {"localhost", "localhost.localdomain"}:
        return True
    host = hostname.strip("[]")
    try:
        addr = ipaddress.ip_address(host)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_unspecified
        )
    except ValueError:
        return False
