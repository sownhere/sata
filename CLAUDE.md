# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Sata?

AI agent for automated API testing and test-result analysis. It ingests API specs (OpenAPI/Swagger or free-form chat), generates test suites, executes them, analyzes results, and surfaces defects via a Streamlit dashboard.

## Commands

```bash
# Install dependencies (uv manages the virtualenv automatically)
uv sync --extra dev

# Run the app
uv run streamlit run app.py

# Run all tests
uv run pytest tests/ --tb=short -q

# Run a single test file
uv run pytest tests/test_spec_parser.py --tb=short -q

# Lint
uvx ruff check app/ tests/ app.py src/
uvx ruff format --check app/ tests/ app.py src/
```

## Environment

Requires a `.env` file (copy from `.env.example`):
- `LLM_API_KEY` — Gemini API key
- `LLM_CHAT_MODEL` — e.g. `gemini-2.0-flash`
- `LLM_BASE_URL` — OpenAI-compatible endpoint for Gemini
- `LLM_EMBEDDING_MODEL` — for RAG (Phase 2)

Python 3.11+ (CI runs 3.11). Linting via Ruff with default config. Max line length 88 chars.

## Architecture

Full details in `docs/source-architecture.md`. The project is migrating from a flat `app/` layout to a layered `src/` structure (Epic 7).

### Current structure (`app/`)

- `app.py` — Streamlit entry point, session state init, UI rendering
- `app/state.py` — `SataState(TypedDict)` — single source of truth for all pipeline data
- `app/pipeline.py` — 10-node LangGraph state machine with conditional routing edges
- `app/utils/` — Deterministic business logic utilities (no AI stubs)

### Target structure (`src/`)

```
src/
├── nodes/       # 1 file per pipeline node (ingest_spec.py, parse_spec.py, ...)
├── tools/       # Deterministic tools (spec_parser, gap_detector, spec_fetcher, ...)
├── core/        # Foundation: state.py, models.py, graph.py, config.py, prompts.py
├── prompts/     # Externalized LLM prompts as .md files
├── ui/          # Streamlit-specific presentation code
└── utils/       # Infrastructure utilities (auth, logging, reporting)
```

**Dependency rule:** `nodes → tools → core`, `ui → core`. No reverse or lateral imports.

### Pipeline flow (10 nodes)

```
ingest_spec → parse_spec → detect_gaps → fill_gaps → review_spec
→ generate_tests → review_test_plan → execute_tests
→ analyze_results → review_results → END
```

Two human-in-the-loop checkpoints: `review_spec` (spec confirmation) and `review_test_plan` (test plan approval).

## Git Conventions

Full details in `GIT_CONVENTION.md`. Key rules:

- **Git Flow**: `main` (production, tagged) and `develop` (integration). Feature branches: `feat/*`, `fix/*`, `refactor/*`
- **Commits**: Conventional Commits format — `<type>(<scope>): <subject>` (max 72 chars, imperative, lowercase)
- **Types**: feat, fix, docs, style, refactor, perf, test, chore, ci, revert
- **PRs must have exactly 1 commit** (squash before pushing; enforced by CI)
- **No direct push** to `main` or `develop` (enforced by `.githooks/pre-push`)
- **Merge strategy**: squash on feature branch + merge commit (`--no-ff`) to develop

## CI Pipeline

Runs on push to `develop` and PRs to `main`/`develop` (`.github/workflows/ci.yml`):

1. **Lint**: ruff check + format check, single-commit enforcement, conventional commit validation
2. **Test**: `pytest tests/ --tb=short -q`
3. **Build**: `py_compile` syntax check

CI excludes `_bmad/`, `.agents/`, `.claude/`, `.cursor/` from linting.
