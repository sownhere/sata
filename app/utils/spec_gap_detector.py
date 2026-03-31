"""Deterministic gap detection for parsed OpenAPI specs.

The detector intentionally uses both the original raw spec and the parsed API
model so it can identify ambiguity without widening the canonical
``parsed_api_model`` contract.
"""

import json
import re
from typing import Optional

import yaml


WRITE_METHODS = {"POST", "PUT", "PATCH"}
COMMON_ERROR_STATUS_CODES = ["400", "401", "403", "404", "409", "422", "429", "500"]
AUTH_OPTIONS = ["bearer", "basic", "api_key", "oauth2", "openIdConnect", "none"]


def detect_spec_gaps(raw_spec: str, parsed_api_model: dict) -> list[dict]:
    """Return deterministic, high-signal gap questions for the parsed spec."""
    spec = _load_raw_spec(raw_spec)
    operations = _extract_raw_operations(spec)
    gaps: list[dict] = []

    for endpoint in parsed_api_model.get("endpoints", []):
        method = str(endpoint.get("method", "")).upper()
        path = str(endpoint.get("path", ""))
        endpoint_key = f"{method} {path}"
        raw_operation = operations.get((path, method), {})

        if _has_missing_success_response(endpoint):
            gaps.append(
                _gap_record(
                    endpoint,
                    "missing_success_response",
                    "response_schemas.2xx",
                    (
                        f"Endpoint {endpoint_key} has no defined success response schema"
                        " - what does a successful response return?"
                    ),
                    "text_area",
                )
            )

        if method in WRITE_METHODS and not endpoint.get("request_body"):
            gaps.append(
                _gap_record(
                    endpoint,
                    "missing_request_body",
                    "request_body",
                    (
                        f"Endpoint {endpoint_key} looks like a write operation"
                        " - what request body fields are expected?"
                    ),
                    "text_area",
                )
            )

        if _has_missing_error_responses(endpoint):
            gaps.append(
                _gap_record(
                    endpoint,
                    "missing_error_responses",
                    "response_schemas.errors",
                    (
                        f"Endpoint {endpoint_key} only documents success responses"
                        " - which error status codes should be expected?"
                    ),
                    "multiselect",
                    COMMON_ERROR_STATUS_CODES,
                )
            )

        if _has_auth_ambiguity(spec, raw_operation):
            gaps.append(
                _gap_record(
                    endpoint,
                    "auth_ambiguity",
                    "auth.type",
                    f"Endpoint {endpoint_key} has unclear auth requirements - which auth type should Sata use?",
                    "select",
                    AUTH_OPTIONS,
                )
            )

    return gaps


def _load_raw_spec(raw_spec: str) -> dict:
    try:
        loaded = json.loads(raw_spec)
    except json.JSONDecodeError:
        try:
            loaded = yaml.safe_load(raw_spec)
        except yaml.YAMLError as exc:
            raise ValueError("Could not parse spec for gap detection.") from exc

    if not isinstance(loaded, dict):
        raise ValueError("Could not parse spec for gap detection.")
    return loaded


def _extract_raw_operations(spec: dict) -> dict:
    operations: dict[tuple[str, str], dict] = {}
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if str(method).lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "head",
                "options",
            }:
                continue
            if isinstance(operation, dict):
                operations[(str(path), str(method).upper())] = operation
    return operations


def _has_missing_success_response(endpoint: dict) -> bool:
    responses = endpoint.get("response_schemas") or {}
    success_codes = [code for code in responses if str(code).startswith("2")]
    if not success_codes:
        return True

    for code in success_codes:
        response = responses.get(code)
        if isinstance(response, dict) and response:
            return False
        if isinstance(response, str) and response.strip():
            return False
        if response not in (None, "", {}, []):
            return False
    return True


def _has_missing_error_responses(endpoint: dict) -> bool:
    responses = endpoint.get("response_schemas") or {}
    if not responses:
        return True
    return not any(not str(code).startswith("2") for code in responses)


def _has_auth_ambiguity(spec: dict, operation: dict) -> bool:
    effective_security = operation.get("security", spec.get("security", []))

    if effective_security == []:
        return False
    if not effective_security:
        return False

    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    for requirement in effective_security:
        if not isinstance(requirement, dict):
            return True
        for scheme_name in requirement:
            scheme = schemes.get(scheme_name)
            if not isinstance(scheme, dict):
                return True
            if _scheme_is_supported(scheme):
                return False
    return True


def _scheme_is_supported(scheme: dict) -> bool:
    scheme_type = scheme.get("type")
    if scheme_type == "http":
        http_scheme = str(scheme.get("scheme", "")).lower()
        return http_scheme in {"bearer", "basic"}
    if scheme_type == "apiKey":
        return True
    if scheme_type in {"oauth2", "openIdConnect"}:
        return True
    return False


def _gap_record(
    endpoint: dict,
    gap_type: str,
    field: str,
    question: str,
    input_type: str,
    options: Optional[list[str]] = None,
) -> dict:
    method = str(endpoint.get("method", "")).upper()
    path = str(endpoint.get("path", ""))
    endpoint_key = f"{method} {path}"
    return {
        "id": _gap_id(method, path, gap_type),
        "endpoint_key": endpoint_key,
        "path": path,
        "method": method,
        "gap_type": gap_type,
        "field": field,
        "question": question,
        "input_type": input_type,
        "options": options,
    }


def _gap_id(method: str, path: str, suffix: str) -> str:
    normalized_path = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    normalized_suffix = suffix.replace("_", "-")
    return f"{method.lower()}-{normalized_path}-{normalized_suffix}"
