---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# sata - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for sata, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can upload an OpenAPI/Swagger JSON or YAML file for parsing
FR2: User can describe API endpoints through conversational chat when no spec file exists
FR3: System can extract endpoints, methods, parameters, request/response schemas, and auth requirements from uploaded specs
FR4: System can identify gaps in parsed specs and ask the user targeted questions to fill them
FR5: User can provide a URL to a public API spec for import
FR6: System presents the parsed API model to the user for review before proceeding
FR7: User can view all discovered endpoints, fields, types, and required flags in a structured format
FR8: User can modify, add, or remove endpoints and fields during spec review
FR9: User can confirm the spec to proceed or reject to re-parse
FR10: System can generate test cases across 6+ defect categories (happy path, missing data, invalid format, wrong type, auth failure, boundary, duplicate, method not allowed)
FR11: System can assign priority levels (P1, P2, P3) to generated test cases
FR12: System can generate destructive operation warnings for DELETE/PUT test cases
FR13: System presents all generated test cases grouped by category for user review
FR14: User can enable or disable test categories before execution
FR15: User can confirm the test plan to proceed or reject to regenerate
FR16: User can acknowledge destructive operation warnings before those tests execute
FR17: System can execute HTTP requests against target API endpoints
FR18: System can handle Bearer token and API key authentication in requests
FR19: System can retry failed requests with basic retry logic
FR20: System can validate API responses against expected schemas
FR21: System can detect pass/fail based on expected vs actual status codes and response structure
FR22: System can analyze test results and identify defect patterns across endpoints
FR23: System can generate developer-friendly failure explanations (what broke, why it matters, how to fix)
FR24: System can categorize failures by defect type and severity
FR25: System can suggest deeper testing areas when all tests pass
FR26: System can provide smart diagnosis when all tests fail (auth misconfiguration, wrong URL, API down)
FR27: User can view results dashboard with pass/fail metrics and drill-down
FR28: User can drill into individual test failures to see request, response, and explanation
FR29: User can request deeper analysis or re-testing of specific areas
FR30: User can trigger a re-test loop after fixing issues
FR31: System uses ReAct agent reasoning with observable tool selection
FR32: System operates 6+ LangChain tools with logged reasoning
FR33: System runs an 8+ node LangGraph pipeline with 5+ conditional routing paths
FR34: System manages shared state across all pipeline nodes via SataState
FR35: System validates generated test cases against the confirmed spec before execution (no hallucinated endpoints)
FR36: User can view the LangGraph pipeline as a visual graph diagram
FR37: User can view agent reasoning logs showing tool selection decisions
FR38: System can generate a results report with pass/fail summary and defect details
FR39: User can select from pre-loaded sample APIs (PetStore, ReqRes, JSONPlaceholder) for quick demo
FR40: System provides a guided demo flow that runs end-to-end on sample data
FR41: System falls back to conversational mode when zero endpoints are found in a parsed spec

### NonFunctional Requirements

NFR1: Pipeline completes end-to-end without crashing on well-formed input across 3+ sample APIs (PetStore, ReqRes, JSONPlaceholder)
NFR2: Each LangGraph node handles errors gracefully so a single failed test case does not crash the entire pipeline
NFR3: If the target API is unreachable, the system displays a clear error message and allows the user to retry or skip
NFR4: If the Gemini API returns an error or times out, the system retries once and displays a helpful message on second failure
NFR5: Each LangGraph node enforces a maximum iteration counter to prevent infinite loops and runaway API costs
NFR6: API keys are stored in `.env` files only, never hardcoded or logged
NFR7: User-provided auth tokens (Bearer, API key) are included only in requests to the target API, never sent to Gemini or logged in the UI
NFR8: No API keys or tokens are displayed in the Streamlit UI or agent reasoning logs
NFR9: System communicates with Gemini API via OpenAI-compatible endpoint (`LLM_BASE_URL`)
NFR10: System executes HTTP requests (GET, POST, PUT, DELETE) against arbitrary target APIs with configurable timeouts
NFR11: System parses OpenAPI/Swagger 3.0 spec format (JSON and YAML)
NFR12: Individual test case execution completes within 30 seconds (including API response wait)
NFR13: Full pipeline for a 15-endpoint API completes within 10 minutes
NFR14: Streamlit UI remains responsive during pipeline execution (no frozen UI)

### Additional Requirements

