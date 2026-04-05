"""LLM-assisted test case generation and deterministic validation utilities.

Canonical location: src.tools.test_case_generator
"""

import json
import os
from collections import Counter
from typing import Any, Optional

from pydantic import ValidationError

from src.core.config import get_settings
from src.core.models import (
    ALLOWED_TEST_CATEGORIES,
    ALLOWED_TEST_PRIORITIES,
    TestCaseModel,
)
from src.core.prompts import load_prompt

DEFAULT_PRIORITY_BY_CATEGORY = {
    "happy_path": "P1",
    "missing_data": "P1",
    "invalid_format": "P2",
    "wrong_type": "P2",
    "auth_failure": "P1",
    "boundary": "P2",
    "duplicate": "P3",
    "method_not_allowed": "P2",
}

DEFAULT_STATUS_BY_CATEGORY = {
    "happy_path": 200,
    "missing_data": 400,
    "invalid_format": 400,
    "wrong_type": 400,
    "auth_failure": 401,
    "boundary": 400,
    "duplicate": 409,
    "method_not_allowed": 405,
}

DESTRUCTIVE_METHODS = {"PUT", "DELETE"}

_CATEGORY_ALIASES = {
    "happy": "happy_path",
    "happy_path": "happy_path",
    "happy_paths": "happy_path",
    "missing_data": "missing_data",
    "missing_field": "missing_data",
    "missing_fields": "missing_data",
    "invalid_format": "invalid_format",
    "wrong_format": "invalid_format",
    "wrong_type": "wrong_type",
    "type_mismatch": "wrong_type",
    "auth_failure": "auth_failure",
    "authentication_failure": "auth_failure",
    "boundary": "boundary",
    "boundary_value": "boundary",
    "duplicate": "duplicate",
    "duplicate_request": "duplicate",
    "method_not_allowed": "method_not_allowed",
    "method_notallowed": "method_not_allowed",
}

_PRIORITY_ALIASES = {
    "P1": "P1",
    "P2": "P2",
    "P3": "P3",
    "HIGH": "P1",
    "CRITICAL": "P1",
    "MEDIUM": "P2",
    "NORMAL": "P2",
    "LOW": "P3",
}


def generate_test_cases_for_model(
    parsed_api_model: dict,
    llm=None,
    retry_count: Optional[int] = None,
) -> dict:
    """Generate test cases for each endpoint in a parsed API model.

    Returns:
        {
            "test_cases": list[dict],          # validated TestCaseModel records
            "failed_endpoints": list[dict],    # [{path, method, error}]
            "category_counts": dict[str, int],
            "priority_counts": dict[str, int],
        }
    """
    model = parsed_api_model or {}
    endpoints = model.get("endpoints") or []
    top_level_auth = model.get("auth") or {}

    if not isinstance(endpoints, list) or not endpoints:
        return {
            "test_cases": [],
            "failed_endpoints": [],
            "category_counts": {},
            "priority_counts": {},
        }

    configured_retry_count = (
        get_settings().execution.retry_count if retry_count is None else retry_count
    )
    # At least one retry after the first attempt (AC 4 / Story 3.1).
    effective_retry_count = max(1, int(configured_retry_count))
    active_llm = llm or _build_llm()

    generated_cases: list[dict] = []
    failed_endpoints: list[dict] = []

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue

        outcome = _generate_endpoint_cases_with_retry(
            endpoint=endpoint,
            top_level_auth=top_level_auth,
            llm=active_llm,
            retry_count=effective_retry_count,
        )

        if outcome["error"] is not None:
            failed_endpoints.append(
                {
                    "path": str(endpoint.get("path") or ""),
                    "method": str(endpoint.get("method") or "").upper(),
                    "error": outcome["error"],
                }
            )
            continue

        generated_cases.extend(outcome["test_cases"])

    category_counts = Counter(case["category"] for case in generated_cases)
    priority_counts = Counter(case["priority"] for case in generated_cases)

    return {
        "test_cases": generated_cases,
        "failed_endpoints": failed_endpoints,
        "category_counts": dict(category_counts),
        "priority_counts": dict(priority_counts),
    }


