"""Unit tests for pure results dashboard helpers."""

from src.ui.results_dashboard import (
    apply_results_filters,
    build_dashboard_filter_options,
    build_detail_view,
    build_endpoint_heatmap_rows,
    build_priority_buckets,
    build_result_rows,
    build_run_delta,
    build_run_summary,
)


def _sample_result_rows():
    test_results = [
        {
            "test_id": "tc-1",
            "test_title": "Get users",
            "endpoint_method": "GET",
            "endpoint_path": "/users",
            "passed": False,
            "expected_status_code": 200,
            "actual_status_code": 404,
            "validation_errors": ["Expected status 200, got 404"],
            "request_headers": {"Authorization": "Bearer hidden"},
            "actual_response_body": {"error": "Not Found"},
        },
        {
            "test_id": "tc-2",
            "test_title": "Create user",
            "endpoint_method": "POST",
            "endpoint_path": "/users",
            "passed": True,
            "expected_status_code": 201,
            "actual_status_code": 201,
            "validation_errors": [],
            "request_headers": {},
            "actual_response_body": {"id": "1"},
        },
    ]
    test_cases = [
        {
            "id": "tc-1",
            "endpoint_method": "GET",
            "endpoint_path": "/users",
            "priority": "P1",
            "category": "happy_path",
            "title": "Get users",
        },
        {
            "id": "tc-2",
            "endpoint_method": "POST",
            "endpoint_path": "/users",
            "priority": "P2",
            "category": "boundary",
            "title": "Create user",
        },
    ]
    failure_analysis = {
        "explanations": [
            {
                "test_id": "tc-1",
                "what_broke": "GET /users returned 404",
                "why_it_matters": "The endpoint looks missing.",
                "how_to_fix": "Verify the base path.",
            }
        ]
    }
    return build_result_rows(test_results, test_cases, failure_analysis)


def test_build_run_summary_calculates_pass_rate():
    summary = build_run_summary([{"passed": True}, {"passed": False}])
    assert summary == {
        "total_tests": 2,
        "passed_tests": 1,
        "failed_tests": 1,
        "pass_rate": 50.0,
    }


def test_build_priority_buckets_counts_failed_rows_only():
    rows = _sample_result_rows()
    buckets = build_priority_buckets(rows)
    assert buckets == [
        {"priority": "P1", "count": 1},
        {"priority": "P2", "count": 0},
        {"priority": "P3", "count": 0},
    ]


def test_build_endpoint_heatmap_rows_aggregates_by_method_and_path():
    rows = _sample_result_rows()
    heatmap_rows = build_endpoint_heatmap_rows(rows)
    assert heatmap_rows[0]["endpoint_label"] == "GET /users"
    assert heatmap_rows[0]["failed_tests"] == 1
    assert heatmap_rows[1]["endpoint_label"] == "POST /users"


def test_detail_view_redacts_headers_and_uses_pass_message():
    passing_row = _sample_result_rows()[1]
    detail = build_detail_view(passing_row)
    assert detail["analysis"]["what_broke"] == "Test passed."

    failing_row = _sample_result_rows()[0]
    detail = build_detail_view(failing_row)
    assert detail["request"]["headers"]["Authorization"] == "Bearer [REDACTED]"
    assert detail["analysis"]["what_broke"] == "GET /users returned 404"


def test_apply_results_filters_preserves_dashboard_context():
    rows = _sample_result_rows()
    filtered = apply_results_filters(
        rows,
        {
            "outcome": "failed",
            "category": "happy_path",
            "priority": "P1",
            "endpoint": "GET /users",
        },
    )
    assert [row["test_id"] for row in filtered] == ["tc-1"]


def test_build_dashboard_filter_options_are_stable():
    options = build_dashboard_filter_options(_sample_result_rows())
    assert options["outcome"] == ["all", "failed", "passed"]
    assert options["category"] == ["all", "boundary", "happy_path"]


def test_build_run_delta_reports_improvement():
    delta = build_run_delta(
        {"passed_tests": 1, "failed_tests": 2, "pass_rate": 33.3},
        {"passed_tests": 2, "failed_tests": 1, "pass_rate": 66.7},
    )
    assert delta == {"passed_delta": 1, "failed_delta": -1, "pass_rate_delta": 33.4}
