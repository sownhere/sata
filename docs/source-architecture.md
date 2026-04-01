# Source Architecture

This document defines the target source code structure for Sata, based on best practices from LangGraph official patterns, production agent harness architectures, and AI agent community conventions.

**Status:** Target architecture — to be implemented via Epic 7 (Source Architecture Restructuring).

## Design Principles

1. **Separate deterministic logic from LLM-dependent logic.** Tools are pure functions; nodes orchestrate LLM calls and state transitions.
2. **One node, one file.** Each LangGraph pipeline node lives in its own module for independent development and testing.
3. **Externalize prompts.** All LLM prompt strings live in versioned markdown files, not inline Python strings.
4. **Layered dependency direction.** `nodes → tools → core` and `ui → core`. No reverse or lateral imports.
5. **3-tier testing.** Unit tests for isolated logic, integration tests for graph flows, e2e tests for full pipeline runs.

## Target Directory Structure

```
sata/
├── src/                             # Main source package
│   ├── __init__.py
│   │
│   ├── nodes/                       # Pipeline nodes (1 file per LangGraph node)
│   │   ├── __init__.py              # Re-exports all node handlers
│   │   ├── ingest_spec.py
│   │   ├── parse_spec.py
│   │   ├── detect_gaps.py
│   │   ├── fill_gaps.py
│   │   ├── review_spec.py
│   │   ├── generate_tests.py        # Stub until Epic 3
│   │   ├── review_test_plan.py      # Stub until Epic 3
│   │   ├── execute_tests.py         # Stub until Epic 4
│   │   ├── analyze_results.py       # Stub until Epic 5
│   │   └── review_results.py        # Stub until Epic 5
│   │
│   ├── tools/                       # Deterministic tools (no LangGraph/Streamlit deps)
│   │   ├── __init__.py              # Public API re-exports
│   │   ├── spec_parser.py           # OpenAPI/Swagger JSON/YAML parsing
│   │   ├── spec_fetcher.py          # Remote spec fetch (SSRF protection, 10MB limit)
│   │   ├── gap_detector.py          # Gap analysis (missing responses, auth ambiguity)
│   │   ├── conversational_builder.py # LLM-based API model extraction from chat
│   │   ├── api_client.py            # HTTP test execution (future — Epic 4)
│   │   ├── data_generator.py        # Test data generation (future — Epic 3)
│   │   └── security_scanner.py      # Injection/rate-limit checks (future — Phase 2)
│   │
│   ├── core/                        # Foundation layer (state, models, config, graph)
│   │   ├── __init__.py
│   │   ├── state.py                 # SataState TypedDict + initial_state()
│   │   ├── models.py                # Pydantic models (EndpointModel, ApiModel, GapRecord, TestCase...)
│   │   ├── graph.py                 # build_pipeline(), routing functions, node metadata
│   │   ├── config.py                # Settings loader (env + yaml merge)
│   │   └── prompts.py               # load_prompt() utility with caching
│   │
│   ├── prompts/                     # Externalized LLM prompts as markdown
│   │   ├── conversational_extraction.md
│   │   ├── conversation_starter.md
│   │   ├── test_generation.md       # Placeholder until Epic 3
│   │   ├── result_analysis.md       # Placeholder until Epic 5
│   │   └── gap_filling.md           # Placeholder until Epic 3
│   │
│   ├── ui/                          # Streamlit-specific presentation code
│   │   ├── __init__.py
│   │   ├── components.py            # Shared Streamlit widget helpers
│   │   ├── spec_review.py           # Checkpoint 1 review panel formatting
│   │   └── visualization.py         # Pipeline graph DOT rendering
│   │
│   └── utils/                       # Pure infrastructure utilities
│       ├── __init__.py
│       ├── auth_manager.py          # Auth token management (future — Epic 4)
│       ├── logger.py                # Structured logging (future)
│       └── report_generator.py      # Report export (future — Epic 5)
│
├── config/
│   └── settings.yaml                # Non-secret tuning (timeouts, retries, model params)
│
├── tests/
│   ├── __init__.py
│   ├── unit/                        # Node & tool tests in isolation (mocked deps)
│   │   ├── __init__.py
│   │   ├── test_state.py
│   │   ├── test_config.py
│   │   ├── test_spec_parser.py
│   │   ├── test_spec_fetcher.py
│   │   ├── test_gap_detector.py
│   │   ├── test_conversational_builder.py
│   │   ├── test_spec_review.py
│   │   └── test_pipeline_visualization.py
│   ├── integration/                 # Graph flow tests (compiled graph, routing)
│   │   ├── __init__.py
│   │   ├── test_pipeline.py
│   │   ├── test_parse_spec_node.py
│   │   └── test_review_spec_node.py
│   └── e2e/                         # Full pipeline with recorded LLM responses
│       ├── __init__.py
│       └── .gitkeep
│
├── reports/                         # Generated test reports (gitignored)
├── examples/                        # Sample API specs (petstore, reqres, jsonplaceholder)
│
├── app.py                           # Thin Streamlit entrypoint (imports from src.ui)
├── main.py                          # CLI entrypoint (future — typer/rich)
├── .env.example
├── requirements.txt
├── README.md
└── CLAUDE.md
```

