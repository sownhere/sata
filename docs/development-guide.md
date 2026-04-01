# Development Guide

This document outlines the setup and development workflows for the Sata project.

## Prerequisites

- Python 3.12+
- `pip` or equivalent Python package manager.

## Environment Setup

1. Copy the sample environment file and insert your API keys.
   ```bash
   cp .env.example .env
   ```
2. Set the variables defined in `.env`:
   - `LLM_API_KEY`: API key for the Language Model provider.
   - `LLM_CHAT_MODEL`: Specify the chat model (e.g. `gpt-4o`, `gemini-pro`).
   - `LLM_BASE_URL`: Base URL mapped to an OpenAI-compatible endpoint.

## Local Development

The project dependencies are managed via a standard `requirements.txt`.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
2. Start the Streamlit Application:
   ```bash
   streamlit run app.py
   ```
   The UI will launch on `localhost:8501`.

## Testing

The testing suite utilizes `pytest` and `pytest-mock` to test utility functions deterministically and mock out HTTP requests.

Run the test suite:
```bash
pytest tests/
```

## Common Development Tasks

> **Note:** The project is migrating from `app/` to `src/`. See [`source-architecture.md`](./source-architecture.md) for the target layout. Paths below show current → target.

- **Updating the State**: Modify `app/state.py` → `src/core/state.py` if new information must be tracked across the LangGraph pipeline. Be sure to update initial default values.
- **Adding Pipeline Nodes**: Currently in `app/pipeline.py` → target: create a new file in `src/nodes/` with a handler function, then register it in `src/core/graph.py` → `build_pipeline()`.
- **Adding Tools**: Currently in `app/utils/` → target: create a new file in `src/tools/`. Tools must not import from `nodes/`, `ui/`, or other tools.
- **Parsing Logic**: Add new OpenAPI rules in `app/utils/spec_parser.py` → `src/tools/spec_parser.py` or modify gap questions in `app/utils/spec_gap_detector.py` → `src/tools/gap_detector.py`.
- **Modifying Prompts**: Currently inline strings → target: edit markdown files in `src/prompts/`. No Python changes needed.
- **Running Unit Tests Only**: `pytest tests/unit/ --tb=short -q` (after test reorganization).
