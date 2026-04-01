# Sata

**AI agent for automated API testing and test-result analysis.**

Sata ingests API documentation or user-provided input, plans and runs API tests, compares responses to expectations, surfaces common API defects, and presents results in a clear dashboard—so teams spend less time on repetitive manual checks and get faster feedback when something breaks.

---

## Agent

| | |
| --- | --- |
| **Name (VN)** | AI Agent tự động kiểm thử API & phân tích kết quả test |
| **Role** | End-to-end assistant: from spec → test cases → execution → report |

---

## Features

### Specification & test design

- Parses API docs or free-form user input to infer **endpoints**, **HTTP methods**, **parameters**, **request bodies**, and **critical test conditions**.
- **Generates test suites** automatically, including:
  - Happy paths (valid requests)
  - Missing or incomplete data
  - Invalid formats and wrong data types
  - Authentication / authorization failures
  - Boundary and edge cases

### Execution & assertion

- **Sends HTTP requests** for each case and evaluates responses against:
  - **Status codes**
  - **Response shape** (schema / structure)
  - **Payload content** and **expected business rules**

### Analysis & defect detection

- Highlights typical API problems, for example:
  - Validation that is too loose or inconsistent
  - Responses that do not match the documented structure
  - Poor or inconsistent exception handling
  - Error messages that vary unpredictably across similar failures

### Reporting

- Aggregates run results into an **interactive UI** (e.g. **Streamlit** or **Gradio**) so you can see **pass/fail** per case, **logs**, and **likely root causes** at a glance.

### Outcomes

- Cuts down **manual regression** effort
- Improves **test coverage** for APIs
- Helps **developers and testers debug** failures faster

---

## Architecture

Source code structure, dependency rules, and migration plan are documented in [`docs/source-architecture.md`](./docs/source-architecture.md).

## Repository

Git workflow, branches, commits, and PR rules for this project are documented in [`GIT_CONVENTION.md`](./GIT_CONVENTION.md).

---

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   Copy `.env.example` to `.env` and fill in the required variables:
   - `LLM_API_KEY`
   - `LLM_CHAT_MODEL`
   - `LLM_BASE_URL`

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```