- Project is a locally-run developer tool accessed via a Streamlit web application on the developer's machine
- Distribution is via git clone with dependencies pinned in `requirements.txt`
- Launch flow is a single command (`streamlit run app.py`) with configuration from `.env`
- System must support bundled demo configurations for public APIs (PetStore, ReqRes, JSONPlaceholder)
- Project initialization should use the `gerardrbentley/cookiecutter-streamlit` starter template as the first implementation story
- Architecture must enforce human-in-the-loop controls at each checkpoint rather than relying only on UI prompts
- Typed shared state (`SataState`) must be the single source of truth for all pipeline nodes
- Every pipeline stage must implement graceful failure handling so the user always receives actionable outcomes
- Secrets and tokens must never be sent to Gemini or logged in any UI or reasoning logs

### UX Design Requirements

UX-DR1: Implement a persistent "Stage header" that clearly shows the current checkpoint stage (Spec confirmation, Test plan approval, Results review, Running) across relevant UI areas
UX-DR2: Provide a consistent "Next required action" area that always explains what the user must do to progress (e.g., confirm spec, approve test plan, start execution)
UX-DR3: Build interactive checkpoint panels using editable tables for spec review and test plan preview, including gap warnings and explicit Confirm/Reject actions
UX-DR4: Implement category toggles with priority grouping (P1, P2, P3) and surface destructive-operation warnings directly next to affected endpoints/tests
UX-DR5: Design results dashboard UX for rapid triage with defect pattern summaries, a heatmap, and drill-down linking each failure to its test definition and explanation
UX-DR6: Ensure rejection paths (e.g., rejecting a checkpoint or requesting deeper analysis) clearly state which pipeline stage the user is returning to and why
UX-DR7: Keep the Streamlit UI responsive during parsing, test generation, execution, and analysis, with visible progress indicators for each phase
UX-DR8: Provide clear, dedicated empty/error/fallback states (e.g., when zero endpoints are found and the app switches to conversational mode) that tell users what happened and what to do next
UX-DR9: Implement safety-focused UX for auth configuration and destructive-operation warnings so users cannot accidentally execute tests against the wrong environment or without understanding the risk

### FR Coverage Map

FR1: Epic 1 — User can upload an OpenAPI/Swagger file for parsing
FR2: Epic 1 — User can describe API endpoints through conversational chat
FR3: Epic 1 — System extracts endpoints, methods, parameters, schemas, auth from uploaded specs
FR4: Epic 1 — System identifies spec gaps and asks targeted questions to fill them
FR5: Epic 1 — User can provide a URL to a public API spec for import
FR6: Epic 2 — System presents parsed API model to user for review
FR7: Epic 2 — User can view all discovered endpoints, fields, types, and required flags
FR8: Epic 2 — User can modify, add, or remove endpoints and fields during spec review
FR9: Epic 2 — User can confirm the spec to proceed or reject to re-parse
FR10: Epic 3 — System generates test cases across 6+ defect categories
FR11: Epic 3 — System assigns priority levels (P1, P2, P3) to test cases
FR12: Epic 3 — System generates destructive operation warnings for DELETE/PUT
FR13: Epic 3 — System presents generated test cases grouped by category for review
FR14: Epic 3 — User can enable or disable test categories before execution
FR15: Epic 3 — User can confirm the test plan or reject to regenerate
FR16: Epic 3 — User must acknowledge destructive operation warnings before execution
FR17: Epic 4 — System executes HTTP requests against target API endpoints
FR18: Epic 4 — System handles Bearer token and API key authentication
FR19: Epic 4 — System retries failed requests with basic retry logic
FR20: Epic 4 — System validates API responses against expected schemas
FR21: Epic 4 — System detects pass/fail based on status codes and response structure
FR22: Epic 4 — System analyzes test results and identifies defect patterns
FR23: Epic 4 — System generates developer-friendly failure explanations
FR24: Epic 4 — System categorizes failures by defect type and severity
FR25: Epic 4 — System suggests deeper testing areas when all tests pass
FR26: Epic 4 — System provides smart diagnosis when all tests fail
FR27: Epic 5 — User can view results dashboard with pass/fail metrics and drill-down
FR28: Epic 5 — User can drill into individual test failures (request, response, explanation)
FR29: Epic 5 — User can request deeper analysis or re-testing of specific areas
FR30: Epic 5 — User can trigger a re-test loop after fixing issues
FR31: Epic 1 — System uses ReAct agent reasoning with observable tool selection
FR32: Epic 1 — System operates 6+ LangChain tools with logged reasoning
FR33: Epic 1 — System runs an 8+ node LangGraph pipeline with 5+ conditional routing paths
FR34: Epic 1 — System manages shared state across all pipeline nodes via SataState
FR35: Epic 3 — System validates generated test cases against confirmed spec (no hallucinated endpoints)
FR36: Epic 6 — User can view the LangGraph pipeline as a visual graph diagram
FR37: Epic 6 — User can view agent reasoning logs showing tool selection decisions
FR38: Epic 5 — System generates a results report with pass/fail summary and defect details
FR39: Epic 6 — User can select from pre-loaded sample APIs for quick demo
FR40: Epic 6 — System provides a guided demo flow that runs end-to-end on sample data
FR41: Epic 1 — System falls back to conversational mode when zero endpoints are found

