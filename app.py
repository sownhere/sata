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
from app.utils.spec_editor import add_endpoint, remove_endpoint, update_endpoint_field
from app.utils.spec_fetcher import fetch_spec_from_url
from src.core.prompts import load_prompt as _load_prompt
from src.nodes.review_spec import prepare_rejection_for_reparse
from src.ui.components import (
    format_gap_answer,
    has_ui_answer,
    render_gap_input,
    render_pipeline_visualization,
)
from src.ui.spec_review import (
    build_auth_checkpoint_rows,
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    build_rejection_return_message,
    get_stage_display_label,
    should_show_auth_checkpoint,
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

if "ingestion_banner" not in st.session_state:
    st.session_state.ingestion_banner = None

if "spec_url_input" not in st.session_state:
    st.session_state.spec_url_input = ""

if "preserved_raw_spec_input" not in st.session_state:
    st.session_state.preserved_raw_spec_input = ""

if "spec_upload_nonce" not in st.session_state:
    st.session_state.spec_upload_nonce = 0

# ── Persistent stage header (UX-DR1) ──────────────────────────────────────
stage = str(st.session_state.state.get("pipeline_stage") or "initial")
stage_label = get_stage_display_label(stage)

st.title("Sata — AI API Tester")
st.subheader(f"Stage: {stage_label}")
st.divider()

_conversation_starter = _load_prompt("conversation_starter").split("---", 1)
CONVERSATION_PROMPT = _conversation_starter[0].strip()
ZERO_ENDPOINT_FALLBACK_MESSAGE = (
    _conversation_starter[1].strip()
    if len(_conversation_starter) > 1
    else "No endpoints were found in your spec. Let's describe them together."
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


def _clear_ingestion_banner() -> None:
    st.session_state.ingestion_banner = None


def _reset_file_uploader_state() -> None:
    # Rotating the widget key forces Streamlit to drop any previously selected file.
    st.session_state.spec_upload_nonce += 1


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

    _clear_ingestion_banner()
    endpoints = model.get("endpoints") or []
    if len(endpoints) == 0:
        # Zero-endpoint fallback — record the correct route before switching
        record_route_transition(
            updated_state, "parse_spec", target_override="fill_gaps"
        )
        return _start_conversation_flow(updated_state, ZERO_ENDPOINT_FALLBACK_MESSAGE)

    next_node = record_route_transition(updated_state, "parse_spec")
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
    if current_stage == "spec_ingestion" and st.session_state.ingestion_banner:
        st.info(st.session_state.ingestion_banner)

    if not state.get("parsed_api_model"):
        st.info(
            "**Next:** Upload your OpenAPI/Swagger spec (JSON or YAML) "
            "or import one from a public URL to begin."
        )

    has_saved_conversation = state.get("spec_source") == "chat" and bool(
        st.session_state.conversation_messages
    )
    manual_button_label = (
        "Resume API conversation"
        if has_saved_conversation
        else "Describe my API manually"
    )
    if st.button(manual_button_label, use_container_width=False):
        _clear_ingestion_banner()
        if not has_saved_conversation:
            _reset_conversation_ui()
        state["raw_spec"] = None
        state["parsed_api_model"] = None
        st.session_state.preserved_raw_spec_input = ""
        state = _prime_ingestion_trace(state, "chat")
        state = _start_conversation_flow(state)
        st.session_state.state = state
        st.rerun()

    if current_stage == "spec_ingestion" and state.get("raw_spec"):
        if not st.session_state.preserved_raw_spec_input:
            st.session_state.preserved_raw_spec_input = state["raw_spec"]

        st.markdown("### Reuse preserved spec source")
        st.caption(
            "Your previous source is preserved here so you can edit it before "
            "parsing again."
        )
        st.text_area(
            "Preserved spec content",
            key="preserved_raw_spec_input",
            height=220,
        )
        if st.button("Parse preserved spec source", use_container_width=False):
            preserved_raw_spec = st.session_state.preserved_raw_spec_input
            if not preserved_raw_spec.strip():
                st.error("Preserved spec content is empty.")
            else:
                _clear_ingestion_banner()
                preserved_source = (
                    state.get("spec_source")
                    if state.get("spec_source") in {"file", "url"}
                    else "file"
                )
                state = _prime_ingestion_trace(state, preserved_source)
                state["raw_spec"] = preserved_raw_spec
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

    st.markdown("### Import from URL")
    st.text_input(
        "Public OpenAPI/Swagger URL",
        key="spec_url_input",
        placeholder="https://example.com/openapi.json",
        help="Enter a public OpenAPI 3.0 JSON or YAML URL.",
    )
    if st.button("Fetch spec from URL", use_container_width=False):
        _reset_conversation_ui()
        state["error_message"] = None
        spec_url = str(st.session_state.spec_url_input or "")
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
                _clear_ingestion_banner()
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
        key=f"spec_upload_input_{st.session_state.spec_upload_nonce}",
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
            _clear_ingestion_banner()
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
    _HTTP_METHODS = (
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS",
    )
    model = state.get("parsed_api_model") or {}
    endpoints = model.get("endpoints") or []
    top_level_auth = model.get("auth") or {}
    endpoint_count = len(endpoints)
    plural = "s" if endpoint_count != 1 else ""
    st.info(
        "**Next required action:** Review your API spec below, then choose "
        "**Confirm Spec** to continue or **Reject & Re-parse** to return "
        "to Spec Ingestion."
    )

    st.markdown("### Checkpoint 1: Confirm or Reject Spec")
    confirm_col, reject_col = st.columns(2)
    confirm_clicked = confirm_col.button(
        "Confirm Spec",
        use_container_width=True,
        disabled=endpoint_count == 0,
    )
    reject_clicked = reject_col.button(
        "Reject & Re-parse",
        use_container_width=True,
        disabled=endpoint_count == 0,
    )

    if should_show_auth_checkpoint(model):
        st.markdown("#### Auth Configuration")
        auth_rows = build_auth_checkpoint_rows(top_level_auth)
        if auth_rows:
            st.dataframe(auth_rows, use_container_width=True)
        else:
            st.caption(
                "One or more endpoints require authentication, but detailed "
                "auth metadata is unavailable in the parsed model."
            )
        st.warning(
            "These credentials will be sent only to your target API - never to the LLM."
        )

    if confirm_clicked:
        _clear_ingestion_banner()
        state["spec_confirmed"] = True
        state["error_message"] = None
        record_route_transition(state, "review_spec", target_override="generate_tests")
        updated_state = run_pipeline_node(state, "generate_tests")
        st.session_state.state = updated_state
        st.rerun()

    if reject_clicked:
        st.session_state.ingestion_banner = build_rejection_return_message(
            state.get("spec_source")
        )
        _reset_file_uploader_state()
        if state.get("raw_spec"):
            st.session_state.preserved_raw_spec_input = state["raw_spec"]
        updated_state = prepare_rejection_for_reparse(state)
        record_route_transition(
            updated_state,
            "review_spec",
            target_override="ingest_spec",
        )
        updated_state = run_pipeline_node(updated_state, "ingest_spec")
        st.session_state.state = updated_state
        st.rerun()

    # API summary banner
    st.markdown(
        f"**{model.get('title', 'API')}** · v{model.get('version', 'unknown')}"
        f" · {endpoint_count} endpoint{plural}"
    )

    # AC2: endpoint summary table (read-only, above edit forms)
    rows = build_endpoint_summary_rows(model)
    if rows:
        st.dataframe(rows, use_container_width=True)
    elif endpoint_count == 0:
        st.info("No endpoints in this spec. Use **+ Add endpoint** below to add one.")

    # AC2: per-endpoint detail expanders + edit / remove (Story 2.2)
    for i, endpoint in enumerate(endpoints):
        if not isinstance(endpoint, dict):
            continue
        detail = build_endpoint_detail_view(endpoint, top_level_auth=top_level_auth)
        with st.expander(detail["heading"]):
            st.markdown(f"**Summary:** {detail['summary']}")
            st.markdown(f"**Operation ID:** {detail['operation_id']}")
            st.markdown(f"**Auth:** {detail['auth']}")
            st.markdown(f"**Tags:** {detail['tags']}")
            st.markdown(f"**Parameters** ({detail['parameter_summary']})")
            if detail["parameters"]:
                st.dataframe(detail["parameters"], use_container_width=True)
            st.markdown(f"**Request Body:** {detail['request_body_summary']}")
            if detail["responses"]:
                st.markdown("**Responses:**")
                st.dataframe(detail["responses"], use_container_width=True)
            else:
                st.markdown("**Responses:** No responses documented")

            if st.button(f"Remove endpoint {i}", key=f"btn_remove_{i}"):
                new_model = remove_endpoint(model, i)
                st.session_state.state["parsed_api_model"] = new_model
                st.rerun()

            _meth = str(endpoint.get("method") or "GET").upper()
            _meth_idx = _HTTP_METHODS.index(_meth) if _meth in _HTTP_METHODS else 0
            with st.form(f"form_edit_{i}"):
                st.markdown("##### Edit endpoint")
                edit_path = st.text_input(
                    "Path",
                    value=str(endpoint.get("path") or ""),
                )
                edit_method = st.selectbox(
                    "Method",
                    _HTTP_METHODS,
                    index=_meth_idx,
                )
                edit_summary = st.text_input(
                    "Summary",
                    value=str(endpoint.get("summary") or ""),
                )
                edit_op_id = st.text_input(
                    "Operation ID",
                    value=str(endpoint.get("operation_id") or ""),
                )
                save = st.form_submit_button("Save changes")
            if save:
                new_model = model
                if edit_path != str(endpoint.get("path") or ""):
                    new_model = update_endpoint_field(new_model, i, "path", edit_path)
                _old_method = str(endpoint.get("method") or "").strip().upper()
                if edit_method != _old_method:
                    new_model = update_endpoint_field(
                        new_model, i, "method", edit_method
                    )
                if edit_summary != str(endpoint.get("summary") or ""):
                    new_model = update_endpoint_field(
                        new_model, i, "summary", edit_summary
                    )
                if edit_op_id != str(endpoint.get("operation_id") or ""):
                    new_model = update_endpoint_field(
                        new_model, i, "operation_id", edit_op_id
                    )
                if new_model is not model:
                    st.session_state.state["parsed_api_model"] = new_model
                    st.rerun()

    with st.expander("+ Add endpoint", expanded=False):
        with st.form("form_add_endpoint"):
            add_path = st.text_input("Path (required)")
            add_method = st.selectbox("Method (required)", _HTTP_METHODS)
            add_summary = st.text_input("Summary (optional)", value="")
            add_op_id = st.text_input("Operation ID (optional)", value="")
            add_submitted = st.form_submit_button("Add endpoint")
        if add_submitted:
            if not str(add_path or "").strip():
                st.error("Path is required.")
            else:
                try:
                    new_ep = {
                        "path": str(add_path).strip(),
                        "method": str(add_method).strip(),
                        "operation_id": str(add_op_id or "").strip(),
                        "summary": str(add_summary or "").strip(),
                        "parameters": [],
                        "request_body": None,
                        "response_schemas": {},
                        "auth_required": False,
                        "tags": [],
                    }
                    new_model = add_endpoint(model, new_ep)
                    st.session_state.state["parsed_api_model"] = new_model
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    # Clarifications captured — use code block to prevent markdown injection
    if state.get("gap_answers"):
        st.markdown("### Clarifications captured")
        answers_text = "\n".join(
            f"{gap_id}: {format_gap_answer(answer)}"
            for gap_id, answer in state["gap_answers"].items()
        )
        st.code(answers_text, language=None)

elif current_stage == "generate_tests":
    st.success("Spec confirmed.")
    st.info(
        "**Next required action:** Story 3.1 will implement actual test "
        "generation. This placeholder stage confirms that Checkpoint 1 "
        "advanced successfully."
    )
