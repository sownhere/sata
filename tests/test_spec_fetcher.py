import socket
import urllib.error

import pytest

from app.utils.spec_fetcher import fetch_spec_from_url, _OPENER


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self, max_bytes: int = -1) -> bytes:
        return self._body if max_bytes < 0 else self._body[:max_bytes]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestSpecFetcher:
    def test_fetch_success_returns_text(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            return _FakeResponse(b'{"openapi":"3.0.0","paths":{}}', status=200)

        monkeypatch.setattr(_OPENER, "open", _open)

        raw = fetch_spec_from_url("https://example.com/openapi.json")
        assert '"openapi"' in raw

    def test_rejects_non_http_scheme(self):
        with pytest.raises(ValueError) as e:
            fetch_spec_from_url("file:///etc/passwd")
        assert "http" in str(e.value).lower()

    def test_rejects_empty_url(self):
        with pytest.raises(ValueError, match="valid public"):
            fetch_spec_from_url("")

    def test_rejects_whitespace_url(self):
        with pytest.raises(ValueError, match="valid public"):
            fetch_spec_from_url("   ")

    def test_rejects_localhost(self):
        with pytest.raises(ValueError, match="public server"):
            fetch_spec_from_url("http://localhost/openapi.json")

    def test_rejects_loopback_ip(self):
        with pytest.raises(ValueError, match="public server"):
            fetch_spec_from_url("http://127.0.0.1/openapi.json")

    def test_rejects_cloud_metadata_ip(self):
        with pytest.raises(ValueError, match="public server"):
            fetch_spec_from_url("http://169.254.169.254/latest/meta-data/")

    def test_non_200_is_fetch_error(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            return _FakeResponse(b"nope", status=404)

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError) as e:
            fetch_spec_from_url("https://example.com/missing")
        msg = str(e.value).lower()
        assert "could not" in msg or "status" in msg

    def test_http_error_is_fetch_error(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            raise urllib.error.HTTPError(
                url="https://example.com",
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=None,
            )

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError) as e:
            fetch_spec_from_url("https://example.com/forbidden")
        assert "403" in str(e.value)

    def test_url_error_is_fetch_error(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            raise urllib.error.URLError("DNS failure")

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError) as e:
            fetch_spec_from_url("https://nope.invalid/openapi.json")
        assert "could not" in str(e.value).lower() or "reach" in str(e.value).lower()

    def test_socket_timeout_is_fetch_error(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            raise urllib.error.URLError(socket.timeout("timed out"))

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError) as e:
            fetch_spec_from_url("https://slow.example.com/openapi.json")
        assert "timed out" in str(e.value).lower()

    def test_bare_oserror_is_fetch_error(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            raise OSError("connection reset")

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError, match="Could not reach URL"):
            fetch_spec_from_url("https://example.com/openapi.json")

    def test_response_size_limit(self, monkeypatch):
        oversized = b"x" * (10 * 1024 * 1024 + 2)

        def _open(_request, timeout):  # noqa: ARG001
            return _FakeResponse(oversized, status=200)

        monkeypatch.setattr(_OPENER, "open", _open)

        with pytest.raises(ValueError, match="too large"):
            fetch_spec_from_url("https://example.com/huge.json")

    def test_decode_is_robust(self, monkeypatch):
        def _open(_request, timeout):  # noqa: ARG001
            return _FakeResponse(b"\xff\xfe\xfd", status=200)

        monkeypatch.setattr(_OPENER, "open", _open)

        raw = fetch_spec_from_url("https://example.com/weird")
        assert isinstance(raw, str)

    def test_html_response_is_returned_as_text_not_fetch_error(self, monkeypatch):
        """AC3: a 200 HTML response is a fetch success; parse failure happens downstream."""

        def _open(_request, timeout):  # noqa: ARG001
            return _FakeResponse(
                b"<html><body>Not an API spec</body></html>", status=200
            )

        monkeypatch.setattr(_OPENER, "open", _open)

        raw = fetch_spec_from_url("https://example.com/wrong-page")
        assert isinstance(raw, str)
        assert "<html>" in raw  # fetcher returns it; parse_openapi_spec will reject it