## Epic List

### Epic 1: Working Foundation — Project Setup & Spec Ingestion
Users can launch the tool locally, provide an API spec (file upload, URL, or conversational description), and see parsed endpoints ready for review. The core LangGraph pipeline skeleton and shared state are established.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR31, FR32, FR33, FR34, FR41
**NFRs:** NFR1, NFR6, NFR9, NFR10, NFR11
**Key notes:** First story uses `cookiecutter-streamlit` starter template; `SataState` initialized; `.env`-only secrets enforced; fallback to conversational mode when no endpoints found.

### Epic 2: Spec Review & Human Checkpoint
Users can view all discovered endpoints and fields, edit or remove entries, and explicitly confirm or reject the spec at a human checkpoint before any tests are generated.
**FRs covered:** FR6, FR7, FR8, FR9
**NFRs:** NFR3
**UX:** UX-DR1 (stage header), UX-DR2 (next required action), UX-DR3 (checkpoint panels with editable tables), UX-DR6 (rejection paths), UX-DR9 (safety-focused auth/env UX)

### Epic 3: Test Plan Generation & Configuration
Users can generate a prioritized, categorized test plan, configure which categories run, review destructive-operation warnings, and confirm or reject the plan before execution.
**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR35
**UX:** UX-DR4 (category toggles with P1/P2/P3 grouping), UX-DR3 (checkpoint panels), UX-DR9 (destructive-op safety)

### Epic 4: Test Execution & Analysis
Users can execute the confirmed test plan against their target API, monitor progress, and receive intelligent analysis with developer-friendly failure explanations and smart diagnosis when all tests fail.
**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR26
**NFRs:** NFR2, NFR3, NFR4, NFR5, NFR12, NFR13, NFR14
**UX:** UX-DR7 (progress indicators, responsive UI during execution)

### Epic 5: Results Dashboard, Reporting & Iteration
Users can explore results through a drill-down dashboard with pass/fail metrics, generate a summary report, request deeper analysis, and trigger re-test loops after fixing issues.
**FRs covered:** FR27, FR28, FR29, FR30, FR38
**UX:** UX-DR5 (heatmap, drill-down, defect pattern summaries)

### Epic 6: Pipeline Observability & Demo Mode
Users and developers can inspect agent reasoning logs, visualize the full LangGraph pipeline as a diagram, and run end-to-end guided demos on pre-loaded sample APIs (PetStore, ReqRes, JSONPlaceholder).
**FRs covered:** FR36, FR37, FR39, FR40
**NFRs:** NFR7, NFR8

---

## Epic 1: Working Foundation — Project Setup & Spec Ingestion

Users can launch the tool locally, provide an API spec (file upload, URL, or conversational description), and see parsed endpoints ready for review. The core LangGraph pipeline skeleton and shared state are established.

### Story 1.1: Project Foundation — Scaffold & Pipeline Skeleton

As a developer,
I want a runnable Streamlit app initialized from the cookiecutter-streamlit template with the full LangGraph pipeline skeleton and SataState wired up,
So that every subsequent story has a known, consistent structure to slot into.

**Acceptance Criteria:**

**Given** the developer has cloned the repo and copied `.env.example` to `.env` with valid keys
**When** they run `streamlit run app.py`
**Then** the Streamlit UI opens in the browser without errors

**Given** the app is running
**When** the developer inspects the app
**Then** a stage header is visible showing the current pipeline stage (stub: "Spec Ingestion")
**And** the LangGraph pipeline is instantiated with 8+ named nodes (stubs returning passthrough state)
**And** `SataState` TypedDict is defined and passed between all nodes as the single source of truth

**Given** no `.env` file exists or required keys are missing
**When** the app starts
**Then** a clear error message is displayed listing the missing variables
**And** the app does not crash silently

**Given** the `.env` file exists with valid keys
**When** the app initializes
**Then** no API keys or secrets are logged to the console or displayed in the UI

---

### Story 1.2: OpenAPI/Swagger File Upload & Parsing

As a developer,
I want to upload an OpenAPI/Swagger JSON or YAML file,
So that the system automatically extracts all endpoints, methods, parameters, schemas, and auth requirements without manual input.

**Acceptance Criteria:**

**Given** the app is on the Spec Ingestion stage
**When** the developer uploads a valid OpenAPI 3.0 JSON file
**Then** the system parses it and populates `SataState` with all discovered endpoints, HTTP methods, path/query/body parameters, request/response schemas, and auth requirements

**Given** the developer uploads a valid OpenAPI 3.0 YAML file
**When** parsing completes
**Then** the same fields are extracted as with a JSON file

