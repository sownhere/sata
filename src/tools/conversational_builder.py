"""LLM-backed conversational extraction for manual API descriptions.

Canonical location: src.tools.conversational_builder
(Migrated from app/utils/conversational_spec_builder.py.)
Prompts externalized to src/prompts/ in Story 7.4.
"""

import json
import os

from src.core.prompts import load_prompt

EXPECTED_TOP_LEVEL_KEYS = {"endpoints", "auth", "title", "version"}
EXPECTED_ENDPOINT_KEYS = {
    "path",
    "method",
    "operation_id",
    "summary",
    "parameters",
    "request_body",
    "response_schemas",
    "auth_required",
    "tags",
}
EXPECTED_AUTH_KEYS = {"type", "scheme", "in", "name"}


def extract_api_model_from_conversation(
    messages: list[dict],
    llm=None,
) -> dict:
    """Return either a follow-up question or a canonical API model."""
    if not messages:
        raise ValueError(
            "Provide at least one conversational message before extraction."
        )

    active_llm = llm or _build_llm()
    response = active_llm.invoke(_build_prompt(messages))
    payload = _load_json_payload(_response_text(response))

    status = payload.get("status")
    if status == "needs_more_info":
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                "Conversation extraction must return a follow-up question."
            )
        return {"status": "needs_more_info", "question": question.strip()}

    if status != "complete":
        raise ValueError(
            "Conversation extraction must return status"
            " 'complete' or 'needs_more_info'."
        )

    api_model = payload.get("api_model")
    _validate_api_model(api_model)
    return {"status": "complete", "api_model": _normalize_api_model(api_model)}


def _build_llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_CHAT_MODEL"],
        base_url=os.environ["LLM_BASE_URL"],
        temperature=0,
    )


def _build_prompt(messages: list[dict]) -> list[dict]:
    transcript_lines = []
    for message in messages:
        role = str(message.get("role", "user")).strip().lower() or "user"
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        transcript_lines.append(f"{role.upper()}: {content}")
    transcript = "\n".join(transcript_lines)
    system_prompt = load_prompt("conversational_extraction")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{transcript}"},
    ]


def _response_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    raise ValueError("Conversation extraction did not return text content.")


def _load_json_payload(text: str) -> dict:
    stripped = text.strip()
    # Strip markdown code fences if present
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first line (```json or ```) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        stripped = "\n".join(lines)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("Conversation extraction must return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Conversation extraction must return a JSON object.")
    return payload


def _validate_api_model(api_model) -> None:
    if not isinstance(api_model, dict):
        raise ValueError("Conversation extraction must return an api_model object.")
    if not EXPECTED_TOP_LEVEL_KEYS.issubset(set(api_model.keys())):
        raise ValueError("Conversation extraction returned an invalid API model shape.")

    endpoints = api_model.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        raise ValueError("Conversation extraction must return at least one endpoint.")

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise ValueError(
                "Conversation extraction returned an invalid endpoint record."
            )
        if not EXPECTED_ENDPOINT_KEYS.issubset(set(endpoint.keys())):
            raise ValueError(
                "Conversation extraction returned an invalid endpoint shape."
            )
        if not isinstance(endpoint.get("path"), str) or not endpoint["path"].strip():
            raise ValueError("Each extracted endpoint must include a path.")
        if (
            not isinstance(endpoint.get("method"), str)
            or not endpoint["method"].strip()
        ):
            raise ValueError("Each extracted endpoint must include a method.")
        if not isinstance(endpoint.get("parameters"), list):
            raise ValueError("Each extracted endpoint must include a parameters list.")
        if not isinstance(endpoint.get("response_schemas"), dict):
            raise ValueError(
                "Each extracted endpoint must include a response_schemas dict."
            )
        if not isinstance(endpoint.get("tags"), list):
            raise ValueError("Each extracted endpoint must include a tags list.")
        if not isinstance(endpoint.get("auth_required"), bool):
            raise ValueError(
                "Each extracted endpoint must include auth_required as a boolean."
            )

    auth = api_model.get("auth")
    if not isinstance(auth, dict) or not EXPECTED_AUTH_KEYS.issubset(set(auth.keys())):
        raise ValueError("Conversation extraction returned an invalid auth shape.")
    if not isinstance(api_model.get("title"), str) or not api_model["title"].strip():
        raise ValueError("Conversation extraction must include an API title.")
    if (
        not isinstance(api_model.get("version"), str)
        or not api_model["version"].strip()
    ):
        raise ValueError("Conversation extraction must include an API version.")


def _normalize_api_model(api_model: dict) -> dict:
    normalized = {
        "endpoints": [],
        "auth": dict(api_model["auth"]),
        "title": api_model["title"].strip(),
        "version": api_model["version"].strip(),
    }

    for endpoint in api_model["endpoints"]:
        normalized["endpoints"].append(
            {
                "path": endpoint["path"].strip(),
                "method": endpoint["method"].strip().upper(),
                "operation_id": endpoint.get("operation_id"),
                "summary": endpoint.get("summary"),
                "parameters": list(endpoint.get("parameters") or []),
                "request_body": endpoint.get("request_body"),
                "response_schemas": {
                    str(status): schema
                    for status, schema in endpoint.get("response_schemas", {}).items()
                },
                "auth_required": endpoint["auth_required"],
                "tags": list(endpoint.get("tags") or []),
            }
        )

    return normalized
