"""Tests for the parse_spec pipeline node in app/pipeline.py.

Covers: node with valid state, node with missing raw_spec, node with malformed spec.
Validates NFR2: node failures must not crash pipeline (never raises).
"""

import json

from src.core.state import initial_state
from src.nodes.parse_spec import parse_spec

# ── Fixtures ────────────────────────────────────────────────────────────────

VALID_SPEC_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
)

MALFORMED_SPEC = "{ this is not valid at all !!! }"


# ── Tests: parse_spec node ──────────────────────────────────────────────────


class TestParseSpecNode:
    def test_valid_state_parses_successfully(self):
        """AC 1: valid raw_spec populates parsed_api_model and advances stage."""
        state = initial_state()
        state["raw_spec"] = VALID_SPEC_JSON
        state["spec_source"] = "file"

        result = parse_spec(state)

        assert result["parsed_api_model"] is not None
        assert len(result["parsed_api_model"]["endpoints"]) == 1
        assert result["parsed_api_model"]["title"] == "Test API"
        assert result["pipeline_stage"] == "spec_parsed"
        assert result["error_message"] is None

    def test_url_fetched_spec_parses_identically(self):
        """URL-imported specs reuse the same parse path as file upload."""
        state = initial_state()
        state["raw_spec"] = VALID_SPEC_JSON
        state["spec_source"] = "url"

        result = parse_spec(state)

        assert result["parsed_api_model"] is not None
        assert len(result["parsed_api_model"]["endpoints"]) == 1
        assert result["parsed_api_model"]["title"] == "Test API"
        assert result["pipeline_stage"] == "spec_parsed"
        assert result["error_message"] is None

    def test_missing_raw_spec(self):
        """Node handles missing raw_spec gracefully without raising."""
        state = initial_state()
        state["raw_spec"] = None

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert result["error_message"] == "No spec content found. Please upload a file."
        # Pipeline stage should NOT advance
        assert result["pipeline_stage"] == "spec_ingestion"

    def test_empty_raw_spec(self):
        """Node handles empty string raw_spec gracefully."""
        state = initial_state()
        state["raw_spec"] = ""

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert result["error_message"] == "No spec content found. Please upload a file."

    def test_malformed_spec_sets_error(self):
        """AC 3: malformed spec sets error_message without crashing."""
        state = initial_state()
        state["raw_spec"] = MALFORMED_SPEC
        state["spec_source"] = "file"

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert result["error_message"] is not None
        assert len(result["error_message"]) > 0
        # Pipeline stage should NOT advance
        assert result["pipeline_stage"] == "spec_ingestion"

    def test_parse_failure_is_distinct_from_fetch_failure(self):
        """Parse errors should describe invalid content, not network problems."""
        state = initial_state()
        state["raw_spec"] = "<html>not an openapi spec</html>"
        state["spec_source"] = "url"

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert result["error_message"] is not None
        assert "could not reach url" not in result["error_message"].lower()
        assert "fetch" not in result["error_message"].lower()

    def test_node_never_raises(self):
        """NFR2: parse_spec must never raise — always returns state."""
        state = initial_state()
        state["raw_spec"] = MALFORMED_SPEC

        # Should not raise any exception
        result = parse_spec(state)
        assert isinstance(result, dict)

    def test_clears_error_on_success(self):
        """Error message is cleared on successful parse (no stale errors)."""
        state = initial_state()
        state["error_message"] = "Previous error from somewhere"
        state["raw_spec"] = VALID_SPEC_JSON
        state["spec_source"] = "file"

        result = parse_spec(state)

        assert result["error_message"] is None
        assert result["parsed_api_model"] is not None

    def test_clears_model_on_failure(self):
        """parsed_api_model is set to None on parse failure."""
        state = initial_state()
        # First, set a valid model
        state["parsed_api_model"] = {"endpoints": []}
        state["raw_spec"] = MALFORMED_SPEC

        result = parse_spec(state)

        assert result["parsed_api_model"] is None

    def test_missing_openapi_field_error_message(self):
        """Error message is descriptive for missing openapi field."""
        spec = json.dumps({"info": {"title": "Test", "version": "1.0.0"}, "paths": {}})
        state = initial_state()
        state["raw_spec"] = spec

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert "openapi" in result["error_message"].lower()

    def test_returns_same_state_object(self):
        """Node returns the same state dict (mutated in place)."""
        state = initial_state()
        state["raw_spec"] = VALID_SPEC_JSON

        result = parse_spec(state)

        assert result is state

    def test_failure_resets_stage_from_spec_parsed(self):
        """Parse failure resets pipeline_stage even when starting from spec_parsed."""
        state = initial_state()
        state["pipeline_stage"] = "spec_parsed"
        state["parsed_api_model"] = {"endpoints": []}
        state["raw_spec"] = MALFORMED_SPEC

        result = parse_spec(state)

        assert result["parsed_api_model"] is None
        assert result["error_message"] is not None
        assert result["pipeline_stage"] == "spec_ingestion"