**Given** the developer uploads a malformed or non-OpenAPI file
**When** parsing fails
**Then** a clear error message is displayed explaining the issue
**And** the user is prompted to upload a different file without crashing the app

**Given** a spec is successfully parsed
**When** extraction completes
**Then** a summary count of discovered endpoints is shown to the user (e.g., "Found 12 endpoints")
**And** the pipeline advances to the next node

---

### Story 1.3: API Spec URL Import

As a developer,
I want to provide a URL pointing to a public OpenAPI spec,
So that the system fetches and parses it without requiring me to download the file manually.

**Acceptance Criteria:**

**Given** the developer enters a valid URL to a publicly accessible OpenAPI 3.0 JSON or YAML spec
**When** they submit the URL
**Then** the system fetches the spec and passes it through the same parser as Story 1.2
**And** `SataState` is populated identically to a file upload

**Given** the entered URL is unreachable or returns a non-200 response
**When** the fetch fails
**Then** a clear error message is displayed (e.g., "Could not reach URL — check the address or your connection")
**And** the user can retry with a different URL without restarting the app

**Given** the URL returns a non-OpenAPI document (e.g., an HTML page)
**When** parsing fails
**Then** the system displays a specific error distinguishing a fetch failure from a parse failure

---

### Story 1.4: Spec Gap Detection & Targeted Questions

As a developer,
I want the system to detect incomplete or ambiguous fields in my parsed spec and ask me targeted questions to fill them,
So that the test suite is based on complete, accurate API information rather than guesses.

**Acceptance Criteria:**

**Given** a spec has been parsed and `SataState` is populated
**When** the gap detection node runs
**Then** the system identifies fields that are missing, ambiguous, or under-specified (e.g., missing response schemas, unclear auth type, undocumented error codes)

**Given** gaps are detected
**When** the system presents them to the user
**Then** each gap is shown as a specific, targeted question (e.g., "Endpoint POST /users has no defined success response schema — what does a 201 response return?")
**And** questions are grouped by endpoint for clarity

**Given** the user answers a gap question
**When** the answer is accepted
**Then** `SataState` is updated with the user-provided information
**And** the filled gap is no longer flagged

**Given** no gaps are detected
**When** gap detection completes
**Then** the system skips the question step and advances the pipeline automatically

---

### Story 1.5: Conversational API Description & Zero-Endpoint Fallback

As a developer,
I want to describe my API endpoints through conversational chat — either by choice or when my uploaded spec contains zero parseable endpoints —
So that I can still build a complete test suite even without a formal spec file.

**Acceptance Criteria:**

**Given** the developer selects "Describe my API manually" instead of uploading a file or URL
**When** the conversational ingestion node activates
**Then** a chat interface is presented with a prompt explaining what information is needed (endpoint paths, methods, expected inputs/outputs)

**Given** the developer's uploaded spec parses successfully but contains zero endpoints
**When** the pipeline reaches the endpoint extraction node
**Then** the system automatically switches to conversational mode
**And** displays a clear fallback message: "No endpoints were found in your spec. Let's describe them together."

**Given** the developer provides endpoint descriptions through chat
**When** the LLM processes the conversation
**Then** `SataState` is populated with the extracted API model in the same structure as file/URL parsing
**And** the pipeline advances to Spec Review

**Given** the developer provides ambiguous or incomplete descriptions
**When** the LLM detects missing required information
**Then** it asks follow-up questions until sufficient detail is captured to generate test cases

---

## Epic 2: Spec Review & Human Checkpoint

Users can view all discovered endpoints and fields, edit or remove entries, and explicitly confirm or reject the spec at a human checkpoint before any tests are generated.

### Story 2.1: Spec Review Panel — Endpoint Table Display

As a developer,
I want to see all parsed API endpoints and their fields presented in a structured, readable panel,
So that I can verify the system understood my spec correctly before any tests are generated.

**Acceptance Criteria:**

**Given** spec ingestion and gap-filling are complete and `SataState` contains the parsed API model
**When** the pipeline advances to the Spec Review stage
**Then** the stage header updates to "Spec Review" (UX-DR1)
**And** a "Next required action" area displays: "Review your API spec below — confirm to proceed or reject to re-parse" (UX-DR2)

**Given** the spec review panel is displayed
**When** the developer views it
**Then** all discovered endpoints are listed with: path, HTTP method, parameters (name, type, required flag), request body schema, expected response schema, and auth requirements
**And** the layout uses a structured table or expandable rows — not raw JSON

**Given** the spec contains 0 endpoints at this stage (edge case bypass)
**When** the review panel would render
**Then** the system shows an empty-state message and routes back to ingestion (UX-DR8)

---

