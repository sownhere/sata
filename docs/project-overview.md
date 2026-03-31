# Project Overview: Sata AI API Tester

Sata is a Streamlit-based web application leveraging LangGraph orchestration and LangChain to automate the ingestion, gap detection, and execution of test plans for OpenAPI/Swagger contracts.

## Executive Summary

Sata addresses API schema deficiencies by securely processing documentation across various upload formats, dynamically identifying configuration or specification gaps, and querying the engineer with actionable clarifications via the Streamlit UI. Afterward, it stages end-to-end tests based directly on definitive endpoint operations, ensuring resilience against API hallucination.

## Tech Stack Summary

| Category                | Technology                                      | Version    | Justification                           |
|-------------------------|-------------------------------------------------|------------|-----------------------------------------|
| **Primary Language**    | Python                                          | 3.12+      | Native support for LangGraph & Streamlit|
| **UI Framework**        | Streamlit                                       | >= 1.32.0  | Efficient, reactive UI                  |
| **Orchestration**       | LangGraph, LangChain, langchain-openai          | >= 0.1.0   | Robust node pipeline handling           |
| **Data & Spec Parsing** | Pydantic, PyYAML, openapi-spec-validator        | >= 6.0.0   | Schema parsing and validation           |
| **Testing Core**        | Pytest, Pytest-mock                             | >= 8.0.0   | Deterministic function verification     |

## Architecture Classification

- **Type**: Backend Orchestration pipeline coupled with Streamlit Presentation
- **Structure**: Monolith (Single cohesive codebase bridging frontend UI and AI backend orchestrators)
