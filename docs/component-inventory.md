# Component Inventory

This document details the internal library modules and components comprising the Sata AI Testing pipeline.

> **Note:** The project is migrating to a layered `src/` structure. See [`source-architecture.md`](./source-architecture.md) for the target layout. Current paths shown with target paths in parentheses.

## Tools (Deterministic Logic)

Sata isolates complex or algorithmic logic outside the LangGraph orchestration to ensure determinism and security.

### 1. Spec Parser (`app/utils/spec_parser.py` → `src/tools/spec_parser.py`)
- **Purpose**: Reliably extracts and normalizes both JSON and YAML OpenAPI 3.x specifications into a strict internal dictionary format (`parsed_api_model`).
- **Key Functions**:
  - `parse_openapi_spec(raw_spec)`: Entry point for transformation. Returns canonical API schema.
  - `_resolve_ref()`: Recursively resolves internal JSON pointer `$ref` dependencies.
  - `_extract_auth()`: Detects security schemes (Bearer, Basic, API Key, OAuth2 stub).
- **Security Check**: Emits high-level trace errors rather than dumping the potentially malicious raw file content back to the AI or Streamlit UI.

### 2. Gap Detector (`app/utils/spec_gap_detector.py` → `src/tools/gap_detector.py`)
- **Purpose**: Identifies ambiguities or incomplete documentation in the target OpenAPI spec, forcing human-in-the-loop clarification before test generation.
- **Rules applied**:
  - **Write Body missing**: Verifies `POST`, `PUT`, `PATCH` endpoints contain documented Request Bodies.
  - **Error responses missing**: Alerts if schemas lack generic non-200 responses.
  - **Auth Ambiguity**: Triggers if multiple security schemes are possible but undefined on strict routes.

### 3. Spec Fetcher (`app/utils/spec_fetcher.py` → `src/tools/spec_fetcher.py`)
- **Purpose**: Connects securely to external web URLs to pull down public OpenAPI specs.
- **Security Protocols**:
  - Limits payloads to **10MB** explicitly (`MAX_RESPONSE_BYTES`).
  - Strict **No-Redirect** policy to prevent internal network scanning or SSRF via location headers.
  - **Local/Private IP filtering**: Hard-blocks localhost, private subnet, and loopback resolutions.

### 4. Conversational Builder (`app/utils/conversational_spec_builder.py` → `src/tools/conversational_builder.py`)
- **Purpose**: Extracts API model from free-form user conversation via LLM when no spec file exists.
- **Key Functions**:
  - `extract_api_model_from_conversation()`: Builds LLM chain, validates output against expected schema.
  - `_validate_api_model()`: Ensures required keys and endpoint structure.

## Core Layer

### State Contract (`app/state.py` → `src/core/state.py`)
- **`SataState(TypedDict)`**: Defines the singular state transition object utilized by the AI nodes. Explicitly enumerates types for properties such as `pipeline_stage`, `detected_gaps`, and `iteration_count`.

### Configuration (`app/utils/env.py` → `src/core/config.py`)
- **Purpose**: Halts application startup synchronously if required integration secrets are absent. Target: merged with `config/settings.yaml` loader for non-secret tuning.
- **Key Variables Checked**: `LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`.

### Data Models (new — `src/core/models.py`)
- **Purpose**: Pydantic models for validation at system boundaries: `EndpointModel`, `AuthModel`, `ApiModel`, `GapRecord`. Future: `TestCase`, `TestResult`, `FailureAnalysis`.

## UI Layer

### Spec Review (`app/utils/spec_review.py` → `src/ui/spec_review.py`)
- **Purpose**: Formats parsed API model into structured Streamlit tables for human checkpoint review.

### Pipeline Visualization (`app/utils/pipeline_visualization.py` → `src/ui/visualization.py`)
- **Purpose**: Generates GraphViz DOT diagrams of the LangGraph pipeline with node status coloring.

## Pipeline Orchestration (`app/pipeline.py` → `src/core/graph.py` + `src/nodes/`)
- **Graph builder and routing**: Moving to `src/core/graph.py`.
- **Node handlers**: Splitting into 10 individual files under `src/nodes/` (1 per node).