### Story 2.2: Spec Editing — Modify, Add & Remove Endpoints and Fields

As a developer,
I want to edit the parsed spec directly in the review panel — modifying field values, adding missing endpoints, or removing incorrect ones —
So that I can correct parser errors or fill in details before committing to test generation.

**Acceptance Criteria:**

**Given** the spec review panel is displayed
**When** the developer clicks to edit a field (e.g., a parameter type or response schema)
**Then** the field becomes editable inline
**And** changes are immediately reflected in `SataState` on save

**Given** the developer wants to add a new endpoint
**When** they use the "Add endpoint" action
**Then** a form appears requesting: path, method, parameters, and optional schema fields
**And** the new endpoint is appended to the spec in `SataState`

**Given** the developer wants to remove an endpoint
**When** they trigger the remove action on an endpoint row
**Then** the endpoint is removed from the display and from `SataState`
**And** no other endpoints are affected

**Given** the developer makes edits and then navigates away or refreshes
**When** they return to the review panel
**Then** their edits are preserved in `SataState` (not lost on re-render)

---

### Story 2.3: Spec Confirmation & Rejection Checkpoint

As a developer,
I want to explicitly confirm or reject the spec at a human checkpoint,
So that no tests are ever generated against a spec I haven't approved.

**Acceptance Criteria:**

**Given** the spec review panel is visible with at least one endpoint
**When** the developer reviews the spec
**Then** explicit "Confirm Spec" and "Reject & Re-parse" buttons are visible (UX-DR3)
**And** neither action triggers automatically — the pipeline is paused until the user acts

**Given** the developer clicks "Confirm Spec"
**When** confirmation is processed
**Then** `SataState` marks the spec as confirmed
**And** the pipeline advances to Test Plan Generation
**And** the confirmed spec can no longer be edited without rejecting first

**Given** the developer clicks "Reject & Re-parse"
**When** rejection is processed
**Then** the stage header and next-action area clearly state which step the user is returning to and why (e.g., "Returning to Spec Ingestion — your previous input is preserved for editing") (UX-DR6)
**And** the pipeline routes back to ingestion with the previous input pre-populated

**Given** the spec contains auth configuration (Bearer token or API key)
**When** displaying the confirmation panel
**Then** the auth details are shown in a dedicated, clearly labelled section
**And** a safety notice warns: "These credentials will be sent only to your target API — never to the LLM" (UX-DR9)

---

## Epic 3: Test Plan Generation & Configuration

Users can generate a prioritized, categorized test plan, configure which categories run, review destructive-operation warnings, and confirm or reject the plan before execution.

### Story 3.1: Test Case Generation — Categories & Priorities

As a developer,
I want the system to automatically generate a comprehensive set of test cases across multiple defect categories with assigned priorities,
So that I have thorough coverage without manually designing each test.

**Acceptance Criteria:**

**Given** the spec has been confirmed and `SataState` contains the confirmed API model
**When** the test generation node runs
**Then** test cases are generated across all applicable defect categories: happy path, missing data, invalid format, wrong type, auth failure, boundary, duplicate, and method not allowed
**And** each test case is assigned a priority: P1 (critical), P2 (important), or P3 (nice to have)

**Given** test cases are generated
**When** the generation node validates them
**Then** every test case references only endpoints and fields present in the confirmed spec (FR35)
**And** any test case referencing a non-existent endpoint is discarded before display

**Given** an endpoint has no auth requirements in the spec
**When** test cases are generated for it
**Then** no auth failure test cases are generated for that endpoint

**Given** the LLM returns an error or times out during generation
**When** the failure occurs
**Then** the system retries once and displays a helpful message on second failure
**And** partial results already generated are preserved in `SataState`

---

### Story 3.2: Test Plan Review — Category Toggles & Destructive Warnings

As a developer,
I want to see all generated test cases grouped by category with priority labels, toggle categories on or off, and see destructive-operation warnings surfaced directly next to relevant tests,
So that I can configure exactly what runs without scrolling through a flat list or missing dangerous operations.

**Acceptance Criteria:**

**Given** test generation is complete
**When** the test plan review panel is displayed
**Then** the stage header updates to "Test Plan Review"
**And** test cases are grouped by defect category (e.g., Happy Path, Auth Failure, Boundary)
**And** each category section shows P1/P2/P3 counts and a toggle to enable or disable the entire category

**Given** a category toggle is switched off
**When** the user views the plan
**Then** all tests in that category are visually marked as excluded
**And** the excluded tests are removed from `SataState`'s execution plan

**Given** the test plan includes DELETE or PUT test cases
**When** those tests are displayed
**Then** a destructive-operation warning is shown directly next to each affected test (e.g., "⚠ This test will DELETE data")
**And** the warning is visible without requiring the user to expand or hover

