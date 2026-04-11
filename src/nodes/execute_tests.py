"""execute_tests pipeline node — HTTP test execution with auth and retry."""

from src.core.config import get_settings
from src.core.observability import append_reasoning_log
from src.core.state import SataState
from src.tools.http_executor import execute_single_test, get_auth_headers
from src.tools.response_validator import validate_response

_CONNECT_ERRORS = ("connection", "connect", "unreachable", "refused", "dns")


def execute_tests(state: SataState) -> SataState:
    """Execute all confirmed test cases as HTTP requests.

    Guards:
    - Requires test_plan_confirmed == True
    - Requires target_api_url to be set
    - Requires test_cases to be non-empty

    On success: populates state["test_results"] and clears error_message.
    On failure: sets error_message and stores any partial results.
    """
    if not state.get("test_plan_confirmed"):
        append_reasoning_log(
            state,
            stage="execute_tests",
            event_type="reasoning",
            reason="Blocked execution because the test plan is not confirmed yet.",
            details={"test_plan_confirmed": False},
        )
        state["error_message"] = "Test plan must be confirmed before executing tests."
        state["pipeline_stage"] = "execute_tests"
        return state

    base_url = (state.get("target_api_url") or "").strip()
    if not base_url:
        append_reasoning_log(
            state,
            stage="execute_tests",
            event_type="reasoning",
            reason="Blocked execution because the target API URL is missing.",
            details={"target_api_url": None},
        )
        state["error_message"] = (
            "Target API URL is required — set TARGET_API_URL in .env"
        )
        state["pipeline_stage"] = "execute_tests"
        return state

    test_cases = state.get("test_cases") or []
    if not test_cases:
        append_reasoning_log(
            state,
            stage="execute_tests",
            event_type="reasoning",
            reason="Blocked execution because no confirmed test cases are available.",
            details={"test_case_count": 0},
        )
        state["error_message"] = "No confirmed test cases to execute."
        state["pipeline_stage"] = "execute_tests"
        return state

    settings = get_settings()
    auth_headers = get_auth_headers((state.get("parsed_api_model") or {}).get("auth"))
    timeout = settings.execution.request_timeout_seconds
    retry_count = settings.execution.retry_count
    max_iterations = settings.pipeline.max_iterations
    state["run_attempt"] = max(1, int(state.get("run_attempt") or 0))

    append_reasoning_log(
        state,
        stage="execute_tests",
        event_type="reasoning",
        reason="Preparing HTTP execution for the confirmed test plan.",
        details={
            "test_case_count": len(test_cases),
            "target_api_url": base_url,
            "auth_configured": bool(auth_headers),
            "retry_count": retry_count,
        },
    )

    results = []
    iteration_count = state.get("iteration_count") or 0

    for test_case in test_cases:
        if iteration_count >= max_iterations:
            state["error_message"] = (
                f"Execution halted: reached max_iterations ({max_iterations})"
            )
            state["test_results"] = results
            state["iteration_count"] = iteration_count
            state["pipeline_stage"] = "execute_tests"
            return state

        iteration_count += 1
        append_reasoning_log(
            state,
            stage="execute_tests",
            event_type="tool_call",
            tool_name="http_executor.execute_single_test",
            reason="Dispatch the next confirmed HTTP test case against the target API.",
            input_summary={
                "test_id": test_case.get("id"),
                "endpoint_method": test_case.get("endpoint_method"),
                "endpoint_path": test_case.get("endpoint_path"),
                "priority": test_case.get("priority"),
                "has_request_overrides": bool(test_case.get("request_overrides")),
            },
        )
        result = execute_single_test(
            test_case, base_url, auth_headers, timeout, retry_count
        )
        validate_response(test_case, result, state.get("parsed_api_model"))
        results.append(result)

        # Unreachable API detection: first test fails with connection error
        if (
            len(results) == 1
            and result["actual_status_code"] is None
            and result.get("error_message")
        ):
            err_lower = result["error_message"].lower()
            if any(phrase in err_lower for phrase in _CONNECT_ERRORS):
                append_reasoning_log(
                    state,
                    stage="execute_tests",
                    event_type="reasoning",
                    reason=(
                        "Halting execution because the first request indicates "
                        "the target API is unreachable."
                    ),
                    details={
                        "test_id": result.get("test_id"),
                        "error_message": result.get("error_message"),
                    },
                )
                state["error_message"] = (
                    "Target API is unreachable — check the URL and your connection"
                )
                state["test_results"] = results
                state["iteration_count"] = iteration_count
                state["pipeline_stage"] = "execute_tests"
                return state

    state["test_results"] = results
    state["iteration_count"] = iteration_count
    state["error_message"] = None
    state["pipeline_stage"] = "execute_tests"
    return state
