---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments: ['README.md', '_bmad-output/brainstorming/brainstorming-session-2026-03-29-01.md']
workflowType: 'prd'
briefCount: 0
researchCount: 0
brainstormingCount: 1
projectDocsCount: 0
classification:
  projectType: developer_tool
  domain: general
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - Sata

**Author:** Sown
**Date:** 2026-03-29

## Executive Summary

Sata is an AI agent that automates API testing end-to-end. Developers and QA testers provide API documentation — an OpenAPI/Swagger spec, a Postman collection, or a plain conversation describing their endpoints — and Sata autonomously parses it into a structured API model, generates comprehensive test suites across multiple defect categories, executes HTTP requests, analyzes responses for defect patterns, and presents results in an interactive Streamlit dashboard. The entire pipeline is checkpoint-driven: Sata does the heavy lifting but pauses at three key stages (spec confirmation, test plan approval, results review) so users stay in control.

Target users are backend developers shipping APIs without dedicated QA support, and QA testers seeking faster coverage. The core problem: writing API test cases is tedious, repetitive, and requires expertise most developers don't have — so testing gets skipped and bugs reach production.

### What Makes This Special

Traditional API testing tools (Postman, pytest, REST-assured) require users to manually write every test case. Sata inverts this: it reasons about your API and generates tests you wouldn't have thought of — missing field validation, type mismatches, auth bypass, boundary values, destructive operation safety — then explains failures in developer-friendly language ("Your API created a user without an email") rather than cryptic assertions.

Sata uses RAG (Retrieval-Augmented Generation) to handle large or unstructured API documentation. Specs are chunked, embedded using `gemini-embedding-001`, and stored in a vector database (Chroma/FAISS). The agent retrieves relevant sections on demand — enabling it to parse massive API specs that exceed context limits, cross-reference original documentation when analyzing failures, and detect Documentation Drift where the spec no longer matches the API's actual behavior.

The core design insight is that the best testing agent is neither fully autonomous (unpredictable, risky) nor fully manual (tedious, incomplete). Sata operates as a collaborative QA teammate: it does the thinking and execution, but always shows its work and asks before acting. This human-in-the-loop architecture — built on LangChain + LangGraph with Gemini — uses a ReAct agent pattern with 6+ tools, 8 LangGraph nodes, and 5 conditional routing paths including a re-test loop for iterative deep analysis.

## Project Classification

- **Project Type:** Developer Tool
- **Domain:** Software Testing / Quality (General)
- **Complexity:** Medium — multi-agent AI architecture with no regulatory requirements
- **Project Context:** Greenfield
- **Tech Stack:** Python 3.12+, LangChain, LangGraph, Gemini (gemini-3-flash-preview), Streamlit, Chroma/FAISS (RAG)

## Success Criteria

### User Success

- User uploads an API spec and receives a complete test report with zero manual test writing
- Every failed test includes a developer-friendly explanation: what broke, why it matters, and how to fix it
- Users confirm the agent understood their API correctly before any tests run (no blind trust)
- Test coverage spans all available defect categories: happy path, missing data, invalid format, wrong type, auth failure, boundary, duplicate, method not allowed, and beyond
- Users with no API testing experience can operate Sata through the guided conversational flow

### Business Success

- **Graduation:** Meets all course requirements with demonstrated mastery across Lectures 1-4 (LLM basics, RAG, Agent & Tool Calling, LangGraph)
- **Demo quality:** Live demo runs end-to-end on a real API (PetStore) without failure during presentation
- **Portfolio value:** Project demonstrates AI agent engineering skills suitable for job interviews and portfolio showcasing

### Technical Success

- Agent reasoning is accurate — generated test cases match the confirmed spec with zero hallucinated endpoints
- Test results are correct — pass/fail judgments match actual API behavior
- The system handles errors gracefully: invalid input, API downtime, rate limiting, and timeouts produce helpful user messages rather than crashes
- LangGraph pipeline completes successfully through all 8 nodes with proper state management

### Measurable Outcomes

- **Accuracy:** 95%+ of generated test cases are valid and relevant to the confirmed spec
- **Coverage:** Minimum 6 defect categories generated per endpoint
- **Reliability:** Pipeline completes without crash on 3+ different sample APIs (PetStore, ReqRes, JSONPlaceholder)
- **Agent intelligence:** Agent uses 6+ tools with observable reasoning (logged and displayed in UI)

