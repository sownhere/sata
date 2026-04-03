"""Sata — AI-Powered API Test Agent.

Entry point: streamlit run app.py

Startup sequence:
1. Validate required environment variables (halt with error if missing).
2. Initialise SataState in session_state.
3. Build LangGraph pipeline.
4. Render persistent stage header (UX-DR1).
"""

from collections import defaultdict

import streamlit as st

from app.pipeline import (
    build_pipeline,
    record_route_transition,
    reset_visualization_trace,
    run_pipeline_node,
)
from app.state import initial_state
from app.utils.env import load_env, validate_env
from app.utils.spec_fetcher import fetch_spec_from_url
from src.core.prompts import load_prompt as _load_prompt
from src.ui.components import (
    format_gap_answer,
    has_ui_answer,
    render_gap_input,
    render_pipeline_visualization,
)

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sata — AI API Tester",
    page_icon="🔬",
    layout="wide",
)

# ── Environment validation (AC: 3, 4 / NFR6-NFR8) ─────────────────────────
load_env()
missing = validate_env()
if missing:
    st.error(
        f"Missing required environment variables: {', '.join(missing)}\n\n"
        "Copy `.env.example` to `.env` and fill in your values, then restart the app."
    )
    st.stop()

# ── Session state initialisation ───────────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = initial_state()

if "pipeline" not in st.session_state:
    st.session_state.pipeline = build_pipeline()

if "conversation_messages" not in st.session_state:
    st.session_state.conversation_messages = []

if "conversation_banner" not in st.session_state:
    st.session_state.conversation_banner = None

# ── Persistent stage header (UX-DR1) ──────────────────────────────────────
stage = str(st.session_state.state.get("pipeline_stage") or "initial")
stage_label = stage.replace("_", " ").title()

st.title("Sata — AI API Tester")
st.subheader(f"Stage: {stage_label}")
st.divider()

_conversation_starter = _load_prompt("conversation_starter").split("---", 1)
CONVERSATION_PROMPT = _conversation_starter[0].strip()
ZERO_ENDPOINT_FALLBACK_MESSAGE = (
    _conversation_starter[1].strip() if len(_conversation_starter) > 1 else ""
)


def _conversation_mode_active(current_state) -> bool:
    if current_state.get("spec_source") == "chat":
        return True
    model = current_state.get("parsed_api_model") or {}
    endpoints = model.get("endpoints")
    return bool(model) and isinstance(endpoints, list) and len(endpoints) == 0


def _append_assistant_message(message: str) -> None:
    if not message.strip():
        return
    history = st.session_state.conversation_messages
    if (
        history
        and history[-1]["role"] == "assistant"
        and history[-1]["content"] == message
    ):
        return
    history.append({"role": "assistant", "content": message})


def _reset_conversation_ui() -> None:
    st.session_state.conversation_messages = []
    st.session_state.conversation_banner = None
    if "state" in st.session_state:
        st.session_state.state["conversation_messages"] = None
        st.session_state.state["conversation_question"] = None


def _prime_ingestion_trace(current_state, spec_source: str):
    current_state = reset_visualization_trace(current_state)
    current_state["spec_source"] = spec_source
    current_state = run_pipeline_node(current_state, "ingest_spec")
    record_route_transition(current_state, "ingest_spec")
    return current_state


def _start_conversation_flow(current_state, banner: str = None):
    if not st.session_state.conversation_messages:
        st.session_state.conversation_messages = [
            {"role": "assistant", "content": CONVERSATION_PROMPT}
        ]
    st.session_state.conversation_banner = banner
    current_state["conversation_messages"] = list(
        st.session_state.conversation_messages
    )
    current_state["conversation_question"] = None
    current_state["detected_gaps"] = None
    current_state["gap_answers"] = None
    current_state["error_message"] = None
    current_state["pipeline_stage"] = "fill_gaps"
    current_state["active_node"] = "fill_gaps"
    if not current_state.get("selected_visual_node"):
        current_state["selected_visual_node"] = "fill_gaps"
    return current_state


def _finalize_parsed_state_after_ingestion(updated_state):
    model = updated_state.get("parsed_api_model")
    if not model:
        return updated_state

    next_node = record_route_transition(updated_state, "parse_spec")
    endpoints = model.get("endpoints") or []
    if len(endpoints) == 0:
        return _start_conversation_flow(updated_state, ZERO_ENDPOINT_FALLBACK_MESSAGE)

    _reset_conversation_ui()
    if next_node == "detect_gaps":
        updated_state = run_pipeline_node(updated_state, "detect_gaps")
        if not updated_state.get("error_message"):
            record_route_transition(updated_state, "detect_gaps")
        else:
            updated_state["active_node"] = "detect_gaps"
    return updated_state


# ── Stage-driven content rendering ────────────────────────────────────────
state = st.session_state.state
current_stage = state["pipeline_stage"]

if state.get("error_message"):
    st.error(state["error_message"])

render_pipeline_visualization(state)

