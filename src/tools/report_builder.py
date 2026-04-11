"""Deterministic report rendering and persistence for review_results output."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.ui.results_dashboard import (
    build_defect_category_buckets,
    build_result_rows,
    build_run_summary,
)

DEFAULT_REPORT_DIR = Path("reports")


def build_results_report(state: dict) -> str:
    """Return a Markdown report for the current test run."""
    summary = build_run_summary(state.get("test_results"))
    failure_analysis = state.get("failure_analysis") or {}
    result_rows = build_result_rows(
        state.get("test_results"),
        state.get("test_cases"),
        failure_analysis,
    )
    category_buckets = build_defect_category_buckets(failure_analysis)
    generated_at = datetime.now(timezone.utc).isoformat()
    run_attempt = int(state.get("run_attempt") or 1)
    demo_context = state.get("demo_context") or {}

    lines = [
        "# Sata Results Report",
        "",
        "## Run Metadata",
        f"- Generated at: {generated_at}",
        f"- Run attempt: {run_attempt}",
        f"- Demo mode: {'Yes' if demo_context else 'No'}",
    ]
    if demo_context:
        lines.append(f"- Demo sample: {demo_context.get('name')}")

    lines.extend(
        [
            "",
            "## Summary Metrics",
            f"- Total tests: {summary['total_tests']}",
            f"- Passed: {summary['passed_tests']}",
            f"- Failed: {summary['failed_tests']}",
            f"- Pass rate: {summary['pass_rate']}%",
            "",
            "## Category Breakdown",
        ]
    )

    if category_buckets:
        for bucket in category_buckets:
            lines.append(
                f"- {bucket['category']}: {bucket['count']} failure(s)"
                f" [{bucket['severity']}]"
            )
    else:
        lines.append("- No grouped defect categories were detected.")

    lines.extend(["", "## Failed Test Details"])
    failed_rows = [row for row in result_rows if not row.get("passed")]
    if failed_rows:
        for row in failed_rows:
            explanation = row.get("explanation") or {}
            lines.extend(
                [
                    f"### {row['test_id']} — {row['endpoint_label']}",
                    f"- Priority: {row['priority']}",
                    f"- Category: {row['category']}",
                    f"- Expected status: {row.get('expected_status_code')}",
                    f"- Actual status: {row.get('actual_status_code')}",
                    f"- What broke: {explanation.get('what_broke') or 'N/A'}",
                    f"- Why it matters: {explanation.get('why_it_matters') or 'N/A'}",
                    f"- How to fix: {explanation.get('how_to_fix') or 'N/A'}",
                    "",
                ]
            )
    else:
        lines.append("- No failing tests in this run.")

    lines.extend(["## Smart Outcomes"])
    suggestions = failure_analysis.get("next_test_suggestions") or []
    diagnosis = failure_analysis.get("smart_diagnosis") or {}
    if suggestions:
        lines.append("### Deeper-Test Suggestions")
        for suggestion in suggestions:
            lines.append(f"- {suggestion}")
    if diagnosis:
        lines.extend(
            [
                "### Smart Diagnosis",
                f"- Category: {diagnosis.get('category')}",
                f"- Confidence: {diagnosis.get('confidence')}",
                f"- Message: {diagnosis.get('message')}",
            ]
        )
    if not suggestions and not diagnosis:
        lines.append("- No smart outcomes were generated for this run.")

    return "\n".join(lines).strip() + "\n"


def write_results_report(
    report_text: str,
    *,
    report_dir: Path | None = None,
) -> dict:
    """Persist a report using timestamped filenames in a predictable folder."""
    directory = report_dir or DEFAULT_REPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = directory / f"sata-results-{timestamp}.md"
    path.write_text(report_text, encoding="utf-8")
    return {
        "path": str(path),
        "content": report_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
