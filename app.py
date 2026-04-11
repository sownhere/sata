"""Sata — AI-Powered API Test Agent.

Entry point: streamlit run app.py

Startup sequence:
1. Validate required environment variables (halt with error if missing).
2. Initialise SataState in session_state.
3. Build LangGraph pipeline.
4. Render persistent stage header (UX-DR1).
"""

from collections import Counter, defaultdict

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
from src.nodes.review_test_plan import prepare_rejection_for_test_regeneration
from src.tools.demo_catalog import get_demo_sample, list_demo_samples
from src.tools.report_builder import build_results_report, write_results_report
from src.ui.components import (
    format_gap_answer,
    has_ui_answer,
    render_gap_input,
    render_pipeline_visualization,
    render_reasoning_log_panel,
)
from src.ui.results_dashboard import (
    apply_results_filters,
    build_dashboard_filter_options,
    build_defect_category_buckets,
    build_detail_view,
    build_endpoint_heatmap_rows,
    build_priority_buckets,
    build_result_rows,
    build_run_delta,
    build_run_summary,
)
from src.ui.spec_review import (
    build_auth_checkpoint_rows,
    build_endpoint_detail_view,
    build_endpoint_summary_rows,
    build_rejection_return_message,
    get_stage_display_label,
    should_show_auth_checkpoint,
)
from src.ui.test_plan_review import (
    build_test_plan_review_sections,
    extract_destructive_test_groups,
    filter_enabled_test_cases,
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
if st.session_state.state.get("demo_context"):
    demo_name = st.session_state.state["demo_context"].get("name", "Demo")
    st.caption(f"Demo mode: {demo_name}")
if stage in {"execute_tests", "review_results"} and st.session_state.state.get(
    "run_attempt"
):
    st.caption(f"Current run attempt: {st.session_state.state['run_attempt']}")
st.divider()

_conversation_starter = _load_prompt("conversation_starter").split("---", 1)
CONVERSATION_PROMPT = _conversation_starter[0].strip()
ZERO_ENDPOINT_FALLBACK_MESSAGE = (
    _conversation_starter[1].strip()
    if len(_conversation_starter) > 1
    else "No endpoints were found in your spec. Let's describe them together."
)
DEMO_SAMPLE_OPTIONS = list_demo_samples()


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


def _reset_test_plan_toggle_state() -> None:
    """Drop category-toggle and Checkpoint 2 ack state before a new review plan."""
    for key in list(st.session_state.keys()):
        if str(key).startswith("toggle-test-plan-category-"):
            del st.session_state[key]
    for key in (
        "checkpoint2_ack_pending",
        "checkpoint2_ack_1",
        "checkpoint2_ack_2",
        "checkpoint2_reject_feedback",
    ):
        st.session_state.pop(key, None)


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


def _load_demo_sample_into_state(current_state, sample_id: str):
    sample = get_demo_sample(sample_id)
    current_state = reset_visualization_trace({**current_state})
    current_state["demo_context"] = {
        "id": sample["id"],
        "name": sample["name"],
        "base_url": sample["base_url"],
        # Source URL is a human-facing docs/landing page — shown as a caption,
        # not used to fetch the spec (bundled YAML is used instead).
        "source_url": sample["source_url"],
        "notes": sample["notes"],
    }
    current_state["target_api_url"] = sample["base_url"]
    current_state["raw_spec"] = sample["raw_spec"]
    current_state["parsed_api_model"] = None
    current_state["spec_confirmed"] = False
    current_state["generated_test_cases"] = None
    current_state["disabled_test_categories"] = None
    current_state["test_cases"] = None
    current_state["test_plan_confirmed"] = False
    current_state["test_results"] = None
    current_state["failure_analysis"] = None
    current_state["generated_report"] = None
    current_state["selected_test_id"] = None
    current_state["results_filters"] = None
    current_state["previous_run_summary"] = None
    current_state["run_history"] = []
    current_state["run_attempt"] = 0
    current_state["reasoning_log"] = []
    current_state["spec_source"] = "demo"
    current_state = _prime_ingestion_trace(current_state, "demo")
    parsed_state = run_pipeline_node(current_state, "parse_spec")
    if parsed_state.get("parsed_api_model"):
        parsed_state = _finalize_parsed_state_after_ingestion(parsed_state)
    return parsed_state


def _merge_test_results(existing_results, refreshed_results):
    merged = {
        str(result.get("test_id") or ""): result for result in (existing_results or [])
    }
    for result in refreshed_results or []:
        merged[str(result.get("test_id") or "")] = result
    return list(merged.values())


def _prepare_rerun_tracking(current_state, scoped_selection=None):
    pending_state = {**current_state}
    current_summary = build_run_summary(current_state.get("test_results"))
    if current_summary["total_tests"] > 0:
        run_history = list(current_state.get("run_history") or [])
        run_history.append(
            {
                "attempt": max(1, int(current_state.get("run_attempt") or 1)),
                "summary": current_summary,
                "selection": current_state.get("scoped_run_selection"),
            }
        )
        pending_state["run_history"] = run_history
        pending_state["previous_run_summary"] = current_summary

    pending_state["run_attempt"] = int(current_state.get("run_attempt") or 0) + 1
    pending_state["scoped_run_selection"] = scoped_selection
    pending_state["failure_analysis"] = None
    pending_state["generated_report"] = None
    # Reset execution guard so re-runs don't accumulate against max_iterations (NFR5).
    pending_state["iteration_count"] = 0
    return pending_state


def _run_results_iteration(current_state, selected_cases=None, scoped_selection=None):
    full_cases = list(current_state.get("test_cases") or [])
    pending_state = _prepare_rerun_tracking(current_state, scoped_selection)
    pending_state["pipeline_stage"] = "execute_tests"
    pending_state["error_message"] = None
    pending_state["selected_test_id"] = None

    if selected_cases is not None:
        pending_state["test_cases"] = list(selected_cases)

    with st.spinner(f"Re-running - Attempt {pending_state['run_attempt']}..."):
        executed_state = run_pipeline_node(pending_state, "execute_tests")

        if (
            selected_cases is not None
            and executed_state.get("test_results") is not None
        ):
            executed_state["test_results"] = _merge_test_results(
                current_state.get("test_results"),
                executed_state.get("test_results"),
            )
            executed_state["test_cases"] = full_cases

        if executed_state.get("test_results") is not None:
            executed_state = run_pipeline_node(executed_state, "analyze_results")

    return executed_state


def _safe_option_index(options, value, default=0):
    try:
        return options.index(value)
    except ValueError:
        return default


# ── Stage-driven content rendering ────────────────────────────────────────
state = st.session_state.state
current_stage = state["pipeline_stage"]

if state.get("error_message"):
    _err = str(state["error_message"])
    if current_stage in ("generate_tests", "review_test_plan") and (
        _err.startswith("Partial generation:")
        or _err.startswith("Regeneration produced no valid test cases")
    ):
        st.warning(_err)
    else:
        st.error(_err)

render_pipeline_visualization(state)
render_reasoning_log_panel(state)

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

    st.markdown("### Demo Mode")
    demo_names = {sample["name"]: sample["id"] for sample in DEMO_SAMPLE_OPTIONS}
    selected_demo_name = st.selectbox(
        "Guided sample API",
        options=list(demo_names.keys()),
        key="demo_sample_selector",
        help=(
            "Load a bundled public sample API and walk through the normal checkpoints."
        ),
    )
    selected_demo = get_demo_sample(demo_names[selected_demo_name])
    st.caption(selected_demo["notes"])
    if st.button("Start Demo Mode", use_container_width=False):
        _reset_conversation_ui()
        _clear_ingestion_banner()
        updated_state = _load_demo_sample_into_state(state, selected_demo["id"])
        st.session_state.state = updated_state
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
        if updated_state.get("test_cases"):
            _reset_test_plan_toggle_state()
            record_route_transition(
                updated_state,
                "generate_tests",
                target_override="review_test_plan",
            )
            updated_state = run_pipeline_node(updated_state, "review_test_plan")
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
    test_cases = list(state.get("test_cases") or [])
    st.info(
        "**Next required action:** Review the generated test plan below. "
        "Story 3.2 will add category toggles and destructive-operation warnings."
    )

    if not test_cases:
        st.warning("No generated test cases are available yet.")
    else:
        st.success(
            f"Generated {len(test_cases)} test case"
            f"{'s' if len(test_cases) != 1 else ''} from the confirmed spec."
        )

        category_counts = Counter(
            str(case.get("category") or "unknown") for case in test_cases
        )
        priority_counts = Counter(
            str(case.get("priority") or "unknown") for case in test_cases
        )

        category_rows = [
            {"category": category, "count": count}
            for category, count in sorted(category_counts.items())
        ]
        priority_order = {"P1": 0, "P2": 1, "P3": 2}
        priority_rows = [
            {"priority": priority, "count": count}
            for priority, count in sorted(
                priority_counts.items(),
                key=lambda item: (priority_order.get(item[0], 99), item[0]),
            )
        ]

        category_col, priority_col = st.columns(2)
        with category_col:
            st.markdown("### Categories")
            st.dataframe(category_rows, use_container_width=True)
        with priority_col:
            st.markdown("### Priorities")
            st.dataframe(priority_rows, use_container_width=True)

        preview_rows = [
            {
                "id": case.get("id"),
                "method": case.get("endpoint_method"),
                "path": case.get("endpoint_path"),
                "category": case.get("category"),
                "priority": case.get("priority"),
                "title": case.get("title"),
            }
            for case in test_cases
        ]
        st.markdown("### Generated Test Cases")
        st.dataframe(preview_rows, use_container_width=True)

elif current_stage == "review_test_plan":
    generated_test_cases = list(
        state.get("generated_test_cases") or state.get("test_cases") or []
    )
    disabled_categories = list(state.get("disabled_test_categories") or [])
    sections = build_test_plan_review_sections(
        generated_test_cases,
        disabled_categories=disabled_categories,
    )

    st.info(
        "**Next required action:** Review the generated test plan below, "
        "toggle categories on or off, and confirm it in the next checkpoint."
    )

    if not generated_test_cases:
        st.warning("No generated test cases are available for review.")
    else:
        desired_disabled_categories: list[str] = []

        for section in sections:
            toggle_key = f"toggle-test-plan-category-{section['category']}"
            if toggle_key not in st.session_state:
                st.session_state[toggle_key] = section["is_enabled"]

            header_col, toggle_col = st.columns([4, 1])
            with header_col:
                st.markdown(f"### {section['label']}")
                counts = section["priority_counts"]
                st.caption(
                    f"P1: {counts['P1']} | P2: {counts['P2']} | P3: {counts['P3']}"
                )
            with toggle_col:
                is_enabled = st.toggle(
                    "Enabled",
                    key=toggle_key,
                    label_visibility="visible",
                )

            if not is_enabled:
                desired_disabled_categories.append(section["category"])

            current_status = "Enabled" if is_enabled else "Excluded"
            for test_case in section["test_cases"]:
                test_priority = str(test_case.get("priority") or "-")
                test_title = str(test_case.get("title") or "Untitled test")
                st.markdown(f"**{test_priority} · {test_title}**")
                st.caption(
                    f"{current_status} · {test_case.get('endpoint_method', '-')} "
                    f"{test_case.get('endpoint_path', '-')}"
                )
                if test_case.get("description"):
                    st.write(str(test_case["description"]))
                destructive_warning = test_case.get("destructive_warning")
                if destructive_warning:
                    st.warning(destructive_warning)
                st.divider()

        desired_disabled_categories = sorted(set(desired_disabled_categories))
        current_enabled_cases = filter_enabled_test_cases(
            generated_test_cases,
            desired_disabled_categories,
        )
        excluded_count = len(generated_test_cases) - len(current_enabled_cases)
        st.success(
            f"{len(current_enabled_cases)} test case"
            f"{'s' if len(current_enabled_cases) != 1 else ''} currently enabled"
            f" for execution; {excluded_count} excluded."
        )

        if desired_disabled_categories != sorted(set(disabled_categories)):
            pending_state = {
                **state,
                "disabled_test_categories": desired_disabled_categories,
            }
            updated_state = run_pipeline_node(pending_state, "review_test_plan")
            st.session_state.state = updated_state
            st.rerun()

        st.divider()
        st.text_area(
            "Rejection feedback (optional — used when regenerating the test plan):",
            key="checkpoint2_reject_feedback",
            placeholder="What should the test plan improve?",
        )

        ack_pending = bool(st.session_state.get("checkpoint2_ack_pending"))

        if ack_pending:
            destructive_groups = extract_destructive_test_groups(
                state.get("test_cases") or []
            )
            group_lines = "\n".join(
                f"- {g['endpoint_method']} {g['endpoint_path']} — {g['count']} test(s)"
                for g in destructive_groups
            )
            st.warning(
                f"**Destructive operations will run.** Confirm you understand "
                f"the risks before proceeding:\n\n{group_lines}"
            )
            ack_1 = st.checkbox(
                "I understand these tests will DELETE or modify real data.",
                key="checkpoint2_ack_1",
            )
            ack_2 = st.checkbox(
                "I am targeting a safe, non-production test environment.",
                key="checkpoint2_ack_2",
            )
            proceed_col, cancel_col = st.columns(2)
            proceed_clicked = proceed_col.button(
                "Proceed with Execution",
                disabled=not (ack_1 and ack_2),
                use_container_width=True,
            )
            cancel_ack_clicked = cancel_col.button(
                "Cancel",
                use_container_width=True,
            )
            if proceed_clicked and ack_1 and ack_2:
                for _ack_key in (
                    "checkpoint2_ack_pending",
                    "checkpoint2_ack_1",
                    "checkpoint2_ack_2",
                ):
                    st.session_state.pop(_ack_key, None)
                pending_state = {**state, "test_plan_confirmed": True}
                record_route_transition(
                    pending_state,
                    "review_test_plan",
                    target_override="execute_tests",
                )
                # Only pre-run when a URL is already set; otherwise let the
                # execute_tests stage render the URL form first.
                if (pending_state.get("target_api_url") or "").strip():
                    updated_state = run_pipeline_node(pending_state, "execute_tests")
                    if updated_state.get("test_results") is not None:
                        updated_state = run_pipeline_node(
                            updated_state, "analyze_results"
                        )
                else:
                    pending_state["pipeline_stage"] = "execute_tests"
                    updated_state = pending_state
                st.session_state.state = updated_state
                st.rerun()
            if cancel_ack_clicked:
                for _ack_key in (
                    "checkpoint2_ack_pending",
                    "checkpoint2_ack_1",
                    "checkpoint2_ack_2",
                ):
                    st.session_state.pop(_ack_key, None)
                st.rerun()
        else:
            confirm_col, reject_col = st.columns(2)
            confirm_clicked = confirm_col.button(
                "Confirm Test Plan",
                use_container_width=True,
            )
            reject_clicked = reject_col.button(
                "Reject & Regenerate",
                use_container_width=True,
            )
            if confirm_clicked:
                destructive_groups = extract_destructive_test_groups(
                    state.get("test_cases") or []
                )
                if destructive_groups:
                    st.session_state["checkpoint2_ack_pending"] = True
                    st.rerun()
                else:
                    pending_state = {**state, "test_plan_confirmed": True}
                    record_route_transition(
                        pending_state,
                        "review_test_plan",
                        target_override="execute_tests",
                    )
                    # Only pre-run when a URL is already set; otherwise let the
                    # execute_tests stage render the URL form so the user can
                    # supply one before the first run.
                    if (pending_state.get("target_api_url") or "").strip():
                        updated_state = run_pipeline_node(
                            pending_state, "execute_tests"
                        )
                        if updated_state.get("test_results") is not None:
                            updated_state = run_pipeline_node(
                                updated_state, "analyze_results"
                            )
                    else:
                        pending_state["pipeline_stage"] = "execute_tests"
                        updated_state = pending_state
                    st.session_state.state = updated_state
                    st.rerun()
            if reject_clicked:
                pending_state = prepare_rejection_for_test_regeneration({**state})
                _reset_test_plan_toggle_state()
                record_route_transition(
                    pending_state,
                    "review_test_plan",
                    target_override="generate_tests",
                )
                updated_state = run_pipeline_node(pending_state, "generate_tests")
                if updated_state.get("test_cases"):
                    record_route_transition(
                        updated_state,
                        "generate_tests",
                        target_override="review_test_plan",
                    )
                    updated_state = run_pipeline_node(updated_state, "review_test_plan")
                st.session_state.state = updated_state
                st.rerun()

elif current_stage == "execute_tests":
    if state.get("test_results") is not None:
        import pandas as pd

        results = state["test_results"]
        pass_count = sum(1 for r in results if r.get("passed"))
        fail_count = len(results) - pass_count
        result_count = len(results)

        if fail_count == 0:
            st.success(f"All {result_count} test(s) passed.")
        else:
            st.error(
                f"{fail_count} of {result_count} test(s) failed — {pass_count} passed."
            )

        rows = [
            {
                "passed": r.get("passed"),
                "test_id": r.get("test_id", ""),
                "endpoint_method": r.get("endpoint_method", ""),
                "endpoint_path": r.get("endpoint_path", ""),
                "actual_status_code": r.get("actual_status_code"),
                "expected_status_code": r.get("expected_status_code"),
                "error_message": r.get("error_message", ""),
            }
            for r in results
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        failures_with_errors = [
            r for r in results if not r.get("passed") and r.get("validation_errors")
        ]
        if failures_with_errors:
            with st.expander(
                f"Validation errors ({len(failures_with_errors)} test(s))"
            ):
                for r in failures_with_errors:
                    label = (
                        r.get("title") or r.get("test_title") or r.get("test_id", "")
                    )
                    st.markdown(f"**{r.get('test_id')}** — {label}")
                    for err in r.get("validation_errors") or []:
                        st.markdown(f"- {err}")
    else:
        has_error = bool(state.get("error_message"))
        if has_error:
            st.error(state["error_message"])
            st.caption(
                "Fix the target URL below (or confirm it's reachable) and re-run."
            )
        else:
            test_count = len(state.get("test_cases") or [])
            st.info(
                f"Test plan confirmed — {test_count} test case"
                f"{'s' if test_count != 1 else ''} ready for execution."
            )

        # Show auth credential status (never display actual values)
        auth = (state.get("parsed_api_model") or {}).get("auth") or {}
        auth_type = (auth.get("type") or "").lower()
        import os

        if auth_type == "bearer":
            if os.environ.get("API_BEARER_TOKEN", "").strip():
                st.success("Auth: Bearer token configured (API_BEARER_TOKEN)")
            else:
                st.warning("Auth: No Bearer token found — set API_BEARER_TOKEN in .env")
        elif auth_type == "apikey":
            if os.environ.get("API_KEY", "").strip():
                st.success("Auth: API key configured (API_KEY)")
            else:
                st.warning("Auth: No API key found — set API_KEY in .env")

        url_input = st.text_input(
            "Target API Base URL",
            value=state.get("target_api_url") or "",
            key="target_api_url_input",
            placeholder="https://api.example.com",
        )
        run_label = "Retry" if has_error else "Run Tests"
        if st.button(run_label, key="execute_tests_run", type="primary"):
            if not url_input.strip():
                st.error("Please enter the target API base URL before running.")
            else:
                # Reset iteration_count so retries don't accumulate
                # against max_iterations (NFR5).
                pending_state = {
                    **state,
                    "target_api_url": url_input.strip(),
                    "error_message": None,
                    "iteration_count": 0,
                }
                with st.spinner("Running tests..."):
                    updated_state = run_pipeline_node(pending_state, "execute_tests")
                    if updated_state.get("test_results") is not None:
                        updated_state = run_pipeline_node(
                            updated_state, "analyze_results"
                        )
                st.session_state.state = updated_state
                st.rerun()

elif current_stage == "review_results":
    if state.get("test_results") is None:
        st.info(
            "No completed test run is available yet. "
            "Go back to Execute Tests to run or re-run the confirmed plan."
        )
        if st.button("Back to Execute Tests", key="review_results_back_to_execute"):
            pending_state = {**state, "pipeline_stage": "execute_tests"}
            st.session_state.state = pending_state
            st.rerun()
    else:
        failure_analysis = state.get("failure_analysis") or {}
        result_rows = build_result_rows(
            state.get("test_results"),
            state.get("test_cases"),
            failure_analysis,
        )
        summary = build_run_summary(state.get("test_results"))
        delta = build_run_delta(state.get("previous_run_summary"), summary)
        category_buckets = build_defect_category_buckets(failure_analysis)
        priority_buckets = build_priority_buckets(result_rows)
        heatmap_rows = build_endpoint_heatmap_rows(result_rows)
        filter_options = build_dashboard_filter_options(result_rows)
        saved_filters = state.get("results_filters") or {}

        st.info(
            "**Next:** triage the dashboard, open any failing test for detail, "
            "generate a report, or trigger a scoped/full re-test."
        )

        metric_cols = st.columns(4)
        metric_cols[0].metric("Total Tests", summary["total_tests"])
        metric_cols[1].metric(
            "Passed",
            summary["passed_tests"],
            delta=delta["passed_delta"] if delta else None,
        )
        metric_cols[2].metric(
            "Failed",
            summary["failed_tests"],
            delta=delta["failed_delta"] if delta else None,
            delta_color="inverse",
        )
        metric_cols[3].metric(
            "Pass Rate",
            f"{summary['pass_rate']}%",
            delta=(f"{delta['pass_rate_delta']}%" if delta else None),
        )

        if failure_analysis.get("all_passed"):
            st.success(
                "All enabled tests passed. "
                "Use the suggestions below to deepen coverage."
            )
            suggestions = failure_analysis.get("next_test_suggestions") or []
            if suggestions:
                for suggestion in suggestions:
                    st.markdown(f"- {suggestion}")
        elif failure_analysis.get("smart_diagnosis"):
            diagnosis = failure_analysis["smart_diagnosis"]
            st.error(
                f"Smart diagnosis: {diagnosis.get('category')} "
                f"({diagnosis.get('confidence')})"
            )
            st.write(diagnosis.get("message"))

        if failure_analysis.get("parse_error"):
            st.warning(
                "Analysis completed, but the explanation payload could not be "
                "parsed. Raw execution details are still available below."
            )

        st.markdown("### Dashboard Filters")
        filter_cols = st.columns(4)
        selected_outcome = filter_cols[0].selectbox(
            "Outcome",
            options=filter_options["outcome"],
            index=_safe_option_index(
                filter_options["outcome"],
                str(saved_filters.get("outcome") or "all"),
            ),
            key="results_filter_outcome",
        )
        selected_category = filter_cols[1].selectbox(
            "Category",
            options=filter_options["category"],
            index=_safe_option_index(
                filter_options["category"],
                str(saved_filters.get("category") or "all"),
            ),
            key="results_filter_category",
        )
        selected_priority = filter_cols[2].selectbox(
            "Priority",
            options=filter_options["priority"],
            index=_safe_option_index(
                filter_options["priority"],
                str(saved_filters.get("priority") or "all"),
            ),
            key="results_filter_priority",
        )
        selected_endpoint = filter_cols[3].selectbox(
            "Endpoint",
            options=filter_options["endpoint"],
            index=_safe_option_index(
                filter_options["endpoint"],
                str(saved_filters.get("endpoint") or "all"),
            ),
            key="results_filter_endpoint",
        )
        state["results_filters"] = {
            "outcome": selected_outcome,
            "category": selected_category,
            "priority": selected_priority,
            "endpoint": selected_endpoint,
        }

        filtered_rows = apply_results_filters(result_rows, state["results_filters"])

        st.markdown("### Defect Categories")
        if category_buckets:
            st.dataframe(category_buckets, use_container_width=True)
        else:
            st.caption("No grouped defect categories were detected for this run.")

        st.markdown("### Priority Breakdown")
        priority_cols = st.columns(3)
        for idx, bucket in enumerate(priority_buckets):
            priority_cols[idx].metric(bucket["priority"], bucket["count"])

        st.markdown("### Endpoint Heatmap")
        if heatmap_rows:
            for row in heatmap_rows:
                with st.expander(
                    f"{row['heatmap']} {row['endpoint_label']} "
                    f"({row['failed_tests']}/{row['total_tests']} failing)"
                ):
                    st.caption(
                        f"Priority spread: P1={row['priority_breakdown']['P1']} | "
                        f"P2={row['priority_breakdown']['P2']} | "
                        f"P3={row['priority_breakdown']['P3']}"
                    )
                    if row.get("top_category"):
                        st.write(f"Top defect category: `{row['top_category']}`")
                    for test_id in row["test_ids"]:
                        if st.button(
                            f"Open {test_id}",
                            key=f"open-heatmap-test-{test_id}",
                        ):
                            state["selected_test_id"] = test_id
                            st.session_state.state = state
                            st.rerun()
        else:
            st.caption("No endpoint heatmap rows are available yet.")

        st.markdown("### Test Results")
        if filtered_rows:
            for row in filtered_rows:
                status_label = "PASS" if row["passed"] else "FAIL"
                status_type = st.success if row["passed"] else st.error
                info_col, action_col = st.columns([5, 1])
                with info_col:
                    status_type(
                        f"{status_label} · {row['test_id']} · {row['endpoint_label']}"
                    )
                    st.caption(
                        f"{row['priority']} · {row['category']} · "
                        f"expected {row.get('expected_status_code')} / "
                        f"actual {row.get('actual_status_code')}"
                    )
                with action_col:
                    if st.button("Details", key=f"details-{row['test_id']}"):
                        state["selected_test_id"] = row["test_id"]
                        st.session_state.state = state
                        st.rerun()
        else:
            st.info("No test results match the current dashboard filters.")

        selected_row = next(
            (
                row
                for row in result_rows
                if row["test_id"] == state.get("selected_test_id")
            ),
            None,
        )
        detail = build_detail_view(selected_row)
        if detail:
            st.markdown("### Failure Drill-Down")
            st.markdown(
                f"**{detail['test_id']}** · {detail['title']} · "
                f"{detail['endpoint_label']}"
            )
            close_detail = st.button(
                "Close detail view",
                key="close-result-detail-view",
            )
            if close_detail:
                state["selected_test_id"] = None
                st.session_state.state = state
                st.rerun()

            request_col, response_col = st.columns(2)
            with request_col:
                st.markdown("#### Request")
                st.json(detail["request"], expanded=False)
            with response_col:
                st.markdown("#### Response")
                st.json(detail["response"], expanded=False)

            st.markdown("#### Analysis")
            st.json(detail["analysis"], expanded=False)

        patterns = failure_analysis.get("patterns") or []
        explanations = failure_analysis.get("explanations") or []
        if patterns:
            with st.expander("Failure Pattern Groups", expanded=False):
                for pattern in patterns:
                    st.markdown(
                        f"- **{pattern.get('pattern_type')}** "
                        f"({pattern.get('severity')}, {pattern.get('count')} affected)"
                    )
                    st.caption(pattern.get("description", ""))
        if explanations:
            with st.expander("Explanation Index", expanded=False):
                for explanation in explanations:
                    st.markdown(
                        f"- **{explanation.get('test_id')}**: "
                        f"{explanation.get('what_broke')}"
                    )

        st.markdown("### Re-Test and Report")
        scope_cols = st.columns(2)
        endpoint_scope = scope_cols[0].multiselect(
            "Endpoints for deeper analysis",
            options=[row["endpoint_label"] for row in heatmap_rows],
            default=(state.get("scoped_run_selection") or {}).get("endpoints") or [],
            key="results_scope_endpoints",
        )
        category_scope = scope_cols[1].multiselect(
            "Categories for deeper analysis",
            options=[
                option for option in filter_options["category"] if option != "all"
            ],
            default=(state.get("scoped_run_selection") or {}).get("categories") or [],
            key="results_scope_categories",
        )

        action_cols = st.columns(4)
        if action_cols[0].button("Generate Report", key="results-generate-report"):
            report_text = build_results_report(state)
            report_artifact = write_results_report(report_text)
            pending_state = {**state, "generated_report": report_artifact}
            st.session_state.state = pending_state
            st.rerun()

        if action_cols[1].button("Re-test Full Plan", key="results-retest-full-plan"):
            updated_state = _run_results_iteration(
                state,
                selected_cases=None,
                scoped_selection={"scope": "full"},
            )
            st.session_state.state = updated_state
            st.rerun()

        if action_cols[2].button(
            "Run Deeper Analysis",
            key="results-run-scoped-analysis",
        ):
            if not endpoint_scope and not category_scope:
                st.warning(
                    "Choose at least one endpoint or category before running "
                    "deeper analysis."
                )
            else:
                selected_cases = [
                    case
                    for case in (state.get("test_cases") or [])
                    if (
                        not endpoint_scope
                        or (
                            f"{case.get('endpoint_method', '').upper()} "
                            f"{case.get('endpoint_path', '')}"
                        )
                        in endpoint_scope
                    )
                    and (
                        not category_scope
                        or str(case.get("category") or "") in category_scope
                    )
                ]
                if not selected_cases:
                    st.warning(
                        "The chosen endpoint/category scope does not map "
                        "to any test cases."
                    )
                else:
                    updated_state = _run_results_iteration(
                        state,
                        selected_cases=selected_cases,
                        scoped_selection={
                            "scope": "scoped",
                            "endpoints": endpoint_scope,
                            "categories": category_scope,
                        },
                    )
                    st.session_state.state = updated_state
                    st.rerun()

        if action_cols[3].button("New Test Run", key="review_results_new_run"):
            pending_state = {
                **state,
                "test_results": None,
                "failure_analysis": None,
                "generated_report": None,
                "selected_test_id": None,
                "target_api_url": ((state.get("demo_context") or {}).get("base_url")),
                "previous_run_summary": None,
                "run_history": [],
                "run_attempt": 0,
                "scoped_run_selection": None,
                "pipeline_stage": "execute_tests",
            }
            st.session_state.state = pending_state
            st.rerun()

        if state.get("generated_report"):
            report_artifact = state["generated_report"]
            st.success(f"Report saved to {report_artifact['path']}")
            st.download_button(
                "Download Report",
                data=report_artifact["content"],
                file_name=report_artifact["path"].split("/")[-1],
                mime="text/markdown",
                key="results-report-download",
            )
            st.code(report_artifact["content"], language="markdown")
