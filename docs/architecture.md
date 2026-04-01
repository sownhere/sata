# Architecture Document

## Executive Summary

Sata is an AI-powered API Test Agent utilizing LangGraph for pipeline orchestration and Streamlit for the user interface. It is designed to ingest OpenAPI/Swagger specifications, extract endpoints, robustly detect documentation gaps (ambiguities, missing error statuses, missing request bodies), and eventually generate test cases simulating defect categories against the supplied API. 

## Technology Stack

- **Primary Language**: Python 3.12+
- **UI Framework**: Streamlit (>= 1.32.0)
- **Orchestration**: LangGraph, LangChain, Langchain-OpenAI (>= 0.1.0)
- **Data Validation & Parsing**: Pydantic (>= 2.0.0), PyYAML (>= 6.0.0), openapi-spec-validator (>= 0.7.0)
- **Environment Management**: Python-dotenv (>= 1.0.0)
- **Testing**: Pytest (>= 8.0.0), Pytest-mock (>= 3.14.0)

## Architecture Pattern

The system follows a state-machine orchestrator pattern tightly coupled with a reactive UI.
- **State Definition**: A centralized and strictly typed `SataState` mechanism is used to persist data across iterative logic nodes and Streamlit re-renders.
- **Orchestrator**: LangGraph is utilized to transition the AI Agent across various logical checkpoints (Ingestion -> Parsing -> Gap Detection -> Filling Gaps -> Specs Review -> Test Generation -> Execution -> Results Analysis).
- **Presentation**: Streamlit bridges user gap-fulfillment via reactive updates feeding directly back into the orchestrator state (`st.session_state`).

## Source Structure

The project is migrating from a flat `app/` layout to a layered `src/` architecture. See [`source-architecture.md`](./source-architecture.md) for the full target structure, dependency rules, and migration plan.

**Target layers:** `src/nodes/` (pipeline nodes) → `src/tools/` (deterministic logic) → `src/core/` (state, models, config, graph) ← `src/ui/` (Streamlit presentation).

## Component Overview

1. **User Interface (`app.py` → `src/ui/`)**: Responsible for presenting file upload options, URL fetching, rendering detected gaps as forms, and displaying the persistent pipeline stage header.
2. **Pipeline Engine (`app/pipeline.py` → `src/core/graph.py` + `src/nodes/`)**: Constructs a `CompiledStateGraph`. Responsible for conditional internal routing based on `state["detected_gaps"]` and state errors. Node handlers are being extracted to individual files.
3. **Spec Parser & Validator (`app/utils/spec_parser.py` → `src/tools/spec_parser.py`)**: Reliably extracts and normalizes the target API's schema into an internal representation without side-effects.
4. **Gap Detector (`app/utils/spec_gap_detector.py` → `src/tools/gap_detector.py`)**: Introspects parsed schemas against raw OpenAPI specs to ask deterministic clarification questions to the user.
5. **Spec Fetcher (`app/utils/spec_fetcher.py` → `src/tools/spec_fetcher.py`)**: Dedicated security-conscious HTTP client to fetch public schemas with timeouts and local IP filtering configurations.