## Dependency Graph

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  src/ui/  │────▶│src/core/ │◀────│src/nodes/│
└──────────┘     └──────────┘     └──────────┘
                       ▲                │
                       │                ▼
                 ┌──────────┐    ┌───────────┐
                 │ config/  │    │src/tools/  │
                 └──────────┘    └───────────┘
                       ▲                │
                       │                ▼
                 ┌──────────┐    ┌───────────┐
                 │  .env    │    │ src/core/  │
                 └──────────┘    └───────────┘
```

**Rules:**
- `nodes/` imports from `core/` and `tools/` — never from `ui/` or other nodes
- `tools/` imports from `core/` only — never from `nodes/`, `ui/`, or other tools
- `ui/` imports from `core/` only — never from `nodes/` or `tools/`
- `core/` imports from nothing within `src/` (foundation layer)
- `app.py` (entrypoint) imports from `ui/`, `core/config`, and `core/graph`

## Layer Responsibilities

### `src/core/` — Foundation Layer
The bottom of the dependency graph. Contains the shared contracts that all other layers depend on.

| Module | Responsibility |
|--------|---------------|
| `state.py` | `SataState` TypedDict — single source of truth for all pipeline data |
| `models.py` | Pydantic models (`EndpointModel`, `ApiModel`, `GapRecord`, `TestCase`, `TestResult`) for validation at system boundaries |
| `graph.py` | `build_pipeline()`, `PIPELINE_NODE_ORDER`, `PIPELINE_NODE_METADATA`, routing functions, instrumentation helpers |
| `config.py` | Loads `.env` (secrets) + `config/settings.yaml` (tuning). Exposes typed `Settings` object |
| `prompts.py` | `load_prompt(name)` — reads from `src/prompts/*.md` with caching |

### `src/nodes/` — Pipeline Nodes
Each file contains exactly one LangGraph node handler with signature:
```python
def node_name(state: SataState) -> SataState:
```
Node-private helpers are prefixed with `_` and live in the same file.

### `src/tools/` — Deterministic Tools
Pure functions that nodes call to do specific work. No LangGraph, no Streamlit, no cross-tool imports. Testable with simple `assert` statements.

### `src/prompts/` — Versioned Prompts
Markdown files containing LLM prompt text. Loaded at runtime by `core/prompts.py`. Changes to prompts require no Python code changes. Each prompt change is visible in `git diff`.

### `src/ui/` — Streamlit Presentation
All Streamlit-specific widget code, layout logic, and formatting helpers. Isolated from business logic so the pipeline can be tested without Streamlit.

### `src/utils/` — Infrastructure Utilities
Cross-cutting concerns: auth token management, structured logging, report generation. Not business logic — pure infrastructure.

## Configuration Strategy

| What | Where | Example |
|------|-------|---------|
| Secrets (API keys, tokens) | `.env` (loaded by `python-dotenv`) | `LLM_API_KEY=sk-...` |
| Tuning parameters | `config/settings.yaml` (loaded by PyYAML) | `pipeline.max_iterations: 10` |
| Prompt content | `src/prompts/*.md` (loaded by `core/prompts.py`) | System prompt text |

Environment variables always override yaml values for any overlapping keys.

## Testing Strategy

| Tier | Directory | What it tests | Speed | Dependencies |
|------|-----------|---------------|-------|-------------|
| Unit | `tests/unit/` | Individual tools and node functions in isolation | Fast | Mocked LLM, no network |
| Integration | `tests/integration/` | Graph compilation, routing logic, node transitions | Medium | Compiled graph with mocked nodes |
| E2E | `tests/e2e/` | Full pipeline with recorded LLM responses (VCR) | Slow | Recorded HTTP cassettes |

**CI command:** `pytest tests/ --tb=short -q` (runs all tiers).
**Dev command:** `pytest tests/unit/ --tb=short -q` (fast feedback loop).

## Migration Path from Current Structure

| Current | Target | Story |
|---------|--------|-------|
| `app/state.py` | `src/core/state.py` | 7.1 |
| `app/utils/env.py` | `src/core/config.py` | 7.1 |
| (new) | `src/core/models.py` | 7.1 |
| `app/utils/spec_parser.py` | `src/tools/spec_parser.py` | 7.2 |
| `app/utils/spec_fetcher.py` | `src/tools/spec_fetcher.py` | 7.2 |
| `app/utils/spec_gap_detector.py` | `src/tools/gap_detector.py` | 7.2 |
| `app/utils/conversational_spec_builder.py` | `src/tools/conversational_builder.py` | 7.2 |
| `app/pipeline.py` (node handlers) | `src/nodes/*.py` | 7.3 |
| `app/pipeline.py` (graph builder + routing) | `src/core/graph.py` | 7.3 |
| Inline prompt strings | `src/prompts/*.md` | 7.4 |
| `app/utils/spec_review.py` | `src/ui/spec_review.py` | 7.5 |
| `app/utils/pipeline_visualization.py` | `src/ui/visualization.py` | 7.5 |
| `app.py` (UI logic) | `src/ui/components.py` + thin `app.py` | 7.5 |
| `tests/*.py` (flat) | `tests/unit/` + `tests/integration/` | 7.6 |
| (new) | `config/settings.yaml` | 7.7 |

## Naming Conventions

- **Nodes:** `src/nodes/<node_name>.py` — matches `PIPELINE_NODE_ORDER` names exactly
- **Tools:** `src/tools/<tool_name>.py` — descriptive, no `spec_` prefix unless disambiguating
- **Prompts:** `src/prompts/<purpose>.md` — lowercase, hyphens not underscores
- **Tests:** `tests/<tier>/test_<module_name>.py` — mirrors the source module being tested