## Product Scope & Phased Development

### MVP Strategy

**Approach:** Problem-Solving MVP — deliver the core "zero manual test writing" value as fast as possible
**Resource:** Solo developer, 2-week timeline, graduation deadline
**Primary Journeys:** Minh (developer happy path) and Prof. Nguyen (grader demo) must work flawlessly

### MVP Feature Set (Phase 1)

- OpenAPI/Swagger spec upload and parsing
- Conversational fallback for gap-filling (ask_user_tool)
- 3 human-in-the-loop checkpoints (spec review, test plan, results)
- Test generation across 6+ defect categories
- HTTP test execution with basic retry logic
- Response validation against expected schema
- Results dashboard with pass/fail, defect details, and drill-down
- Auth configuration (Bearer token, API key)
- Destructive action warnings for DELETE/PUT endpoints
- Graph visualization page (LangGraph diagram)
- Demo with PetStore sample API
- 6+ LangChain tools with ReAct reasoning
- 8+ LangGraph nodes with 5+ conditional routes

**Deferred from MVP:**
- OAuth2 and complex auth flows
- Custom test case injection
- PDF/CSV export
- Visual charts (donut, radar, heatmap)

### Growth Features (Phase 2)

- RAG-powered documentation handling for large specs
- Visual charts and analytics (donut, radar, heatmap)
- Real-time execution view with progress bar
- Agent reasoning panel (live tool selection display)
- Multi-format export (JSON, CSV, PDF)
- Documentation Drift detection
- Rate limiting and timeout handling
- Smart defaults and minimal question routing

### Vision (Phase 3)

- "Surprise Me" creative edge case generation
- Test history and run comparison over time
- Custom test case injection alongside AI-generated tests
- Test coverage map visualization
- Auto-discovery mode (probe API from URL alone)
- CI/CD headless mode (skip checkpoints, full automation)
- Health score algorithm tracking API quality over time

### Risk Mitigation Strategy

**Technical Risks:**
- *Gemini output quality* — Mitigation: structured prompts with explicit output schemas, validate generated test cases against confirmed spec before execution
- *LangGraph state complexity* — Mitigation: build incrementally (linear pipeline first, add conditionals one at a time), use SataState TypedDict as single source of truth
- *API execution reliability* — Mitigation: timeouts, basic retry logic, clear error messages when target API is unreachable

**Resource Risks:**
- *Solo developer, 2-week deadline* — Mitigation: strict MVP boundary, no Growth features until after graduation
- *Fallback plan* — if any single feature blocks progress, cut it and document as Growth. The graduation checklist (3+ tools, 4+ nodes, conditional routing, UI) is the non-negotiable floor

## User Journeys

### Journey 1: Minh — Backend Developer, Happy Path

**Situation:** Minh is a junior backend developer at a startup. He just finished building a REST API for user management (CRUD operations). His tech lead asked him to "make sure it's properly tested" before deploying to staging. Minh has never written API tests — he's been manually testing with curl.

**Opening Scene:** It's Friday afternoon. Minh has a Swagger file auto-generated from his FastAPI app. He opens Sata's Streamlit UI, sees three tabs: Upload Spec / Chat With Me / URL Import. He drags his `openapi.json` into the upload area and clicks "Start Analysis."

**Rising Action:** Sata parses his spec and shows Checkpoint 1: "I found 5 endpoints. Here's what I understand." Minh sees an interactive table — all fields, types, required flags. He notices Sata flagged a gap: "PUT /users/:id — missing request body schema." He types in the chat: "same fields as POST but all optional." Sata updates the model. He clicks Confirm.

Sata generates 42 test cases across 8 categories and shows Checkpoint 2. Minh sees the category toggles — all P1 and P2 enabled. He notices DELETE /users/:id tests and Sata's warning: "These tests will DELETE real data. Are you testing against a test environment?" He confirms yes. He clicks Run Tests.