def filter_test_cases_against_confirmed_spec(
    test_cases: list[dict],
    parsed_api_model: dict,
) -> dict:
    """Discard generated cases that do not map to confirmed spec endpoints/fields."""
    accepted: list[dict] = []
    dropped: list[dict] = []

    endpoint_lookup: dict[tuple[str, str], dict] = {}
    for endpoint in (parsed_api_model or {}).get("endpoints") or []:
        if not isinstance(endpoint, dict):
            continue
        path = str(endpoint.get("path") or "").strip()
        method = str(endpoint.get("method") or "").strip().upper()
        if path and method:
            endpoint_lookup[(method, path)] = endpoint

    for raw_case in test_cases or []:
        try:
            validated_case = TestCaseModel.model_validate(raw_case)
        except ValidationError as exc:
            dropped.append(
                {
                    "reason": "invalid_test_case_shape",
                    "test_case": raw_case,
                    "details": str(exc).splitlines()[0],
                }
            )
            continue

        endpoint_key = (validated_case.endpoint_method, validated_case.endpoint_path)
        endpoint = endpoint_lookup.get(endpoint_key)
        if endpoint is None:
            dropped.append(
                {
                    "reason": "unknown_endpoint",
                    "test_case": validated_case.model_dump(),
                }
            )
            continue

        if validated_case.category == "auth_failure" and not bool(
            endpoint.get("auth_required")
        ):
            dropped.append(
                {
                    "reason": "auth_not_required",
                    "test_case": validated_case.model_dump(),
                }
            )
            continue

        allowed_fields = _extract_known_fields(endpoint)
        unknown_refs = [
            field_ref
            for field_ref in validated_case.field_refs
            if field_ref not in allowed_fields
        ]
        if unknown_refs:
            dropped.append(
                {
                    "reason": "unknown_field_refs",
                    "unknown_fields": unknown_refs,
                    "test_case": validated_case.model_dump(),
                }
            )
            continue

        accepted.append(validated_case.model_dump())

    return {"accepted": accepted, "dropped": dropped}


def _generate_endpoint_cases_with_retry(
    endpoint: dict,
    top_level_auth: dict,
    llm,
    retry_count: int,
) -> dict:
    attempts = retry_count + 1
    last_error: Optional[str] = None

    for _ in range(attempts):
        try:
            return {
                "test_cases": _generate_endpoint_cases(
                    endpoint=endpoint,
                    top_level_auth=top_level_auth,
                    llm=llm,
                ),
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001 - message is returned to node/UI
            last_error = str(exc)

    return {"test_cases": [], "error": last_error or "Unknown generation failure"}


def _generate_endpoint_cases(endpoint: dict, top_level_auth: dict, llm) -> list[dict]:
    endpoint_path = str(endpoint.get("path") or "").strip()
    endpoint_method = str(endpoint.get("method") or "").strip().upper()
    if not endpoint_path or not endpoint_method:
        raise ValueError("Endpoint path/method are required for test generation.")

    applicable_categories = _applicable_categories(endpoint)
    response = llm.invoke(
        _build_generation_messages(
            endpoint=endpoint,
            top_level_auth=top_level_auth,
            required_categories=applicable_categories,
        )
    )
    payload = _load_json_payload(_response_text(response))
    raw_cases = payload if isinstance(payload, list) else payload.get("test_cases")
    if not isinstance(raw_cases, list):
        raise ValueError("Generator response must include a test_cases list.")

    normalized_cases: list[dict] = []
    for index, raw_case in enumerate(raw_cases, start=1):
        candidate = _normalize_test_case_record(
            raw_case=raw_case,
            endpoint=endpoint,
            ordinal=index,
        )
        if candidate is not None:
            normalized_cases.append(candidate)

    existing_categories = {case["category"] for case in normalized_cases}
    next_ordinal = len(normalized_cases) + 1
    for category in applicable_categories:
        if category in existing_categories:
            continue
        normalized_cases.append(
            _build_fallback_case(
                endpoint=endpoint,
                category=category,
                ordinal=next_ordinal,
            )
        )
        next_ordinal += 1

    validated_cases: list[dict] = []
    seen_ids: set[str] = set()
    for index, candidate in enumerate(normalized_cases, start=1):
        if (
            not endpoint.get("auth_required")
            and candidate["category"] == "auth_failure"
        ):
            continue
        if candidate["id"] in seen_ids:
            candidate["id"] = _build_case_id(endpoint, candidate["category"], index)
        model = TestCaseModel.model_validate(candidate)
        validated = model.model_dump()
        seen_ids.add(validated["id"])
        validated_cases.append(validated)

    return validated_cases


def _build_generation_messages(
    endpoint: dict,
    top_level_auth: dict,
    required_categories: tuple[str, ...],
) -> list[dict]:
    payload = {
        "endpoint": endpoint,
        "top_level_auth": top_level_auth or {},
        "required_categories": list(required_categories),
        "allowed_priorities": list(ALLOWED_TEST_PRIORITIES),
    }
    return [
        {"role": "system", "content": load_prompt("test_generation")},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=True, indent=2),
        },
    ]


def _normalize_test_case_record(
    raw_case: Any,
    endpoint: dict,
    ordinal: int,
) -> Optional[dict]:
    if not isinstance(raw_case, dict):
        return None

    category = _normalize_category(raw_case.get("category") or raw_case.get("type"))
    if category is None:
        return None

    endpoint_path = str(
        raw_case.get("endpoint_path") or endpoint.get("path") or ""
    ).strip()
    endpoint_method = (
        str(raw_case.get("endpoint_method") or endpoint.get("method") or "")
        .strip()
        .upper()
    )
    priority = _normalize_priority(raw_case.get("priority"), category)
    case_id = str(
        raw_case.get("id") or _build_case_id(endpoint, category, ordinal)
    ).strip()

    field_refs = raw_case.get("field_refs")
    if isinstance(field_refs, str):
        normalized_field_refs = [field_refs]
    elif isinstance(field_refs, list):
        normalized_field_refs = [str(item) for item in field_refs]
    else:
        normalized_field_refs = []

    request_overrides = raw_case.get("request_overrides")
    if not isinstance(request_overrides, dict):
        request_overrides = {}

    expected = raw_case.get("expected")
    if not isinstance(expected, dict):
        expected = {}
    if "status_code" not in expected:
        expected["status_code"] = DEFAULT_STATUS_BY_CATEGORY[category]

    return {
        "id": case_id,
        "endpoint_path": endpoint_path,
        "endpoint_method": endpoint_method,
        "category": category,
        "priority": priority,
        "title": str(
            raw_case.get("title") or _default_title(endpoint, category)
        ).strip(),
        "description": str(
            raw_case.get("description") or _default_description(endpoint, category)
        ).strip(),
        "request_overrides": request_overrides,
        "expected": expected,
        "is_destructive": bool(raw_case.get("is_destructive"))
        or endpoint_method in DESTRUCTIVE_METHODS,
        "field_refs": normalized_field_refs,
    }


