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

- **Updating the State**: Modify `app/state.py` if new information must be tracked across the LangGraph pipeline. Be sure to update initial default values.
- **Adding Pipeline Nodes**: Open `app/pipeline.py` to draft a new function node and register it in `build_pipeline()`.
- **Parsing Logic**: Add new OpenAPI rules directly into `app/utils/spec_parser.py` or modify gap questions in `app/utils/spec_gap_detector.py`.