**Climax:** Results appear. 35 passed, 7 failed. Minh clicks the first failure: "POST /users accepted a request without an email field — returned 201 instead of 400. Your API created a user without an email address. Fix: Add email validation in your POST /users handler." Minh immediately understands the bug. He didn't even know this was a problem.

**Resolution:** Minh fixes the 7 validation gaps in 30 minutes, re-runs Sata, gets 42/42 green. He sends the report to his tech lead. It's 4pm — he was expecting to spend the whole weekend on this.

### Journey 2: Linh — QA Tester, Power User

**Situation:** Linh is a senior QA engineer at a mid-size company. She tests APIs daily using Postman. She's skeptical about AI testing tools — "they always miss the edge cases I know about." Her manager asked her to evaluate Sata.

**Opening Scene:** Linh uploads the company's payment API spec — 25 endpoints, complex auth with OAuth2. She wants to see if Sata can match her manual expertise.

**Rising Action:** At Checkpoint 1, Linh is impressed — Sata correctly identified all 25 endpoints and their auth requirements. But she notices it missed a business rule: "amount must be positive and have max 2 decimal places." She adds this via the chat panel. Sata updates the model.

At Checkpoint 2, Sata generated 187 test cases. Linh browses them by category. She's surprised — Sata generated boundary tests she wouldn't have considered: amount=0.001 (3 decimals), amount=999999999.99 (max value), negative amounts. But she wants to add her own: a duplicate payment within 1 second (race condition). She uses the custom test injection form to add it.

**Climax:** Results show 163 passed, 24 failed. The failure heatmap immediately reveals: all POST endpoints have weak input validation, and the /refund endpoint accepts unauthenticated requests. Linh clicks into the auth failure — Sata shows the exact request without a token that returned 200 instead of 401. She's found a real security vulnerability.

**Resolution:** Linh reports the security finding to the dev team with Sata's exported JSON report attached. She tells her manager: "It found a critical auth bypass I missed in my last manual test cycle. I'm keeping this tool."

### Journey 3: Tuan — Developer with No Docs, Conversational Mode

**Situation:** Tuan is a freelance developer. He built a small API for a client but never wrote documentation. The client wants proof it's been tested. Tuan has no Swagger file, no Postman collection — just a running API.

**Opening Scene:** Tuan opens Sata and clicks "Chat With Me." Sata asks: "Tell me about your API. What's the base URL?"

**Rising Action:** Through conversation, Sata asks structured questions:
- "What endpoints does it have?" → Tuan lists 3 endpoints
- "For POST /orders, what fields are required?" → Sata shows a multiple choice for field types
- "What auth do you use?" → Radio buttons: Bearer Token / API Key / Basic / None
- "What should happen when someone sends invalid data?" → Tuan says "return 400 with error message"

After 5 minutes of conversation, Sata shows Checkpoint 1 with the spec it built. Tuan sees his API model — structured for the first time ever.

**Climax:** Sata runs 28 tests. 20 pass, 8 fail. Tuan realizes his API has no input validation at all — every invalid input returns 200. He didn't know this was a problem because he always tested with valid data.

**Resolution:** Tuan fixes the issues and sends the client a PDF report showing all tests pass. The client is impressed. Tuan now uses Sata on every project — and he keeps the generated spec model as free documentation.

### Journey 4: Professor Nguyen — Course Grader

**Situation:** Professor Nguyen is grading 20 LangChain course graduation projects today. He has a checklist: agent reasoning, 3+ tools, 4+ LangGraph nodes, conditional routing, UI demo. He opens Sown's Sata project.

**Opening Scene:** He clicks the link to the Streamlit app. The landing page has a "Quick Demo" section with pre-loaded sample APIs. He selects "PetStore API" and clicks Start Demo.

**Rising Action:** The pipeline runs. At each checkpoint, he sees the agent's work. He clicks the "Graph Visualization" tab — the full LangGraph diagram renders automatically with 8 nodes and labeled conditional edges. He opens the "Agent Reasoning" panel — he can see the agent choosing tools in real-time: "Using parse_openapi_tool... Found 15 endpoints... Using generate_test_cases_tool for /pets happy path..."