def _build_fallback_case(endpoint: dict, category: str, ordinal: int) -> dict:
    endpoint_method = str(endpoint.get("method") or "").strip().upper()
    field_ref = _first_field_ref(endpoint)
    field_refs = (
        [field_ref]
        if field_ref
        and category
        in {
            "missing_data",
            "invalid_format",
            "wrong_type",
            "boundary",
            "duplicate",
        }
        else []
    )

    return {
        "id": _build_case_id(endpoint, category, ordinal),
        "endpoint_path": str(endpoint.get("path") or "").strip(),
        "endpoint_method": endpoint_method,
        "category": category,
        "priority": DEFAULT_PRIORITY_BY_CATEGORY[category],
        "title": _default_title(endpoint, category),
        "description": _default_description(endpoint, category),
        "request_overrides": {},
        "expected": {"status_code": DEFAULT_STATUS_BY_CATEGORY[category]},
        "is_destructive": endpoint_method in DESTRUCTIVE_METHODS,
        "field_refs": field_refs,
    }


def _default_title(endpoint: dict, category: str) -> str:
    method = str(endpoint.get("method") or "").strip().upper()
    path = str(endpoint.get("path") or "").strip()
    return f"{method} {path} {category.replace('_', ' ')}"


def _default_description(endpoint: dict, category: str) -> str:
    method = str(endpoint.get("method") or "").strip().upper()
    path = str(endpoint.get("path") or "").strip()
    return f"Auto-generated {category.replace('_', ' ')} scenario for {method} {path}."


def _normalize_category(value: Any) -> Optional[str]:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    return _CATEGORY_ALIASES.get(
        normalized, normalized if normalized in ALLOWED_TEST_CATEGORIES else None
    )


def _normalize_priority(value: Any, category: str) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return DEFAULT_PRIORITY_BY_CATEGORY[category]
    normalized = _PRIORITY_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_TEST_PRIORITIES:
        return DEFAULT_PRIORITY_BY_CATEGORY[category]
    return normalized


def _applicable_categories(endpoint: dict) -> tuple[str, ...]:
    categories = [
        "happy_path",
        "missing_data",
        "invalid_format",
        "wrong_type",
        "boundary",
        "duplicate",
        "method_not_allowed",
    ]
    if bool(endpoint.get("auth_required")):
        categories.append("auth_failure")
    return tuple(categories)


def _build_case_id(endpoint: dict, category: str, ordinal: int) -> str:
    method = str(endpoint.get("method") or "").strip().lower()
    path = str(endpoint.get("path") or "").strip().strip("/")
    path_key = path.replace("/", "-").replace("{", "").replace("}", "") or "root"
    return f"tc-{method}-{path_key}-{category}-{ordinal}"


def _first_field_ref(endpoint: dict) -> Optional[str]:
    for parameter in endpoint.get("parameters") or []:
        if isinstance(parameter, dict) and str(parameter.get("name") or "").strip():
            return str(parameter["name"]).strip()

    request_body = endpoint.get("request_body") or {}
    if isinstance(request_body, dict):
        properties = request_body.get("properties") or {}
        if isinstance(properties, dict):
            for field_name in properties:
                normalized = str(field_name or "").strip()
                if normalized:
                    return normalized
    return None


def _extract_known_fields(endpoint: dict) -> set[str]:
    fields: set[str] = set()
    for parameter in endpoint.get("parameters") or []:
        if isinstance(parameter, dict):
            name = str(parameter.get("name") or "").strip()
            if name:
                fields.add(name)

    request_body = endpoint.get("request_body") or {}
    if isinstance(request_body, dict):
        properties = request_body.get("properties") or {}
        if isinstance(properties, dict):
            for field_name in properties:
                normalized = str(field_name or "").strip()
                if normalized:
                    fields.add(normalized)
    return fields


def _build_llm():
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    return ChatOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_CHAT_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
    )


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    raise ValueError("Test generation did not return text content.")


def _load_json_payload(text: str):
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        stripped = "\n".join(lines)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("Test generation must return valid JSON.") from exc
    if not isinstance(payload, (dict, list)):
        raise ValueError("Test generation must return a JSON object or list.")
    return payload
