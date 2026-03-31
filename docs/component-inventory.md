# Component Inventory

This document details the internal library modules and components comprising the Sata AI Testing pipeline. 

## Utilities Library (`app/utils/`)

Sata isolates complex or algorithmic logic outside the LangGraph orchestration to ensure determinism and security.

### 1. Spec Parser (`spec_parser.py`)
- **Purpose**: Reliably extracts and normalizes both JSON and YAML OpenAPI 3.x specifications into a strict internal dictionary format (`parsed_api_model`).
- **Key Functions**:
  - `parse_openapi_spec(raw_spec)`: Entry point for transformation. Returns canonical API schema.
  - `_resolve_ref()`: Recursively resolves internal JSON pointer `$ref` dependencies.
  - `_extract_auth()`: Detects security schemes (Bearer, Basic, API Key, OAuth2 stub).
- **Security Check**: Emits high-level trace errors rather than dumping the potentially malicious raw file content back to the AI or Streamlit UI.

### 2. Gap Detector (`spec_gap_detector.py`)
- **Purpose**: Identifies ambiguities or incomplete documentation in the target OpenAPI spec, forcing human-in-the-loop clarification before test generation.
- **Rules applied**:
  - **Write Body missing**: Verifies `POST`, `PUT`, `PATCH` endpoints contain documented Request Bodies.
  - **Error responses missing**: Alerts if schemas lack generic non-200 responses.
  - **Auth Ambiguity**: Triggers if multiple security schemes are possible but undefined on strict routes.

### 3. Spec Fetcher (`spec_fetcher.py`)
- **Purpose**: Connects securely to external web URLs to pull down public OpenAPI specs.
- **Security Protocols**:
  - Limits payloads to **10MB** explicitly (`MAX_RESPONSE_BYTES`).
  - Strict **No-Redirect** policy to prevent internal network scanning or SSRF via location headers.
  - **Local/Private IP filtering**: Hard-blocks localhost, private subnet, and loopback resolutions.

### 4. Environment Validator (`env.py`)
- **Purpose**: Halts application startup synchronously if required integration secrets are absent.
- **Key Variables Checked**: `LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`.

## State Contract (`app/state.py`)

- **`SataState(TypedDict)`**: Defines the singular state transition object utilized by the AI nodes. Explicitly enumerates types for properties such as `pipeline_stage`, `detected_gaps`, and `iteration_count`.