**Climax:** Results dashboard loads — pass/fail metrics, charts, drill-down on failures. He checks his grading checklist: Agent with reasoning? Yes, visible in reasoning panel. 3+ tools? He counts 6 in the logs. 4+ nodes? 8 shown in the graph. Conditional routing? Three checkpoints plus a re-test loop. UI demo? This entire experience. Every box checked.

**Resolution:** Professor Nguyen gives full marks. He notes in his feedback: "Impressive architecture. The agent reasoning panel and graph visualization made evaluation straightforward. One of the strongest projects this cohort."

### Journey 5: Anh — Tech Lead Reviewing Results

**Situation:** Anh is the tech lead at Minh's startup. She doesn't run Sata herself — she reviews the results her developers send her. She needs to quickly assess API quality across multiple services and decide what to prioritize for fixing.

**Opening Scene:** Minh sends Anh a link to Sata's results dashboard for the user management API. She opens it on her laptop between meetings.

**Rising Action:** She sees the top-level metrics immediately: 35/42 passed, health score concept visible. The failure heatmap catches her eye — POST endpoints are red across validation categories, but GET and DELETE are green. She understands the pattern instantly: "Our write endpoints lack input validation."

She clicks into the defect analysis section. Sata's summary reads: "Pattern detected — all POST endpoints accept requests with missing required fields. Root cause: no server-side validation layer. Severity: Medium-High." She doesn't need to read 42 individual test results.

**Climax:** Anh opens the exported JSON report and drops it into the team's sprint board as a bug ticket with the exact findings attached. She adds a note: "Fix all POST validation before staging deploy. Sata report attached — see defect analysis section for details."

**Resolution:** The team fixes the issues in one sprint. Anh asks Minh to run Sata on every API before it goes to staging from now on. Sata becomes part of the team's quality gate process.

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---|---|
| Minh (Developer) | Spec upload, auto-parse, checkpoint flow, developer-friendly error messages, re-test loop |
| Linh (QA Tester) | Large spec handling, custom test injection, failure heatmap, JSON export, security detection |
| Tuan (No Docs) | Conversational spec builder, smart questions (radio/checkbox), PDF export, spec-as-documentation |
| Prof. Nguyen (Grader) | Demo script with sample APIs, graph visualization, agent reasoning panel, one-click demo |
| Anh (Tech Lead) | Results dashboard, defect pattern analysis, exportable reports, at-a-glance metrics |

## Developer Tool Specific Requirements

### Project-Type Overview

Sata is a locally-run developer tool accessed through a Streamlit web application. Users clone the repository, install dependencies, and launch the app locally. Target environment: developer's local machine with Python 3.12+.

### Installation & Setup

- **Distribution:** Git clone from repository
- **Dependencies:** `requirements.txt` with pinned versions (LangChain, LangGraph, Streamlit, ChromaDB/FAISS, etc.)
- **Launch:** `streamlit run app.py` (single command startup)
- **Configuration:** `.env` file for API keys (`LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`)
- **No Docker required** for MVP — local Python environment is sufficient

### API Surface

Sata is not consumed as a library — its "API surface" is the Streamlit UI:
- File upload widget (OpenAPI/Swagger specs)
- Chat interface (conversational spec building)
- Interactive checkpoint panels (confirm/reject/modify)
- Results dashboard with drill-down

### Sample APIs & Examples

Bundled demo configurations pointing to public APIs:
- **PetStore** (Swagger sample) — primary demo API
- **ReqRes** (reqres.in) — user management CRUD
- **JSONPlaceholder** — simple REST endpoints

Users can also provide any public API URL or upload their own spec.

### Documentation

Full documentation planned post-MVP. Not in scope for initial development.

## Functional Requirements

### API Spec Ingestion

- **FR1:** User can upload an OpenAPI/Swagger JSON or YAML file for parsing
- **FR2:** User can describe API endpoints through conversational chat when no spec file exists
- **FR3:** System can extract endpoints, methods, parameters, request/response schemas, and auth requirements from uploaded specs
- **FR4:** System can identify gaps in parsed specs and ask the user targeted questions to fill them
- **FR5:** User can provide a URL to a public API spec for import

### Spec Confirmation (Checkpoint 1)

- **FR6:** System presents the parsed API model to the user for review before proceeding
- **FR7:** User can view all discovered endpoints, fields, types, and required flags in a structured format
- **FR8:** User can modify, add, or remove endpoints and fields during spec review
- **FR9:** User can confirm the spec to proceed or reject to re-parse