**Given** the developer re-enables a previously disabled category
**When** the toggle is turned back on
**Then** those tests are restored to the execution plan in `SataState`

---

### Story 3.3: Test Plan Confirmation & Rejection Checkpoint

As a developer,
I want to explicitly confirm the test plan or reject it to regenerate,
So that no tests execute until I've reviewed and acknowledged everything — including any destructive operations.

**Acceptance Criteria:**

**Given** the test plan review panel is visible
**When** the developer has reviewed the plan
**Then** explicit "Confirm Test Plan" and "Reject & Regenerate" buttons are visible
**And** neither action triggers automatically

**Given** the test plan contains destructive operations (DELETE/PUT tests) that have not been acknowledged
**When** the developer clicks "Confirm Test Plan"
**Then** a blocking acknowledgement prompt appears listing all destructive tests by endpoint
**And** the pipeline does not advance until the developer explicitly confirms they understand the risk

**Given** all destructive tests are acknowledged and the developer confirms
**When** confirmation is processed
**Then** `SataState` marks the test plan as confirmed with the final enabled test set
**And** the pipeline advances to Test Execution

**Given** the developer clicks "Reject & Regenerate"
**When** rejection is processed
**Then** a clear message states which stage they are returning to (e.g., "Regenerating test plan from your confirmed spec")
**And** the pipeline routes back to test generation
**And** the developer can optionally provide feedback on what to change before regenerating

---

## Epic 4: Test Execution & Analysis

Users can execute the confirmed test plan against their target API, monitor progress, and receive intelligent analysis with developer-friendly failure explanations and smart diagnosis when all tests fail.

### Story 4.1: HTTP Test Execution with Auth & Retry

As a developer,
I want the system to execute all confirmed test cases as real HTTP requests against my target API, with proper auth handling, retry logic, and visible progress,
So that I get accurate results without managing the execution loop manually.

**Acceptance Criteria:**

**Given** the test plan is confirmed and execution begins
**When** the execution node runs
**Then** the stage header updates to "Running"
**And** a progress indicator shows how many tests have completed vs. total (e.g., "14 / 38 tests run")
**And** the Streamlit UI remains responsive — it does not freeze during execution

**Given** a test case requires Bearer token authentication
**When** the HTTP request is built
**Then** the token is included in the `Authorization` header
**And** the token is never sent to the LLM or written to any log or UI element

**Given** a test case requires API key authentication
**When** the HTTP request is built
**Then** the key is included in the correct header or query param as defined in the spec
**And** the key is never sent to the LLM or written to any log or UI element

**Given** a test case HTTP request fails (network error or non-retryable error)
**When** the first attempt fails
**Then** the system retries once before marking the test as failed
**And** the failure reason is stored in `SataState` for analysis

**Given** the target API is completely unreachable
**When** the first test attempts to connect
**Then** execution halts with a clear error: "Target API is unreachable — check the URL and your connection"
**And** the user is offered the option to retry or abort

**Given** a pipeline node runs more iterations than the configured maximum
**When** the counter limit is hit
**Then** execution stops for that node and `SataState` records the timeout
**And** the user receives a message explaining why execution stopped early

**Given** individual test cases execute
**When** each completes
**Then** it finishes within 30 seconds including API response wait
**And** a full 15-endpoint API pipeline completes within 10 minutes

---

### Story 4.2: Response Validation & Pass/Fail Detection

As a developer,
I want each test case's response to be automatically validated against the expected schema and status code,
So that I get precise pass/fail results rather than just raw HTTP responses.

**Acceptance Criteria:**

**Given** an HTTP response is received for a test case
**When** validation runs
**Then** the actual status code is compared to the expected status code defined in the spec
**And** the response body structure is compared to the expected response schema

**Given** the actual status code and response structure both match expectations
**When** validation completes
**Then** the test case is marked as **Pass** in `SataState`

**Given** the actual status code differs from expected, or the response body fails schema validation
**When** validation completes
**Then** the test case is marked as **Fail** in `SataState`
**And** both the expected and actual values are stored for display in the results

**Given** the API returns a valid response but with an unexpected extra field
**When** validation runs
**Then** the test passes (non-strict schema matching — extra fields are allowed unless spec explicitly forbids them)

**Given** the API returns no response body for a test case that expects one
**When** validation runs
**Then** the test is marked as **Fail** with reason "Empty response body — expected schema not satisfied"

---

### Story 4.3: Failure Analysis & Developer-Friendly Explanations

As a developer,
I want each test failure to be analyzed for defect patterns and presented with a plain-language explanation of what broke, why it matters, and how to fix it,
So that I can act on results immediately without interpreting raw request/response diffs myself.

**Acceptance Criteria:**