if current_stage in ("spec_ingestion", "spec_parsed"):
    if not state.get("parsed_api_model"):
        st.info(
            "**Next:** Upload your OpenAPI/Swagger spec (JSON or YAML) "
            "or import one from a public URL to begin."
        )

    if st.button("Describe my API manually", use_container_width=False):
        _reset_conversation_ui()
        state["raw_spec"] = None
        state["parsed_api_model"] = None
        state = _prime_ingestion_trace(state, "chat")
        state = _start_conversation_flow(state)
        st.session_state.state = state
        st.rerun()

    st.markdown("### Import from URL")
    spec_url = st.text_input(
        "Public OpenAPI/Swagger URL",
        placeholder="https://example.com/openapi.json",
        help="Enter a public OpenAPI 3.0 JSON or YAML URL.",
    )
    if st.button("Fetch spec from URL", use_container_width=False):
        _reset_conversation_ui()
        state["error_message"] = None
        if not spec_url.strip():
            state["error_message"] = "Please enter a URL before fetching."
            st.session_state.state = state
            st.rerun()
        else:
            try:
                raw_spec = fetch_spec_from_url(spec_url)
            except ValueError as exc:
                state["error_message"] = f"Fetch error: {exc}"
                st.session_state.state = state
                st.rerun()
            else:
                state = _prime_ingestion_trace(state, "url")
                state["raw_spec"] = raw_spec
                updated_state = run_pipeline_node(state, "parse_spec")
                if updated_state.get("parsed_api_model"):
                    updated_state = _finalize_parsed_state_after_ingestion(
                        updated_state
                    )
                elif updated_state.get("error_message"):
                    updated_state["error_message"] = (
                        f"Parse error: {updated_state['error_message']}"
                    )
                st.session_state.state = updated_state
                st.rerun()

    st.markdown("### Upload file")
    uploaded_file = st.file_uploader(
        "Upload OpenAPI/Swagger spec",
        type=["json", "yaml", "yml"],
        help="Supports OpenAPI 3.0 in JSON or YAML format",
    )

    if uploaded_file is not None and not state.get("parsed_api_model"):
        _reset_conversation_ui()
        try:
            raw_spec = uploaded_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            state["error_message"] = (
                "Could not read file: unsupported encoding. "
                "Please save your spec as UTF-8 and try again."
            )
            st.session_state.state = state
            st.rerun()
        else:
            state = _prime_ingestion_trace(state, "file")
            state["raw_spec"] = raw_spec
            updated_state = run_pipeline_node(state, "parse_spec")
            if updated_state.get("parsed_api_model"):
                updated_state = _finalize_parsed_state_after_ingestion(updated_state)
            st.session_state.state = updated_state
            st.rerun()

    model = state.get("parsed_api_model")
    if model and current_stage == "spec_parsed":
        endpoint_count = len(model.get("endpoints", []))
        st.success(
            f"Found {endpoint_count} endpoint{'s' if endpoint_count != 1 else ''}  — "
            f"'{model.get('title', 'API')}'"
        )
        st.info(
            "**Next:** Proceed to gap detection (Story 1.4) or URL import (Story 1.3)."
        )

elif current_stage == "fill_gaps":
    if _conversation_mode_active(state):
        if st.session_state.conversation_banner:
            st.warning(st.session_state.conversation_banner)

        st.info(
            "**Next:** Describe your endpoints, methods, inputs, outputs, and auth. "
            "Sata will either build the API model or ask one follow-up question."
        )

        for message in st.session_state.conversation_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        user_message = st.chat_input(
            state.get("conversation_question")
            or "Describe an endpoint, request body, response, or auth requirement."
        )

        if user_message:
            st.session_state.conversation_messages.append(
                {"role": "user", "content": user_message}
            )
            state["conversation_messages"] = list(
                st.session_state.conversation_messages
            )
            updated_state = run_pipeline_node(state, "fill_gaps")

            if updated_state.get("conversation_question"):
                _append_assistant_message(updated_state["conversation_question"])
            elif updated_state.get("parsed_api_model"):
                st.session_state.conversation_banner = None
                _append_assistant_message(
                    "Thanks. I captured your API structure and prepared it for review."
                )
                updated_state["pipeline_stage"] = "review_spec"
                record_route_transition(
                    updated_state, "fill_gaps", target_override="review_spec"
                )

            st.session_state.state = updated_state
            st.rerun()
    else:
        st.info(
            "**Next:** Answer the clarification questions below so Sata can"
            " prepare the spec for review."
        )
        detected_gaps = state.get("detected_gaps") or []
        grouped_gaps = defaultdict(list)
        for gap in detected_gaps:
            grouped_gaps[gap["endpoint_key"]].append(gap)

        with st.form("gap-clarification-form"):
            updated_answers = dict(state.get("gap_answers") or {})

            for endpoint_key, endpoint_gaps in grouped_gaps.items():
                st.markdown(f"### {endpoint_key}")
                for gap in endpoint_gaps:
                    updated_answers[gap["id"]] = render_gap_input(
                        gap, updated_answers.get(gap["id"])
                    )

            submitted = st.form_submit_button("Apply clarification answers")

        if submitted:
            state["gap_answers"] = {
                gap_id: answer
                for gap_id, answer in updated_answers.items()
                if has_ui_answer(answer)
            }
            updated_state = run_pipeline_node(state, "fill_gaps")
            if not updated_state.get("error_message"):
                record_route_transition(updated_state, "fill_gaps")
            st.session_state.state = updated_state
            st.rerun()

elif current_stage == "review_spec":
    model = state.get("parsed_api_model") or {}
    endpoint_count = len(model.get("endpoints", []))
    plural = "s" if endpoint_count != 1 else ""
    st.success(
        f"Spec ready for review: found {endpoint_count} endpoint{plural}"
        f" for '{model.get('title', 'API')}'."
    )
    st.info(
        "**Next:** Story 2.1 will provide the full review panel."
        " This story completes the clarification checkpoint."
    )
    if state.get("gap_answers"):
        st.markdown("### Clarifications captured")
        for gap_id, answer in state["gap_answers"].items():
            st.write(f"- `{gap_id}`: {format_gap_answer(answer)}")
