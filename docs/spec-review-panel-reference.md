# Spec Review Panel Reference

This document captures the display contract for Story 2.1.

## Purpose

The Spec Review checkpoint is read-only. It lets the user verify the parsed API model before any edit, confirm, or reject controls are added in later stories.

## UI Contract

- Stage label for `review_spec` must render as `Spec Review`.
- The next-action message must tell the user to review the API spec before confirming or rejecting.
- The screen should show:
  - API title and version
  - endpoint count
  - a structured endpoint summary table
  - one expander per endpoint with parameters, request body summary, response summary, and auth status
- The review panel must not render raw JSON, `raw_spec`, secrets, or tokens.

## Helper Functions

`app/utils/spec_review.py` provides deterministic formatting helpers:

- `get_stage_display_label(stage)`
- `build_endpoint_summary_rows(parsed_api_model)`
- `build_endpoint_detail_view(endpoint)`

These helpers keep presentation logic out of parsing and pipeline nodes.

## Empty-State Behavior

If the review stage is reached with zero endpoints, the app should:

- show a clear warning that there are no endpoints to review
- give the user a direct action to return to Spec Ingestion
- leave `spec_confirmed` false

## Scope Boundary

- Story 2.1: display-only review panel
- Story 2.2: inline editing, add, remove
- Story 2.3: confirm/reject controls and auth safety copy