**Given** test execution is complete and failures exist in `SataState`
**When** the analysis node runs
**Then** failures are grouped by defect type and severity (e.g., "3× Missing Required Field — High")

**Given** a test case has failed
**When** the analysis node processes it
**Then** a developer-friendly explanation is generated containing: what broke, why it matters, and a concrete suggestion for how to fix it
**And** the explanation is stored in `SataState` alongside the test case result

**Given** multiple failures share the same root cause pattern (e.g., auth fails on all POST endpoints)
**When** pattern analysis runs
**Then** the pattern is surfaced as a single grouped finding rather than N identical explanations

**Given** a failure analysis explanation is generated
**When** it is stored
**Then** no auth tokens, API keys, or sensitive request data are included in the explanation text

---

### Story 4.4: Smart Diagnosis — All-Pass Suggestions & All-Fail Detection

As a developer,
I want the system to detect when all tests pass (suggesting deeper coverage) or when all tests fail (diagnosing a systemic issue),
So that I always receive actionable next steps rather than a bare result count.

**Acceptance Criteria:**

**Given** execution completes and all enabled test cases pass
**When** the analysis node processes the results
**Then** the system generates suggestions for deeper testing areas (e.g., "All happy path tests passed — consider adding rate limit or pagination edge cases")
**And** the suggestions are displayed prominently in the results view

**Given** execution completes and all enabled test cases fail
**When** the analysis node processes the results
**Then** the system runs smart diagnosis to identify likely systemic causes
**And** presents the most probable diagnosis from: auth misconfiguration, wrong base URL, API is down, or all endpoints require a setup step not yet performed

**Given** smart diagnosis identifies auth misconfiguration as the likely cause
**When** the diagnosis is displayed
**Then** the message includes the specific auth field from the spec and a suggestion to verify the token/key value

**Given** smart diagnosis identifies the target API as unreachable
**When** the diagnosis is displayed
**Then** the message is distinct from a per-test network error and suggests checking the base URL in `.env`

---

## Epic 5: Results Dashboard, Reporting & Iteration

Users can explore results through a drill-down dashboard with pass/fail metrics, generate a summary report, request deeper analysis, and trigger re-test loops after fixing issues.

### Story 5.1: Results Dashboard — Pass/Fail Metrics & Defect Heatmap

As a developer,
I want a high-level results dashboard showing pass/fail metrics, a defect heatmap, and category summaries,
So that I can triage the overall health of my API at a glance without reading every test result individually.

**Acceptance Criteria:**

**Given** test execution and analysis are complete
**When** the results dashboard is displayed
**Then** the stage header updates to "Results Review"
**And** the dashboard shows: total tests run, pass count, fail count, and pass rate percentage

**Given** the dashboard is rendered
**When** the developer views the defect summary
**Then** failures are grouped by defect category with counts (e.g., "Auth Failure: 4", "Missing Data: 2")
**And** a heatmap or visual indicator highlights which endpoints have the most failures

**Given** the dashboard is rendered
**When** the developer views the priority breakdown
**Then** P1, P2, and P3 failures are shown separately so critical issues are immediately visible

**Given** all tests passed
**When** the dashboard renders
**Then** a clear success state is displayed alongside the deeper testing suggestions from Story 4.4

---

### Story 5.2: Failure Drill-Down — Request, Response & Explanation View

As a developer,
I want to click into any failing test case and see the full request that was sent, the response that came back, and the plain-language explanation of what went wrong,
So that I have everything I need to reproduce and fix the issue without leaving the tool.

**Acceptance Criteria:**

**Given** the results dashboard is displayed with one or more failures
**When** the developer clicks on a failing test case
**Then** a detail view opens showing: the exact HTTP request (method, URL, headers minus sensitive tokens, body), the actual response (status code, headers, body), and the developer-friendly explanation generated in Story 4.3

**Given** the detail view is open
**When** the developer views the request headers
**Then** auth tokens and API keys are redacted (e.g., `Authorization: Bearer ***`) — never shown in full

**Given** the developer is viewing a failure detail
**When** they want to return to the dashboard
**Then** a back navigation is available and the dashboard state is preserved (scroll position, filters)

**Given** a test case passed
**When** the developer clicks on it
**Then** the detail view shows the request and response but no failure explanation — instead shows "Test passed — response matched expected schema and status code"

---

### Story 5.3: Results Report Generation

As a developer,
I want to generate a structured results report from the completed test run,
So that I can share findings with my team or keep a record of the API quality at a point in time.

**Acceptance Criteria:**

**Given** test execution and analysis are complete
**When** the developer requests a report
**Then** a report is generated containing: run summary (date, target API, total tests, pass/fail counts), per-category breakdown, all failures with their explanations, and any smart diagnosis or deeper testing suggestions

