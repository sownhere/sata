---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
workflowType: 'architecture'
project_name: 'sata'
user_name: 'Sown'
date: '2026-03-29'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- Spec ingestion and clarification: users can upload an OpenAPI/Swagger JSON/YAML, import from a URL, or describe endpoints via chat when no spec exists (FR1–FR5). The system extracts endpoints/methods/params/schemas/auth (FR3) and asks targeted questions to resolve gaps (FR4).
- Human-in-the-loop checkpoints: the agent provides checkpointed review and confirmation before proceeding (FR6–FR9), then a test-plan review where categories can be enabled/disabled and destructive operations are acknowledged (FR13–FR16), and finally a results review with drill-down and a re-test loop (FR27–FR30).
- Test generation and execution: generate tests across 6+ defect categories with priorities (FR10–FR12), execute HTTP requests (FR17), support Bearer token/API-key auth (FR18), retry failures once with basic retry logic (FR19), and validate results by comparing status codes and response structure to expected schemas (FR20–FR21).
- Results interpretation: detect defect patterns (FR22), produce developer-friendly failure explanations (FR23), categorize failures by type/severity (FR24), and provide next-step diagnosis when all tests pass or all tests fail (FR25–FR26).
- Agent + pipeline architecture: ReAct tool usage with observable tool selection (FR31), 6+ tools with logged reasoning (FR32), and an 8+ node LangGraph pipeline with conditional routing (FR33), using shared typed state (`SataState`) (FR34), and validating generated tests against the confirmed spec to avoid hallucinated endpoints (FR35).
- UI/outputs: visualization of the LangGraph pipeline and agent reasoning logs (FR36–FR37) plus a results report with pass/fail and defect details (FR38), with a guided demo using sample APIs (FR39–FR40). If parsing yields no endpoints, the system falls back to conversational mode (FR41).

**Non-Functional Requirements:**
- Reliability: pipeline must complete end-to-end without crashing across multiple sample APIs; each LangGraph node must handle errors so a single failed case doesn’t crash the run; clear messaging when the target API is unreachable; Gemini errors/timeouts retried once; each node enforces a maximum iteration counter to prevent infinite loops/runaway costs (NFR1–NFR5).
- Security boundary: API keys come from `.env` only; auth tokens are included only in requests to the target API and never sent to Gemini or logged; no tokens/keys shown in Streamlit UI or agent reasoning logs (NFR6–NFR8).
- Integration: Gemini via OpenAI-compatible endpoint (`LLM_BASE_URL`); HTTP execution with configurable timeouts; OpenAPI/Swagger 3.0 parsing (JSON and YAML) (NFR9–NFR11).
- Performance/responsiveness: per-test execution within ~30 seconds; full pipeline for a 15-endpoint API within ~10 minutes; Streamlit UI stays responsive during pipeline execution (NFR12–NFR14).

### Scale & Complexity

- **Project complexity level:** Medium
- **Primary domain:** local full-stack (Python agents + Streamlit UI + HTTP execution)
- **Cross-cutting concerns identified:**
  - checkpoint gating (spec confirmation -> test plan review -> results review)
  - stateful multi-node orchestration (typed shared state + conditional routing)
  - strict “no hallucinated endpoints” validation against the confirmed spec
  - security boundary around tokens/keys (never to Gemini; never logged)
  - node-level resilience (timeouts/retries/max-iterations to prevent runaway)

### Technical Constraints & Dependencies

- Python 3.12+, Streamlit single-command startup, `.env`-based secrets.
- Must call Gemini through an OpenAI-compatible base URL.
- Must execute arbitrary HTTP methods (GET/POST/PUT/DELETE) with timeouts and basic retry logic.
- Later phases mention RAG for large/unstructured specs, but MVP must focus on the core checkpointed pipeline.

### Cross-Cutting Concerns Identified

- Human-in-the-loop controls must be architecture-enforced (not just “UI prompts”).
- Typed/shared state is required so all pipeline nodes interpret tool outputs consistently.
- Every stage needs graceful failure handling so the pipeline produces actionable outcomes rather than crashes.

## Starter Template Evaluation

### Primary Technology Domain

Web application (Python + Streamlit UI + agent orchestration) based on the PRD requirements.

### Starter Options Considered

- `gerardrbentley/cookiecutter-streamlit` (cookiecutter): Streamlit-first scaffolding for quickly getting the MVP UI runnable.
- `mcandemir/streamlit-project-template`: maintainability-focused Streamlit template with opinionated code structure.
- `uv init --app` + add Streamlit: modern Python project scaffold, but not Streamlit-specific.

### Selected Starter: `gerardrbentley/cookiecutter-streamlit`

**Rationale for Selection:**
- The project is UI-heavy for checkpoints/dashboard; a Streamlit-first scaffold reduces friction early.
- It lets architecture effort focus on the non-freezing execution pipeline, tool boundaries, and NFR enforcement.

**Initialization Command:**

```bash
python -m pip install cookiecutter
cookiecutter https://github.com/gerardrbentley/cookiecutter-streamlit
```

**Architectural Decisions Provided by Starter:**

- Streamlit-native project structure and run loop aligned with `streamlit run`.
- Clear module boundaries for later introduction of LangChain/LangGraph orchestration, tool calling, typed shared state, and HTTP execution/validation.

Note: project initialization using this command should be the first implementation story.

