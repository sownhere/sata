# Source Tree Analysis

This document provides an overview of the directory structure and key file locations for the Sata project.

> **Note:** The project is migrating from the current `app/` layout to a layered `src/` structure. See [`source-architecture.md`](./source-architecture.md) for the target layout (Epic 7).

## Current Directory Tree

```
project-root/
├── app/                  # Main application package (current — migrating to src/)
│   ├── utils/            # Shared utilities
│   │   ├── conversational_spec_builder.py  # LLM-based chat spec extraction
│   │   ├── env.py              # Environment validation logic
│   │   ├── pipeline_visualization.py # GraphViz pipeline diagrams
│   │   ├── spec_fetcher.py     # Remote OpenAPI spec HTTP fetching
│   │   ├── spec_gap_detector.py # Deterministic OpenAPI gap analysis
│   │   ├── spec_parser.py      # OpenAPI JSON/YAML parsing
│   │   └── spec_review.py      # Human checkpoint UI formatting
│   ├── __init__.py
│   ├── pipeline.py       # LangGraph orchestration, nodes, routing, graph builder
│   └── state.py          # Typed shared state definition (SataState)
├── docs/                 # Project knowledge and generated documentation
├── tests/                # Test suite (flat — migrating to unit/integration/e2e)
├── config/               # Non-secret configuration (target: settings.yaml)
├── _bmad-output/         # BMAD generated artifacts and specs
├── _bmad/                # BMAD local configuration
├── .github/              # GitHub Actions workflows / repo config
├── .env.example          # Template for required environment variables
├── requirements.txt      # Python dependencies
├── app.py                # Main execution entry point (Streamlit)
├── README.md             # High-level project overview
└── CHANGELOG.md          # Version history
```

## Target Directory Tree

See [`source-architecture.md`](./source-architecture.md) for the full target structure with `src/nodes/`, `src/tools/`, `src/core/`, `src/prompts/`, `src/ui/`, and `src/utils/`.

## Critical Folders Explained

- **`app/`** (current): Contains all core logic in a flat layout. Being restructured into `src/` with separated concerns:
  - **`utils/`**: Mixes deterministic tools (spec_parser, gap_detector) with UI formatting (spec_review, visualization). Target: split into `src/tools/` and `src/ui/`.
  - **`pipeline.py`**: Monolith containing 10 node handlers, 6 routers, metadata, instrumentation, and graph builder. Target: nodes to `src/nodes/`, graph builder to `src/core/graph.py`.
  - **`state.py`**: Defines `SataState` — single source of truth. Target: `src/core/state.py` (unchanged logic).

- **`tests/`**: Automated tests for utility methods, app components, and LangGraph workflow nodes. Target: 3-tier split into `unit/`, `integration/`, `e2e/`.
