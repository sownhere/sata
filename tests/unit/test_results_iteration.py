"""Tests for results-iteration helpers in app.py (re-test loop).

These guard against a regression where re-runs accumulated against
execute_tests' max_iterations guard (NFR5) because iteration_count was
never reset between attempts.
"""

import importlib.util
from pathlib import Path


def _load_app_module():
    """Load app.py as a module without running streamlit side-effects."""
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    spec = importlib.util.spec_from_file_location("sata_app_under_test", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_state(iteration_count: int = 10, run_attempt: int = 1) -> dict:
    return {
        "test_results": [
            {
                "test_id": "T-1",
                "passed": True,
                "endpoint_method": "GET",
                "endpoint_path": "/pets",
                "actual_status_code": 200,
                "expected_status_code": 200,
            }
        ],
        "test_cases": [{"test_id": "T-1"}],
        "iteration_count": iteration_count,
        "run_attempt": run_attempt,
        "run_history": [],
        "scoped_run_selection": None,
    }


def test_prepare_rerun_tracking_resets_iteration_count():
    app_module = _load_app_module()

    previous_state = _base_state(iteration_count=10, run_attempt=1)
    pending_state = app_module._prepare_rerun_tracking(previous_state)

    assert pending_state["iteration_count"] == 0, (
        "iteration_count must reset so re-runs don't accumulate toward "
        "max_iterations (NFR5)"
    )
    assert pending_state["run_attempt"] == 2
    assert pending_state["previous_run_summary"] is not None
    assert len(pending_state["run_history"]) == 1


def test_prepare_rerun_tracking_resets_across_multiple_reruns():
    app_module = _load_app_module()

    state = _base_state(iteration_count=10, run_attempt=1)
    for expected_attempt in (2, 3, 4):
        state = app_module._prepare_rerun_tracking(state)
        assert state["iteration_count"] == 0
        assert state["run_attempt"] == expected_attempt
        # Simulate an execution that consumed iterations again.
        state["iteration_count"] = 10
        state["test_results"] = _base_state()["test_results"]
