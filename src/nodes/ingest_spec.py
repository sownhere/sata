"""ingest_spec pipeline node — receives spec source selection."""

from src.core.state import SataState


def ingest_spec(state: SataState) -> SataState:
    """Receive spec source selection and keep the app at ingestion stage."""
    state["pipeline_stage"] = "spec_ingestion"
    return state
