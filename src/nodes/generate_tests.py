"""generate_tests pipeline node — stub until Epic 3."""

from src.core.state import SataState


def generate_tests(state: SataState) -> SataState:
    """Story 2.3 stage stub: make the next phase visible after confirmation."""
    state["pipeline_stage"] = "generate_tests"
    state["error_message"] = None
    return state
