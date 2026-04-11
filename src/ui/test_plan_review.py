"""Deterministic formatting helpers for the Test Plan Review checkpoint."""

from collections import Counter
from typing import Optional

from src.core.models import ALLOWED_TEST_PRIORITIES


def format_test_category_label(category: str) -> str:
    """Return a human-readable label for a test category key."""
    normalized = str(category or "").strip().replace("_", " ")
    return normalized.title() if normalized else "Unknown"


def extract_destructive_test_groups(
    test_cases: list[dict],
) -> list[dict]:
    """Return destructive tests grouped by endpoint, sorted by method then path.

    Each group: {"endpoint_method": str, "endpoint_path": str, "count": int}.
    Only includes test cases where is_destructive is True.
    """
    counts: dict[tuple[str, str], int] = {}
    for test_case in test_cases or []:
        if not bool(test_case.get("is_destructive")):
            continue
        method = str(test_case.get("endpoint_method") or "").strip().upper()
        path = str(test_case.get("endpoint_path") or "").strip()
        key = (method, path)
        counts[key] = counts.get(key, 0) + 1
    return [
        {"endpoint_method": method, "endpoint_path": path, "count": count}
        for (method, path), count in sorted(counts.items())
    ]


def filter_enabled_test_cases(
    generated_test_cases: list[dict],
    disabled_test_categories: Optional[list[str]] = None,
) -> list[dict]:
    """Return the execution-plan subset with disabled categories removed."""
    disabled_categories = {
        str(category).strip()
        for category in (disabled_test_categories or [])
        if str(category).strip()
    }
    return [
        test_case
        for test_case in (generated_test_cases or [])
        if str(test_case.get("category") or "").strip() not in disabled_categories
    ]


def build_test_plan_review_sections(
    generated_test_cases: list[dict],
    disabled_categories: Optional[list[str]] = None,
) -> list[dict]:
    """Group the full generated plan into deterministic review sections."""
    disabled_categories = {
        str(category).strip()
        for category in (disabled_categories or [])
        if str(category).strip()
    }

    grouped_cases: dict[str, list[dict]] = {}
    for test_case in generated_test_cases or []:
        category = str(test_case.get("category") or "").strip() or "unknown"
        grouped_cases.setdefault(category, []).append(test_case)

    sections: list[dict] = []
    for category, category_cases in grouped_cases.items():
        priority_counts = Counter(
            str(test_case.get("priority") or "").strip() for test_case in category_cases
        )
        is_enabled = category not in disabled_categories

        section_cases = []
        for test_case in category_cases:
            case_copy = dict(test_case)
            case_copy["status"] = "Enabled" if is_enabled else "Excluded"
            case_copy["destructive_warning"] = _build_destructive_warning(case_copy)
            section_cases.append(case_copy)

        sections.append(
            {
                "category": category,
                "label": format_test_category_label(category),
                "is_enabled": is_enabled,
                "priority_counts": {
                    priority: int(priority_counts.get(priority, 0))
                    for priority in ALLOWED_TEST_PRIORITIES
                },
                "test_cases": section_cases,
            }
        )

    sections.sort(key=lambda section: _category_sort_key(section["category"]))
    return sections


def _category_sort_key(category: str) -> tuple[int, str]:
    category_order = (
        "happy_path",
        "missing_data",
        "invalid_format",
        "wrong_type",
        "auth_failure",
        "boundary",
        "duplicate",
        "method_not_allowed",
    )
    try:
        return (category_order.index(category), category)
    except ValueError:
        return (len(category_order), category)


def _build_destructive_warning(test_case: dict) -> Optional[str]:
    if not bool(test_case.get("is_destructive")):
        return None

    method = str(test_case.get("endpoint_method") or "").strip().upper() or "REQUEST"
    path = str(test_case.get("endpoint_path") or "").strip()

    if method == "DELETE":
        prefix = "This test will DELETE data"
    else:
        prefix = "This test may modify data"

    if path:
        return f"{prefix} ({method} {path})."
    return f"{prefix}."
