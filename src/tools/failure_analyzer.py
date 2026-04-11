"""LLM-powered failure analysis tool — groups test failures into patterns.

Canonical location: src.tools.failure_analyzer
Sends only safe, non-sensitive fields to the LLM. Never sends auth headers,
API keys, tokens, or raw response bodies.
"""

import json
import os
from pathlib import Path
from typing import Optional

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "result_analysis.md"

# Safe fields to include in the LLM prompt — never response body or headers
_SAFE_FIELDS = (
    "test_id",
    "test_title",
    "endpoint_method",
    "endpoint_path",
    "expected_status_code",
    "actual_status_code",
    "validation_errors",
)
_CONNECT_ERROR_TERMS = (
    "connection",
    "connect",
    "unreachable",
    "timeout",
    "dns",
    "refused",
)


def analyze_failures(failed_results: list, llm=None) -> dict:
    """Analyze failed test results and return grouped patterns + explanations.

    Args:
        failed_results: List of result dicts where ``passed == False``.
                        Only safe fields are forwarded to the LLM.
        llm: Optional LLM instance for injection in tests.
              If None, a real ChatOpenAI client is built from env vars.

    Returns:
        Dict with keys: ``patterns``, ``explanations``, ``all_passed``.
        On LLM JSON parse failure: also includes ``parse_error``.
    """
    if not failed_results:
        return {
            "patterns": [],
            "explanations": [],
            "all_passed": True,
            "all_failed": False,
            "next_test_suggestions": [],
            "smart_diagnosis": None,
        }

    safe_payload = [
        {field: r.get(field) for field in _SAFE_FIELDS} for r in failed_results
    ]

    prompt_text = _load_prompt() + "\n" + json.dumps(safe_payload, indent=2)
    active_llm = llm or _build_llm()

    response = active_llm.invoke([{"role": "user", "content": prompt_text}])
    raw = (response.content or "").strip()

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "patterns": [],
            "explanations": [],
            "all_passed": False,
            "all_failed": False,
            "next_test_suggestions": [],
            "smart_diagnosis": None,
            "parse_error": str(exc),
        }

    return {
        "patterns": parsed.get("patterns") or [],
        "explanations": parsed.get("explanations") or [],
        "all_passed": False,
        "all_failed": False,
        "next_test_suggestions": [],
        "smart_diagnosis": None,
    }


def suggest_next_test_scenarios(
    test_results: list[dict],
    parsed_api_model: Optional[dict],
    test_cases: Optional[list[dict]] = None,
) -> list[str]:
    """Return deterministic follow-up suggestions for all-pass runs."""
    if not test_results or not all(result.get("passed") for result in test_results):
        return []

    suggestions: list[str] = []
    endpoints = (parsed_api_model or {}).get("endpoints") or []
    categories = {str(case.get("category") or "") for case in (test_cases or [])}
    methods = {str(endpoint.get("method") or "").upper() for endpoint in endpoints}
    auth = (parsed_api_model or {}).get("auth") or {}

    suggestions.append(
        "Re-run the strongest P1 flows with production-like data "
        "to confirm the passing baseline holds under realistic payloads."
    )
    if "boundary" not in categories:
        suggestions.append(
            "Add boundary-value coverage for IDs, pagination, and optional "
            "query parameters to probe limits that the current run did not stress."
        )
    if auth and auth.get("type"):
        suggestions.append(
            f"Exercise expired or insufficient {auth.get('type')} credentials "
            "to confirm auth failures are handled safely without leaking secrets."
        )
    if {"POST", "PUT", "PATCH", "DELETE"} & methods:
        suggestions.append(
            "Add state-transition checks that compare create/update/delete "
            "flows across consecutive requests so regressions are caught "
            "beyond single-call happy paths."
        )
    if len(suggestions) < 3:
        suggestions.append(
            "Broaden schema assertions for optional fields and response "
            "variants so contract drift is caught even when status codes stay green."
        )
    return suggestions[:3]


def diagnose_all_failed_results(
    test_results: list[dict],
    parsed_api_model: Optional[dict],
) -> Optional[dict]:
    """Return one best-fit systemic diagnosis for all-failed runs."""
    results = list(test_results or [])
    if not results or any(result.get("passed") for result in results):
        return None

    auth = (parsed_api_model or {}).get("auth") or {}
    statuses = [result.get("actual_status_code") for result in results]
    error_text = " ".join(
        " ".join(
            [
                str(result.get("error_message") or ""),
                " ".join(result.get("validation_errors") or []),
            ]
        )
        for result in results
    ).lower()

    if auth and _looks_like_auth_failure(statuses, error_text):
        auth_label = auth.get("scheme") or auth.get("type") or "configured auth"
        location = auth.get("location") or auth.get("in") or "header"
        return {
            "category": "auth_misconfiguration",
            "confidence": "high",
            "message": (
                "Every request is failing like an authentication issue. "
                f"Verify the {auth_label} credential sent via {location}, "
                "confirm the token/key is current, "
                "and re-run without exposing the secret value."
            ),
        }

    if _looks_like_wrong_base_url(statuses):
        return {
            "category": "wrong_base_url",
            "confidence": "medium",
            "message": (
                "Every request is resolving to a missing route. "
                "Check TARGET_API_URL and any base-path configuration "
                "to confirm the app is pointing at the correct API root."
            ),
        }

    if _looks_like_unreachable_api(statuses, error_text):
        return {
            "category": "api_unreachable",
            "confidence": "high",
            "message": (
                "The target API looks unreachable or unavailable. "
                "Check TARGET_API_URL, DNS/network access, and whether the "
                "sample API is temporarily down before re-running."
            ),
        }

    return {
        "category": "missing_setup_step",
        "confidence": "medium",
        "message": (
            "The failures look systemic but reachable, which often means "
            "a required setup step is missing. Verify prerequisite seed data, "
            "environment bootstrap steps, or dependent resources before re-running."
        ),
    }


def _load_prompt() -> str:
    """Load and return the result_analysis prompt (strips the markdown heading)."""
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Strip the first line if it's the markdown heading
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _build_llm():
    from langchain_openai import ChatOpenAI

    from src.core.config import get_settings

    settings = get_settings()
    return ChatOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_CHAT_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
    )


def _looks_like_auth_failure(statuses: list[object], error_text: str) -> bool:
    if statuses and all(
        status in {401, 403} for status in statuses if status is not None
    ):
        return True
    return any(
        term in error_text
        for term in ("unauthorized", "forbidden", "token", "api key", "apikey")
    )


def _looks_like_wrong_base_url(statuses: list[object]) -> bool:
    concrete_statuses = [status for status in statuses if status is not None]
    return bool(concrete_statuses) and all(
        status == 404 for status in concrete_statuses
    )


def _looks_like_unreachable_api(statuses: list[object], error_text: str) -> bool:
    if statuses and all(status is None for status in statuses):
        return True
    return any(term in error_text for term in _CONNECT_ERROR_TERMS)
