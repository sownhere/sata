"""OpenAPI/Swagger spec parser.

Canonical location: src.tools.spec_parser
Parses raw OpenAPI 3.0 JSON or YAML strings into the canonical
``parsed_api_model`` dict consumed by all downstream pipeline nodes.

Security note (NFR6-NFR8): Never log or display ``raw_spec`` content.
Error messages must not include raw file content.
"""

import json
from typing import Optional

import yaml
from openapi_spec_validator import validate as _validate_openapi

# ── Public API ──────────────────────────────────────────────────────────────


def parse_openapi_spec(raw_spec: str) -> dict:
    """Parse raw OpenAPI 3.0 JSON or YAML string into parsed_api_model dict.

    Returns a dict matching the canonical schema:
        {endpoints: [...], auth: {...}, title: str, version: str}

    Raises ValueError with a human-readable message on any failure.
    """
    spec = _load_spec(raw_spec)
    _validate_structure(spec)
    info = spec.get("info") or {}
    return {
        "endpoints": _extract_endpoints(spec),
        "auth": _extract_auth(spec),
        "title": info.get("title", "Unknown API"),
        "version": str(info.get("version", "unknown")),
    }


# ── Internal helpers ────────────────────────────────────────────────────────


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve an internal JSON Pointer $ref within the spec.

    Returns {} for external $refs or unresolvable paths.
    """
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    node = spec
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _load_spec(raw_spec: str) -> dict:
    """Try JSON first, then YAML. Raise ValueError on both failures."""
    try:
        return json.loads(raw_spec)
    except json.JSONDecodeError:
        pass
    try:
        result = yaml.safe_load(raw_spec)
        if isinstance(result, dict):
            return result
        raise ValueError(
            "File content is not a valid OpenAPI spec (not a YAML mapping)."
        )
    except yaml.YAMLError:
        raise ValueError("Could not parse file as JSON or YAML: invalid format.")


def _validate_structure(spec: dict) -> None:
    """Validate minimal OpenAPI 3.x structure, then run full spec validation."""
    if "openapi" not in spec:
        raise ValueError("Not an OpenAPI spec: missing 'openapi' version field.")
    if not str(spec.get("openapi", "")).startswith("3."):
        raise ValueError(f"Only OpenAPI 3.x is supported. Found: {spec.get('openapi')}")
    if "paths" not in spec:
        raise ValueError("OpenAPI spec has no 'paths' — no endpoints to extract.")
    try:
        _validate_openapi(spec)
    except Exception as e:
        first_line = (
            str(e).splitlines()[0].strip()
            if str(e).strip()
            else "Spec structure is invalid."
        )
        raise ValueError(f"OpenAPI spec validation failed: {first_line}")


def _extract_endpoints(spec: dict) -> list:
    """Extract all path + method combinations into canonical endpoint dicts."""
    endpoints: list[dict] = []
    paths = spec.get("paths") or {}
    global_security = spec.get("security", [])

    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_params = path_item.get("parameters", [])
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            op_security = operation.get("security", global_security)
            endpoints.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "parameters": _extract_parameters(
                        path_params, operation.get("parameters", []), spec
                    ),
                    "request_body": _extract_request_body(
                        operation.get("requestBody"), spec
                    ),
                    "response_schemas": _extract_responses(
                        operation.get("responses", {}), spec
                    ),
                    "auth_required": bool(op_security),
                    "tags": operation.get("tags", []),
                }
            )
    return endpoints


def _extract_parameters(path_params: list, op_params: list, spec: dict) -> list:
    """Merge path-level and operation-level params, resolving $refs."""

    def _resolve_one(p: dict) -> Optional[dict]:
        if "$ref" in p:
            resolved = _resolve_ref(spec, p["$ref"])
            return resolved if resolved else None
        return p

    merged: dict = {}
    for p in path_params:
        if not isinstance(p, dict):
            continue
        r = _resolve_one(p)
        if r:
            merged[(r.get("name"), r.get("in"))] = r
    for p in op_params:
        if not isinstance(p, dict):
            continue
        r = _resolve_one(p)
        if r:
            merged[(r.get("name"), r.get("in"))] = r

    return [
        {
            "name": p.get("name"),
            "in": p.get("in"),
            "required": p.get("required", False),
            "schema": p.get("schema", {}),
            "description": p.get("description"),
        }
        for p in merged.values()
    ]


def _extract_request_body(request_body: Optional[dict], spec: dict) -> Optional[dict]:
    """Extract request body schema if present, resolving $refs."""
    if not request_body or not isinstance(request_body, dict):
        return None
    if "$ref" in request_body:
        request_body = _resolve_ref(spec, request_body["$ref"])
        if not request_body:
            return None
    content = request_body.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema") or {}
        if isinstance(schema, dict) and "$ref" in schema:
            schema = _resolve_ref(spec, schema["$ref"]) or {}
        return schema
    for media_obj in content.values():
        if isinstance(media_obj, dict):
            schema = media_obj.get("schema") or {}
            if isinstance(schema, dict) and "$ref" in schema:
                schema = _resolve_ref(spec, schema["$ref"]) or {}
            return schema
    return None


def _extract_responses(responses: dict, spec: dict) -> dict:
    """Extract response schemas keyed by status code, resolving $refs."""
    result = {}
    for status, resp in responses.items():
        if not isinstance(resp, dict):
            continue
        if "$ref" in resp:
            resp = _resolve_ref(spec, resp["$ref"])
            if not resp:
                result[str(status)] = ""
                continue
        content = resp.get("content", {})
        if "application/json" in content:
            schema = content["application/json"].get("schema") or {}
            if isinstance(schema, dict) and "$ref" in schema:
                schema = _resolve_ref(spec, schema["$ref"]) or {}
            result[str(status)] = schema
        else:
            result[str(status)] = resp.get("description", "")
    return result


def _extract_auth(spec: dict) -> dict:
    """Extract primary auth scheme from securitySchemes."""
    schemes = spec.get("components", {}).get("securitySchemes", {})
    for name, scheme in schemes.items():
        if not isinstance(scheme, dict):
            continue
        stype = scheme.get("type", "")
        if stype == "http":
            http_scheme = scheme.get("scheme", "").lower()
            return {
                "type": "bearer" if http_scheme == "bearer" else "basic",
                "scheme": scheme.get("scheme"),
                "in": "header",
                "name": "Authorization",
            }
        elif stype == "apiKey":
            return {
                "type": "api_key",
                "scheme": None,
                "in": scheme.get("in"),
                "name": scheme.get("name"),
            }
        elif stype == "oauth2":
            return {"type": "oauth2", "scheme": None, "in": None, "name": None}
        elif stype == "openIdConnect":
            return {
                "type": "openIdConnect",
                "scheme": None,
                "in": None,
                "name": None,
            }
    return {"type": None, "scheme": None, "in": None, "name": None}