**Given** the report is generated
**When** the developer views or downloads it
**Then** the report is in a readable format (Markdown or plain text)
**And** no auth tokens, API keys, or sensitive values are included in the report

**Given** a report has been generated
**When** the developer triggers report generation again on the same run
**Then** the previous report is overwritten or timestamped to avoid confusion

---

### Story 5.4: Deeper Analysis, Re-test Loop & Iteration

As a developer,
I want to request deeper analysis on specific failing areas or trigger a full re-test after I've made fixes,
So that I can iterate quickly without restarting the entire pipeline from scratch.

**Acceptance Criteria:**

**Given** the results dashboard is visible
**When** the developer selects one or more endpoints or categories and requests deeper analysis
**Then** the pipeline re-runs test generation and execution scoped to the selected subset
**And** new results are merged into `SataState` alongside the original run

**Given** the developer has fixed issues in their API and wants to re-test
**When** they trigger the re-test loop
**Then** the pipeline re-executes the full confirmed test plan against the target API without requiring spec re-ingestion
**And** the new results replace the previous run in `SataState` and the dashboard refreshes

**Given** a re-test is triggered
**When** execution begins
**Then** the same progress indicators from Story 4.1 are shown
**And** the stage header clearly indicates this is a re-test run (e.g., "Re-running — Attempt 2")

**Given** the re-test completes
**When** results are displayed
**Then** a comparison indicator shows improvement or regression vs. the previous run (e.g., "↑ 3 tests now passing")

---

## Epic 6: Pipeline Observability & Demo Mode

Users and developers can inspect agent reasoning logs, visualize the full LangGraph pipeline as a diagram, and run end-to-end guided demos on pre-loaded sample APIs (PetStore, ReqRes, JSONPlaceholder).

### Story 6.1: Agent Reasoning Logs — Tool Selection Transparency

As a developer,
I want to view the agent's reasoning logs showing which tools were selected and why at each pipeline step,
So that I can understand and trust the agent's decision-making and debug unexpected behaviour.

**Acceptance Criteria:**

**Given** the pipeline has completed at least one stage
**When** the developer opens the reasoning log view
**Then** each tool call is shown with: the tool name, the agent's stated reason for selecting it, and the input passed to it

**Given** a tool call involves auth tokens or API keys
**When** the log entry is rendered
**Then** all sensitive values are redacted (e.g., `token=***`) and never shown in full

**Given** multiple pipeline stages have completed
**When** the developer views the full log
**Then** entries are organized by pipeline stage so they can trace the reasoning across the full run

**Given** the LLM produces a reasoning step with no tool call (pure reasoning/planning)
**When** it is logged
**Then** it is shown as a reasoning step distinct from tool call entries

---

### Story 6.2: LangGraph Pipeline Visualization

As a developer,
I want to view the LangGraph pipeline as a visual graph diagram,
So that I can understand the full flow, conditional routing paths, and which node is currently active.

**Acceptance Criteria:**

**Given** the app is running
**When** the developer navigates to the pipeline visualization view
**Then** all 8+ pipeline nodes are displayed as a directed graph with labelled edges showing routing conditions

**Given** the pipeline is mid-execution
**When** the graph is displayed
**Then** the currently active node is visually highlighted
**And** completed nodes are marked as done

**Given** the pipeline has taken a conditional branch (e.g., rejection path, fallback to conversational mode)
**When** the graph is displayed after the run
**Then** the path actually taken is visually distinguished from paths not taken

**Given** the developer views the graph
**When** they hover or click on a node
**Then** a tooltip or panel shows the node's name and its role in the pipeline

---

### Story 6.3: Demo Mode — Sample APIs & Guided End-to-End Flow

As a developer or evaluator,
I want to select a pre-loaded sample API and run a fully guided end-to-end demo flow,
So that I can see the complete tool in action without needing my own API or spec file.

**Acceptance Criteria:**

**Given** the app is on the Spec Ingestion stage
**When** the developer selects "Demo Mode"
**Then** three sample APIs are available for selection: PetStore, ReqRes, and JSONPlaceholder
**And** selecting one pre-populates `SataState` with the bundled spec — no file upload or URL required

**Given** a sample API is selected and demo mode begins
**When** the guided flow runs
**Then** the pipeline proceeds through all stages automatically with pre-configured inputs
**And** the developer can still interact at each human checkpoint (confirm/reject) — the demo does not skip human gates

**Given** demo mode is running
**When** test execution reaches the sample API
**Then** the HTTP requests are made against the real public API endpoint (PetStore, ReqRes, or JSONPlaceholder)
**And** real results are returned — not mocked

**Given** the demo completes
**When** the results dashboard is shown
**Then** the experience is identical to a real run — the developer sees a genuine pass/fail report they can drill into

