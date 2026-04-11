"""Pure view-model helpers for results dashboard, drill-down, and reruns."""

from __future__ import annotations

from collections import Counter, defaultdict

from src.tools.redaction import redact_headers, sanitize_value

PRIORITY_ORDER = ("P1", "P2", "P3")
PRIORITY_RANK = {priority: index for index, priority in enumerate(PRIORITY_ORDER)}
HEATMAP_GLYPHS = {
    "none": "⬜",
    "low": "🟨",
    "medium": "🟧",
    "high": "🟥",
}


def build_run_summary(test_results: list[dict] | None) -> dict:
    """Return deterministic summary counts for a test run."""
    results = list(test_results or [])
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result.get("passed"))
    failed_tests = total_tests - passed_tests
    pass_rate = round((passed_tests / total_tests) * 100, 1) if total_tests else 0.0
    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "pass_rate": pass_rate,
    }


def build_result_rows(
    test_results: list[dict] | None,
    test_cases: list[dict] | None,
    failure_analysis: dict | None = None,
) -> list[dict]:
    """Join execution results with test-plan metadata and explanations."""
    case_by_id = {str(case.get("id")): case for case in (test_cases or [])}
    explanation_by_id = {
        str(explanation.get("test_id")): explanation
        for explanation in ((failure_analysis or {}).get("explanations") or [])
    }

    rows: list[dict] = []
    for result in test_results or []:
        test_id = str(result.get("test_id") or "")
        case = case_by_id.get(test_id, {})
        endpoint_method = str(
            result.get("endpoint_method") or case.get("endpoint_method") or ""
        ).upper()
        endpoint_path = str(
            result.get("endpoint_path") or case.get("endpoint_path") or ""
        )
        rows.append(
            {
                "test_id": test_id,
                "title": result.get("test_title") or case.get("title") or test_id,
                "passed": bool(result.get("passed")),
                "priority": str(case.get("priority") or "P3"),
                "category": str(case.get("category") or "unknown"),
                "endpoint_method": endpoint_method,
                "endpoint_path": endpoint_path,
                "endpoint_label": f"{endpoint_method} {endpoint_path}".strip(),
                "expected_status_code": result.get("expected_status_code"),
                "actual_status_code": result.get("actual_status_code"),
                "validation_errors": list(result.get("validation_errors") or []),
                "attempt_count": int(result.get("attempt_count") or 0),
                "request_url": result.get("request_url"),
                "request_headers": redact_headers(result.get("request_headers") or {}),
                "request_query_params": sanitize_value(
                    result.get("request_query_params") or {}
                ),
                "request_body": sanitize_value(result.get("request_body")),
                "response_headers": redact_headers(
                    result.get("response_headers") or {}
                ),
                "response_body": sanitize_value(result.get("actual_response_body")),
                "error_message": result.get("error_message"),
                "explanation": explanation_by_id.get(test_id),
            }
        )

    rows.sort(
        key=lambda row: (
            0 if not row["passed"] else 1,
            PRIORITY_RANK.get(row["priority"], len(PRIORITY_ORDER)),
            row["endpoint_label"],
            row["test_id"],
        )
    )
    return rows


def build_defect_category_buckets(failure_analysis: dict | None) -> list[dict]:
    """Return grouped defect-pattern rows for dashboard summaries."""
    buckets: list[dict] = []
    for pattern in (failure_analysis or {}).get("patterns") or []:
        buckets.append(
            {
                "category": str(pattern.get("pattern_type") or "other"),
                "count": int(pattern.get("count") or 0),
                "severity": str(pattern.get("severity") or "Medium"),
                "description": str(pattern.get("description") or ""),
                "affected_test_ids": list(pattern.get("affected_test_ids") or []),
            }
        )
    buckets.sort(key=lambda item: (-item["count"], item["category"]))
    return buckets


def build_priority_buckets(result_rows: list[dict]) -> list[dict]:
    """Return failed-result counts by priority for P1/P2/P3 dashboard cards."""
    failed_priorities = Counter(
        row["priority"] for row in result_rows if not row.get("passed")
    )
    return [
        {"priority": priority, "count": int(failed_priorities.get(priority, 0))}
        for priority in PRIORITY_ORDER
    ]


