# Source Tree Analysis

This document provides an overview of the directory structure and key file locations for the Sata project.

## Directory Tree

```
project-root/
├── app/                  # Main application package
│   ├── utils/            # Shared utilities
│   │   ├── env.py              # Environment validation logic
│   │   ├── spec_fetcher.py     # Remote OpenAPI spec HTTP fetching
│   │   ├── spec_gap_detector.py # Deterministic OpenAPI gap analysis
│   │   └── spec_parser.py      # OpenAPI JSON/YAML parsing
│   ├── __init__.py
│   ├── app.py            # Streamlit UI entry point
│   ├── pipeline.py       # LangGraph orchestration and nodes
│   └── state.py          # Typed shared state definition (SataState)
├── docs/                 # Project knowledge and generated documentation
├── tests/                # Test suite
├── _bmad-output/         # BMAD generated artifacts and specs
├── _bmad/                # BMAD local configuration
├── .github/              # GitHub Actions workflows / repo config
├── .env.example          # Template for required environment variables
├── requirements.txt      # Python dependencies
├── app.py                # Main execution entry point (Streamlit)
├── README.md             # High-level project overview
└── CHANGELOG.md          # Version history
```

## Critical Folders Explained

- **`app/`**: Contains the core logic of the Sata AI Agent. Divided into:
  - **`utils/`**: Helper methods for fetching and processing OpenAPI schemas, maintaining deterministic logic away from AI stubs.
  - **`app.py`**: The Streamlit application UI layer. Displays standard inputs, persistent headers, and routes state updates back into the graph.
  - **`pipeline.py`**: The LangGraph state machine. Defines stubs and real node logic, handling transitions based on parsed specs or chat interactions.
  - **`state.py`**: Defines `SataState`, acting as the single source of truth passed across all nodes in the Graph.

- **`tests/`**: Contains the automated tests validating the utility methods, app components, and LangGraph workflow nodes.
