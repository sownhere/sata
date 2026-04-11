"""Unit tests for deterministic results report generation."""

from pathlib import Path

from src.tools.report_builder import build_results_report, write_results_report


def _report_state():
    return {
        "run_attempt": 2,
        "demo_context": {"name": "PetStore"},
        "test_results": [
            {
                "test_id": "tc-1",
                "test_title": "Get users",
                "endpoint_method": "GET",
                "endpoint_path": "/users",
                "passed": False,
                "expected_status_code": 200,
                "actual_status_code": 404,
                "validation_errors": ["Expected status 200, got 404"],
                "request_headers": {"Authorization": "Bearer secret"},
                "actual_response_body": {"token": "hidden"},
            }
        ],
        "test_cases": [
            {
                "id": "tc-1",
                "endpoint_method": "GET",
                "endpoint_path": "/users",
                "priority": "P1",
                "category": "happy_path",
                "title": "Get users",
            }
        ],
        "failure_analysis": {
            "patterns": [
                {
                    "pattern_type": "status_mismatch",
                    "count": 1,
                    "severity": "High",
                    "description": "GET /users returns 404",
                    "affected_test_ids": ["tc-1"],
                }
            ],
            "explanations": [
                {
                    "test_id": "tc-1",
                    "what_broke": "GET /users returned 404",
                    "why_it_matters": "Consumers cannot load users.",
                    "how_to_fix": "Check the base URL.",
                }
            ],
            "smart_diagnosis": {
                "category": "wrong_base_url",
                "confidence": "medium",
                "message": "Check TARGET_API_URL.",
            },
            "next_test_suggestions": [],
        },
    }


def test_build_results_report_contains_required_sections_and_redacted_content():
    report = build_results_report(_report_state())

    assert "## Run Metadata" in report
    assert "## Summary Metrics" in report
    assert "## Category Breakdown" in report
    assert "## Failed Test Details" in report
    assert "## Smart Outcomes" in report
    assert "Bearer secret" not in report
    assert "hidden" not in report


def test_write_results_report_uses_timestamped_files(tmp_path: Path):
    artifact_one = write_results_report("first\n", report_dir=tmp_path)
    artifact_two = write_results_report("second\n", report_dir=tmp_path)

    assert Path(artifact_one["path"]).exists()
    assert Path(artifact_two["path"]).exists()
    assert artifact_one["path"] != artifact_two["path"]