def build_endpoint_heatmap_rows(result_rows: list[dict]) -> list[dict]:
    """Aggregate result rows by endpoint for heatmap-style display."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in result_rows:
        grouped[row["endpoint_label"]].append(row)

    heatmap_rows: list[dict] = []
    for endpoint_label, rows in grouped.items():
        total = len(rows)
        failed = sum(1 for row in rows if not row["passed"])
        categories = Counter(
            row["category"] for row in rows if not row["passed"] and row["category"]
        )
        priorities = Counter(
            row["priority"] for row in rows if not row["passed"] and row["priority"]
        )
        heat_level = _heat_level(failed, total)
        heatmap_rows.append(
            {
                "endpoint_label": endpoint_label,
                "total_tests": total,
                "failed_tests": failed,
                "passed_tests": total - failed,
                "heat_level": heat_level,
                "heatmap": HEATMAP_GLYPHS[heat_level] * max(1, failed if failed else 1),
                "top_category": categories.most_common(1)[0][0] if categories else None,
                "priority_breakdown": {
                    priority: int(priorities.get(priority, 0))
                    for priority in PRIORITY_ORDER
                },
                "test_ids": [row["test_id"] for row in rows],
            }
        )

    heatmap_rows.sort(
        key=lambda row: (
            -row["failed_tests"],
            -row["total_tests"],
            row["endpoint_label"],
        )
    )
    return heatmap_rows


def apply_results_filters(result_rows: list[dict], filters: dict | None) -> list[dict]:
    """Return rows matching current dashboard filter selections."""
    filters = filters or {}
    outcome = str(filters.get("outcome") or "all")
    category = str(filters.get("category") or "all")
    priority = str(filters.get("priority") or "all")
    endpoint = str(filters.get("endpoint") or "all")

    filtered: list[dict] = []
    for row in result_rows:
        if outcome == "failed" and row.get("passed"):
            continue
        if outcome == "passed" and not row.get("passed"):
            continue
        if category != "all" and row.get("category") != category:
            continue
        if priority != "all" and row.get("priority") != priority:
            continue
        if endpoint != "all" and row.get("endpoint_label") != endpoint:
            continue
        filtered.append(row)
    return filtered


def build_dashboard_filter_options(result_rows: list[dict]) -> dict:
    """Return deterministic filter option lists for the dashboard controls."""
    categories = sorted(
        {
            row["category"]
            for row in result_rows
            if row.get("category") and row["category"] != "unknown"
        }
    )
    endpoints = sorted(
        {row["endpoint_label"] for row in result_rows if row.get("endpoint_label")}
    )
    return {
        "outcome": ["all", "failed", "passed"],
        "category": ["all", *categories],
        "priority": ["all", *PRIORITY_ORDER],
        "endpoint": ["all", *endpoints],
    }


def build_detail_view(row: dict | None) -> dict | None:
    """Shape a single result row into detail-view sections."""
    if not row:
        return None

    explanation = row.get("explanation") or {}
    analysis_message = {
        "status": "passed" if row.get("passed") else "failed",
        "what_broke": explanation.get("what_broke")
        or ("Test passed." if row.get("passed") else None),
        "why_it_matters": explanation.get("why_it_matters"),
        "how_to_fix": explanation.get("how_to_fix"),
    }
    if not row.get("passed") and not explanation:
        analysis_message["what_broke"] = (
            "No failure explanation was available for this test."
        )
        analysis_message["why_it_matters"] = (
            "The raw execution result is still shown below "
            "so you can inspect the issue."
        )

    return {
        "test_id": row.get("test_id"),
        "title": row.get("title"),
        "endpoint_label": row.get("endpoint_label"),
        "request": {
            "method": row.get("endpoint_method"),
            "url": row.get("request_url"),
            "headers": redact_headers(row.get("request_headers") or {}),
            "query_params": sanitize_value(row.get("request_query_params") or {}),
            "body": sanitize_value(row.get("request_body")),
        },
        "response": {
            "status_code": row.get("actual_status_code"),
            "headers": redact_headers(row.get("response_headers") or {}),
            "body": sanitize_value(row.get("response_body")),
            "error_message": row.get("error_message"),
        },
        "analysis": analysis_message,
    }


def build_run_delta(
    previous_summary: dict | None,
    current_summary: dict | None,
) -> dict | None:
    """Return run-to-run comparison metrics for the results dashboard."""
    if not previous_summary or not current_summary:
        return None

    return {
        "passed_delta": int(current_summary["passed_tests"])
        - int(previous_summary["passed_tests"]),
        "failed_delta": int(current_summary["failed_tests"])
        - int(previous_summary["failed_tests"]),
        "pass_rate_delta": round(
            float(current_summary["pass_rate"]) - float(previous_summary["pass_rate"]),
            1,
        ),
    }


def _heat_level(failed: int, total: int) -> str:
    if failed <= 0 or total <= 0:
        return "none"
    ratio = failed / total
    if ratio >= 0.75:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"