### Test Generation

- **FR10:** System can generate test cases across 6+ defect categories (happy path, missing data, invalid format, wrong type, auth failure, boundary, duplicate, method not allowed)
- **FR11:** System can assign priority levels (P1, P2, P3) to generated test cases
- **FR12:** System can generate destructive operation warnings for DELETE/PUT test cases

### Test Plan Review (Checkpoint 2)

- **FR13:** System presents all generated test cases grouped by category for user review
- **FR14:** User can enable or disable test categories before execution
- **FR15:** User can confirm the test plan to proceed or reject to regenerate
- **FR16:** User can acknowledge destructive operation warnings before those tests execute

### Test Execution

- **FR17:** System can execute HTTP requests against target API endpoints
- **FR18:** System can handle Bearer token and API key authentication in requests
- **FR19:** System can retry failed requests with basic retry logic
- **FR20:** System can validate API responses against expected schemas
- **FR21:** System can detect pass/fail based on expected vs actual status codes and response structure

### Results Analysis

- **FR22:** System can analyze test results and identify defect patterns across endpoints
- **FR23:** System can generate developer-friendly failure explanations (what broke, why it matters, how to fix)
- **FR24:** System can categorize failures by defect type and severity
- **FR25:** System can suggest deeper testing areas when all tests pass
- **FR26:** System can provide smart diagnosis when all tests fail (auth misconfiguration, wrong URL, API down)

### Results Review (Checkpoint 3)

- **FR27:** User can view results dashboard with pass/fail metrics and drill-down
- **FR28:** User can drill into individual test failures to see request, response, and explanation
- **FR29:** User can request deeper analysis or re-testing of specific areas
- **FR30:** User can trigger a re-test loop after fixing issues

### Agent Architecture

- **FR31:** System uses ReAct agent reasoning with observable tool selection
- **FR32:** System operates 6+ LangChain tools with logged reasoning
- **FR33:** System runs an 8+ node LangGraph pipeline with 5+ conditional routing paths
- **FR34:** System manages shared state across all pipeline nodes via SataState
- **FR35:** System validates generated test cases against the confirmed spec before execution (no hallucinated endpoints)

### Visualization & Reporting

- **FR36:** User can view the LangGraph pipeline as a visual graph diagram
- **FR37:** User can view agent reasoning logs showing tool selection decisions
- **FR38:** System can generate a results report with pass/fail summary and defect details

### Demo & Sample Data

- **FR39:** User can select from pre-loaded sample APIs (PetStore, ReqRes, JSONPlaceholder) for quick demo
- **FR40:** System provides a guided demo flow that runs end-to-end on sample data

### Edge Case Handling

- **FR41:** System falls back to conversational mode when zero endpoints are found in a parsed spec

## Non-Functional Requirements

### Reliability

- Pipeline completes end-to-end without crashing on well-formed input across 3+ sample APIs (PetStore, ReqRes, JSONPlaceholder)
- Each LangGraph node handles errors gracefully — a single failed test case does not crash the entire pipeline
- If the target API is unreachable, the system displays a clear error message and allows the user to retry or skip
- If the Gemini API returns an error or times out, the system retries once and displays a helpful message on second failure
- Each LangGraph node enforces a maximum iteration counter to prevent infinite loops and runaway API costs

### Security

- API keys are stored in `.env` files only, never hardcoded or logged
- User-provided auth tokens (Bearer, API key) are included only in requests to the target API, never sent to Gemini or logged in the UI
- No API keys or tokens are displayed in the Streamlit UI or agent reasoning logs

### Integration

- System communicates with Gemini API via OpenAI-compatible endpoint (`LLM_BASE_URL`)
- System executes HTTP requests (GET, POST, PUT, DELETE) against arbitrary target APIs with configurable timeouts
- System parses OpenAPI/Swagger 3.0 spec format (JSON and YAML)

### Performance

- Individual test case execution completes within 30 seconds (including API response wait)
- Full pipeline for a 15-endpoint API completes within 10 minutes
- Streamlit UI remains responsive during pipeline execution (no frozen UI)
