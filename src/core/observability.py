"""Shared observability helpers for reasoning and tool-call logs."""

from __future__ import annotations

from datetime import datetime, timezone

from src.tools.redaction import sanitize_value


def append_reasoning_log(
    state: dict,
    *,
    stage: str,
    event_type: str,
    reason: str,
    tool_name: str | None = None,
    input_summary: object | None = None,
    details: object | None = None,
) -> dict:
    """Append a sanitized reasoning/tool-call event to shared state."""
    events = list(state.get("reasoning_log") or [])
    events.append(
        {
            "order": len(events) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "event_type": event_type,
            "tool_name": tool_name,
            "reason": reason,
            "input_summary": sanitize_value(input_summary),
            "details": sanitize_value(details),
        }
    )
    state["reasoning_log"] = events
    return state
