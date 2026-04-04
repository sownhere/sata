"""Pydantic v2 data models for Sata's canonical data contracts.

Canonical location: src.core.models
These models define the validated shapes for API specs, endpoints, auth,
and gap records. They are data contracts only — no business logic or I/O.

Usage:
    from src.core.models import ApiModel, EndpointModel, AuthModel, GapRecord
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AuthModel(BaseModel):
    """Auth configuration extracted from an API spec."""

    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = None
    """Auth type: "bearer", "apiKey", or None."""

    scheme: Optional[str] = None
    """Auth scheme, e.g. "Bearer"."""

    location: Optional[str] = Field(None, alias="in")
    """Where the credential is sent: "header" or "query"."""

    name: Optional[str] = None
    """Header/query parameter name, e.g. "Authorization"."""


class EndpointModel(BaseModel):
    """A single API endpoint extracted from a parsed spec."""

    path: str
    """URL path, e.g. "/users/{id}"."""

    method: str
    """HTTP method in uppercase, e.g. "GET"."""

    operation_id: str = ""
    """OpenAPI operationId, e.g. "listUsers"."""

    summary: str = ""
    """Short human-readable description."""

    parameters: list[dict] = Field(default_factory=list)
    """List of parameter dicts with keys: name, in, required, schema, description."""

    request_body: Optional[dict] = None
    """Request body schema dict, or None if not applicable."""

    response_schemas: dict = Field(default_factory=dict)
    """Map of status code string to response schema dict, e.g. {"200": {...}}."""

    auth_required: bool = False
    """Whether this endpoint requires authentication."""

    tags: list[str] = Field(default_factory=list)
    """OpenAPI tags for grouping."""


class ApiModel(BaseModel):
    """Top-level parsed API model — the canonical shape of parsed_api_model."""

    title: str = ""
    """API title from info.title."""

    version: str = ""
    """API version from info.version."""

    endpoints: list[EndpointModel] = Field(default_factory=list)
    """All discovered endpoints."""

    auth: Optional[AuthModel] = None
    """Top-level auth configuration."""


class GapRecord(BaseModel):
    """A detected gap in a parsed API spec that requires clarification.

    Schema matches the dict produced by ``_gap_record()`` in
    ``src.tools.gap_detector`` — that function is the canonical schema source.
    """

    id: str
    """Unique gap identifier, e.g. "get-users-missing-response-schema"."""

    endpoint_key: str
    """Human-readable endpoint identifier, e.g. "GET /users"."""

    path: str
    """URL path of the endpoint with the gap."""

    method: str
    """HTTP method of the endpoint with the gap."""

    gap_type: str
    """Gap category, e.g. "missing_response_schema", "ambiguous_auth"."""

    field: str
    """Specific field that is missing or ambiguous."""

    question: str
    """Human-readable question to resolve the gap."""

    input_type: str
    """Expected input type for the answer: "text", "select", etc."""

    options: Optional[list[str]] = None
    """Allowed answer options for select-type gaps."""
