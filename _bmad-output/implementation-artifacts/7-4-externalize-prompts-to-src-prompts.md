# Story 7.4: Externalize Prompts to `src/prompts/`

Status: ready-for-dev

## Story

As a developer working on Sata,
I want all LLM prompt strings externalized into versioned markdown files under `src/prompts/`,
So that prompts can be reviewed, diffed, and tuned without modifying Python code.

## Acceptance Criteria

1. **Given** `app/utils/conversational_spec_builder.py` contains an inline prompt in `_build_prompt()` and `app.py` contains `CONVERSATION_PROMPT` and `ZERO_ENDPOINT_FALLBACK_MESSAGE`, **when** the externalization is applied, **then** the following files exist under `src/prompts/`:
   - `src/prompts/conversational_extraction.md` — the full system prompt for API model extraction from conversation (sourced from `_build_prompt()`)
   - `src/prompts/conversation_starter.md` — the user-facing prompt text and zero-endpoint fallback (sourced from `CONVERSATION_PROMPT` and `ZERO_ENDPOINT_FALLBACK_MESSAGE` in `app.py`)
   - `src/prompts/test_generation.md` — placeholder for future test generation prompt
   - `src/prompts/result_analysis.md` — placeholder for future result analysis prompt
   - `src/prompts/gap_filling.md` — placeholder for future gap filling prompt

2. **Given** prompts are externalized, **when** the developer inspects `src/core/prompts.py`, **then** `load_prompt(name: str) -> str` exists, reads from `src/prompts/{name}.md`, caches loaded prompts, and raises `FileNotFoundError` with a clear message if the file does not exist.

3. **Given** prompt files are loaded at runtime, **when** `pytest tests/ --tb=short -q` runs, **then** all tests involving `conversational_spec_builder` pass with prompts loaded from files instead of inline strings.

4. **Given** a developer wants to tune the conversational extraction prompt, **when** they edit `src/prompts/conversational_extraction.md`, **then** no Python file needs to change — the updated prompt is picked up on the next execution.

## Tasks / Subtasks

- [ ] Task 1: Create the `src/prompts/` directory with all required markdown files (AC: 1)
  - [ ] Create `src/prompts/conversational_extraction.md` — copy the exact static prefix of the prompt string assembled by `_build_prompt()` in `app/utils/conversational_spec_builder.py` (the lines before the `f"Conversation:\n{transcript}"` dynamic suffix). See Prompt Inventory below for the exact content.
  - [ ] Create `src/prompts/conversation_starter.md` — contain the `CONVERSATION_PROMPT` string followed by a `---` separator and the `ZERO_ENDPOINT_FALLBACK_MESSAGE` string. See Prompt Inventory below for format.
  - [ ] Create `src/prompts/test_generation.md` — placeholder stub only (see Placeholder Format below)
  - [ ] Create `src/prompts/result_analysis.md` — placeholder stub only
  - [ ] Create `src/prompts/gap_filling.md` — placeholder stub only

- [ ] Task 2: Implement `load_prompt()` in `src/core/prompts.py` — replace the `NotImplementedError` stub from Story 7.1 (AC: 2)
  - [ ] Remove the `raise NotImplementedError(...)` stub body
  - [ ] Implement `load_prompt(name: str) -> str` that resolves `src/prompts/{name}.md` relative to the `src/` package root using `pathlib.Path(__file__).parent.parent / "prompts" / f"{name}.md"`
  - [ ] Add a module-level `_PROMPT_CACHE: dict[str, str] = {}` dict for caching
  - [ ] On first call for a given `name`, read the file and store in `_PROMPT_CACHE[name]`; on subsequent calls, return the cached string
  - [ ] Raise `FileNotFoundError` with the message `f"Prompt file not found: src/prompts/{name}.md"` if the `.md` file does not exist

- [ ] Task 3: Update `app/utils/conversational_spec_builder.py` (or `src/tools/conversational_builder.py` if Story 7.2 is complete) to load the system prompt from `load_prompt()` instead of the inline string (AC: 3, 4)
  - [ ] In `_build_prompt(messages)`, replace the inline multi-line string literal with a call to `load_prompt("conversational_extraction")`
  - [ ] Append the dynamic `f"Conversation:\n{transcript}"` suffix to the loaded prompt string (this dynamic part stays in Python — only the static prefix moves to the file)
  - [ ] Import `load_prompt` from `src.core.prompts`
  - [ ] Do NOT move `_build_prompt()` logic itself — only the static prompt text changes source

- [ ] Task 4: Update `app.py` to load conversation UI strings from `load_prompt()` (AC: 3, 4)
  - [ ] Replace the `CONVERSATION_PROMPT` string literal with `load_prompt("conversation_starter").split("---")[0].strip()`
  - [ ] Replace the `ZERO_ENDPOINT_FALLBACK_MESSAGE` string literal with `load_prompt("conversation_starter").split("---")[1].strip()`
  - [ ] Import `load_prompt` from `src.core.prompts` at the top of `app.py`
  - [ ] Keep the constant names (`CONVERSATION_PROMPT`, `ZERO_ENDPOINT_FALLBACK_MESSAGE`) in place so no downstream call sites in `app.py` need changes

- [ ] Task 5: Add unit tests for `load_prompt()` (AC: 2, 3)
  - [ ] Create `tests/unit/test_core_prompts.py` (new file)
  - [ ] Test: `load_prompt("conversational_extraction")` returns a non-empty string and contains the substring `"Return valid JSON only"`
  - [ ] Test: `load_prompt("conversation_starter")` returns a non-empty string
  - [ ] Test: `load_prompt("nonexistent_prompt")` raises `FileNotFoundError` with a message containing `"src/prompts/nonexistent_prompt.md"`
  - [ ] Test: calling `load_prompt("conversational_extraction")` twice returns the same object (cache hit — use `assert result1 is result2`)
  - [ ] Test: `load_prompt("test_generation")`, `load_prompt("result_analysis")`, `load_prompt("gap_filling")` each return a non-empty string (placeholder files exist)
  - [ ] All tests must be offline — no LLM calls, no network I/O

- [ ] Task 6: Verify full test suite still passes (AC: 3)
  - [ ] Run `pytest tests/ --tb=short -q` — all tests green, including `test_conversational_spec_builder.py`
  - [ ] Confirm `ruff check app/ tests/ app.py` and `ruff format --check app/ tests/ app.py` pass (max line length 88)

## Dev Notes

### Epic & Scope Context

Epic 7 restructures the flat `app/` layout into a layered `src/` architecture. Story 7.4 is the prompts externalization step:

- Story 7.1 created `src/core/prompts.py` as a stub (`raise NotImplementedError`). This story fills it in.
- Story 7.2 moved `conversational_spec_builder.py` to `src/tools/conversational_builder.py`. If Story 7.2 is complete, update `src/tools/conversational_builder.py`; if not, update `app/utils/conversational_spec_builder.py`. Either way, update the file that is the live source of truth for the `_build_prompt()` function.
- Stories 7.3, 7.5, 7.6, 7.7 are independent of this story and should not be touched here.
- Scope is intentionally narrow: externalize the two existing prompt sources, implement `load_prompt()`, and add tests. Do not refactor any other logic.

### Dependencies

- **7.1 must be complete:** `src/core/prompts.py` must exist with the stub `load_prompt` function. This story replaces that stub body.
- **7.2 preferred but not blocking:** If 7.2 is complete, `_build_prompt()` lives in `src/tools/conversational_builder.py` and that is the file to update. If 7.2 is not yet merged, update `app/utils/conversational_spec_builder.py` instead. The test file `tests/test_conversational_spec_builder.py` imports from `app.utils.conversational_spec_builder` — this import path must remain resolvable (either as the real module or as a re-export shim from 7.2).

### Prompt Inventory

**Which Python variables/return values become which `.md` files:**

| Source location | Python identifier | Target `.md` file |
|---|---|---|
| `app/utils/conversational_spec_builder.py` `_build_prompt()` | Static prefix of the returned string (lines 77–88 in the current source, ending before `f"Conversation:\n{transcript}"`) | `src/prompts/conversational_extraction.md` |
| `app.py` line 71–73 | `CONVERSATION_PROMPT` string literal | First section of `src/prompts/conversation_starter.md` (before `---` separator) |
| `app.py` line 74–76 | `ZERO_ENDPOINT_FALLBACK_MESSAGE` string literal | Second section of `src/prompts/conversation_starter.md` (after `---` separator) |

**Exact content for `src/prompts/conversational_extraction.md`:**

This file contains the static portion of the prompt constructed in `_build_prompt()`. The dynamic `Conversation:\n{transcript}` suffix is appended by Python at call time and must NOT be included in the file. The file content should be:

```
You extract API structure from a conversation.
Return valid JSON only.
Use one of these shapes:
{"status":"needs_more_info","question":"<one concrete follow-up question>"}
{"status":"complete","api_model":{"endpoints":[{"path":"/users","method":"GET","operation_id":"listUsers","summary":"List users","parameters":[],"request_body":null,"response_schemas":{"200":{"type":"object"}},"auth_required":false,"tags":[]}],"auth":{"type":null,"scheme":null,"in":null,"name":null},"title":"Users API","version":"unknown"}}
Rules:
- Only extract API structure, not test cases.
- Do not ask for or emit secrets.
- If required details are missing, return needs_more_info.
- For complete responses, endpoints must be non-empty and methods must be uppercase.
- Keep auth.type one of: bearer, basic, api_key, oauth2, openIdConnect, null.
```

**Exact content for `src/prompts/conversation_starter.md`:**

```
Describe your API endpoints, HTTP methods, expected inputs, success responses, and auth style. For example: GET /users returns 200 with a list of users.
---
No endpoints were found in your spec. Let's describe them together.
```

**Placeholder format for `test_generation.md`, `result_analysis.md`, `gap_filling.md`:**

Each placeholder file should contain a brief comment indicating it is a stub, for example:

```
# Placeholder — prompt to be defined in Epic 3 / Epic 5.
# This file is loaded by src/core/prompts.py at runtime.
```

The file must be non-empty so `load_prompt()` returns a non-empty string without error.

### `load_prompt()` Implementation Details

The complete implementation for `src/core/prompts.py`:

```python
"""Prompt loader — reads LLM prompt text from src/prompts/*.md files."""

from pathlib import Path

_PROMPT_CACHE: dict[str, str] = {}

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Return the content of src/prompts/{name}.md, cached after first read.

    Args:
        name: Prompt file stem (no extension), e.g. "conversational_extraction".

    Returns:
        Full text of the markdown prompt file as a string.

    Raises:
        FileNotFoundError: If src/prompts/{name}.md does not exist.
    """
    if name in _PROMPT_CACHE:
        return _PROMPT_CACHE[name]

    prompt_path = _PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: src/prompts/{name}.md"
        )

    text = prompt_path.read_text(encoding="utf-8")
    _PROMPT_CACHE[name] = text
    return text
```

### Caching Strategy

Use a module-level `dict[str, str]` (`_PROMPT_CACHE`), not `functools.lru_cache`.

Rationale:
- `functools.lru_cache` on a function that raises `FileNotFoundError` on miss will not cache the error — this is fine — but clearing the cache in tests requires `load_prompt.cache_clear()` which leaks the caching implementation into tests.
- A module-level dict allows tests to call `_PROMPT_CACHE.clear()` in a `teardown`/`monkeypatch` fixture if isolation is needed, without coupling tests to the LRU API.
- For this codebase scale, a plain dict provides identical performance to `lru_cache` with no bounded eviction concern (there are fewer than 10 prompt files).

The cache is populated on first call and never invalidated during a running process. This is appropriate because prompt files are only intended to change between process restarts.

### Path Resolution — Finding `src/prompts/` at Runtime

`src/core/prompts.py` resolves the prompts directory as:

```python
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
```

`__file__` resolves to the absolute path of `src/core/prompts.py`. `.parent` is `src/core/`. `.parent.parent` is `src/`. `/ "prompts"` yields `src/prompts/`. This is robust regardless of the working directory when the process is launched (e.g., `streamlit run app.py` from the repo root, or `pytest` from any directory).

Do NOT use `os.getcwd()` or a hardcoded relative path — both are fragile across launch contexts.

### How `_build_prompt()` Uses the Loaded Prompt

After the change, `_build_prompt()` in `conversational_builder.py` (or `conversational_spec_builder.py`) should look like:

```python
from src.core.prompts import load_prompt

def _build_prompt(messages: list[dict]) -> str:
    transcript_lines = []
    for message in messages:
        role = str(message.get("role", "user")).strip().lower() or "user"
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        transcript_lines.append(f"{role.upper()}: {content}")

    transcript = "\n".join(transcript_lines)
    system_prefix = load_prompt("conversational_extraction")
    return f"{system_prefix}\n\nConversation:\n{transcript}"
```

The static system prompt prefix is loaded from the `.md` file. The `Conversation:\n{transcript}` dynamic suffix is still appended in Python because it depends on runtime data. This is the correct split point — only static, tunable text lives in the markdown file.

### `app.py` Update (`CONVERSATION_PROMPT` and `ZERO_ENDPOINT_FALLBACK_MESSAGE`)

`conversation_starter.md` uses a `---` separator to store both strings in one file without creating a new file format. The `app.py` constants are reassigned from the loaded file:

```python
from src.core.prompts import load_prompt

_conversation_starter_parts = load_prompt("conversation_starter").split("---")
CONVERSATION_PROMPT = _conversation_starter_parts[0].strip()
ZERO_ENDPOINT_FALLBACK_MESSAGE = _conversation_starter_parts[1].strip()
```

This approach:
- Keeps both UI strings together in one topically-coherent prompt file
- Does not require a new serialisation format or YAML front-matter
- Keeps the constant names in `app.py` unchanged so all call sites (`_start_conversation_flow`, `_finalize_parsed_state_after_ingestion`) continue to work without modification

### File Structure Requirements

Files to **create**:
- `src/prompts/conversational_extraction.md`
- `src/prompts/conversation_starter.md`
- `src/prompts/test_generation.md`
- `src/prompts/result_analysis.md`
- `src/prompts/gap_filling.md`
- `tests/unit/test_core_prompts.py`

Files to **modify**:
- `src/core/prompts.py` — replace `raise NotImplementedError` stub with full `load_prompt()` implementation
- `app/utils/conversational_spec_builder.py` (or `src/tools/conversational_builder.py` if Story 7.2 is complete) — replace inline string in `_build_prompt()` with `load_prompt("conversational_extraction")` call
- `app.py` — replace `CONVERSATION_PROMPT` and `ZERO_ENDPOINT_FALLBACK_MESSAGE` literals with `load_prompt("conversation_starter")` calls

Files to **leave untouched**:
- All existing `tests/test_*.py` files (must keep passing without modification)
- `app/pipeline.py`, `app/state.py`, `app/utils/spec_parser.py`, `app/utils/spec_gap_detector.py`, `app/utils/spec_fetcher.py`
- `requirements.txt`

### Testing Requirements

**Existing tests — must stay green with no modification:**

`tests/test_conversational_spec_builder.py` contains five tests. All five use a `FakeLLM` that is passed as the `llm=` argument to `extract_api_model_from_conversation()`. None of the tests call `_build_prompt()` directly or assert on the exact prompt string sent to the LLM (they only assert on the `result` dict returned by the function). Therefore these tests will continue to pass after the prompt is externalized, as long as:
1. `src/prompts/conversational_extraction.md` exists and is non-empty (so `load_prompt()` does not raise).
2. The `_build_prompt()` function still returns a string (which it will — it just loads from file instead of a literal).

No changes are needed to `tests/test_conversational_spec_builder.py`.

**New tests — `tests/unit/test_core_prompts.py`:**

```python
"""Tests for src.core.prompts.load_prompt()."""

import pytest
from src.core import prompts as prompts_module
from src.core.prompts import load_prompt


def setup_function():
    # Clear cache between tests for isolation
    prompts_module._PROMPT_CACHE.clear()


def test_load_prompt_conversational_extraction_returns_nonempty_string():
    result = load_prompt("conversational_extraction")
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_load_prompt_conversational_extraction_contains_key_instruction():
    result = load_prompt("conversational_extraction")
    assert "Return valid JSON only" in result


def test_load_prompt_conversation_starter_returns_nonempty_string():
    result = load_prompt("conversation_starter")
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_load_prompt_raises_file_not_found_for_missing_prompt():
    with pytest.raises(FileNotFoundError, match="src/prompts/nonexistent_prompt.md"):
        load_prompt("nonexistent_prompt")


def test_load_prompt_caches_result_on_second_call():
    prompts_module._PROMPT_CACHE.clear()
    result1 = load_prompt("conversational_extraction")
    result2 = load_prompt("conversational_extraction")
    assert result1 is result2  # same object — cache hit


def test_load_prompt_placeholder_files_are_loadable():
    for name in ("test_generation", "result_analysis", "gap_filling"):
        result = load_prompt(name)
        assert isinstance(result, str) and len(result.strip()) > 0, (
            f"Placeholder prompt '{name}' must be non-empty"
        )
```

All tests must be offline — no LLM calls, no HTTP requests.

### Architecture Compliance

- `src/core/prompts.py` imports only from `pathlib` (stdlib). It must never import from `app/`, `src/tools/`, `src/nodes/`, or `src/ui/`. This preserves the `core` as the dependency floor.
- `src/prompts/*.md` are data files, not Python modules. They have no `__init__.py`.
- The dependency direction after this story: `conversational_builder.py → src.core.prompts → src/prompts/*.md`. No reverse or lateral imports.
- `app.py` importing `load_prompt` from `src.core.prompts` is permitted — `app.py` is the entry point and sits outside the layered `src/` hierarchy.
- The `src/prompts/` directory does not need an `__init__.py` — it is not a Python package, it is a resource directory.

### Risks and Guardrails

- **Path resolution risk:** If `_PROMPTS_DIR` is computed incorrectly (e.g., using `os.getcwd()` instead of `Path(__file__)`), `load_prompt()` will raise `FileNotFoundError` at runtime when the process is launched from a different working directory. Always derive the path from `__file__`.
- **Cache isolation in tests:** Module-level `_PROMPT_CACHE` persists across test functions within a single pytest session. The `setup_function()` fixture in `test_core_prompts.py` must call `_PROMPT_CACHE.clear()` before each test to prevent cache state from leaking between tests (especially the cache-hit test).
- **Separator collision risk in `conversation_starter.md`:** The `---` separator used to split `CONVERSATION_PROMPT` from `ZERO_ENDPOINT_FALLBACK_MESSAGE` will break if either string itself contains `---` on its own line. The current string values do not contain this pattern. If future prompt text requires `---`, the split strategy in `app.py` must be revised (e.g., use a more unique separator like `<!-- split -->`). Document this constraint in `conversation_starter.md` with a comment.
- **Encoding risk:** Always read prompt files with `encoding="utf-8"` (not the platform default). The implementation above already specifies this.
- **Scope creep risk:** Do not migrate any other inline strings, f-strings, or error messages into `src/prompts/`. Only the two sources identified in the Prompt Inventory belong here. Error messages, log lines, and UI labels are not LLM prompts.
- **Ruff line length:** The `FileNotFoundError` message string in `load_prompt()` must not exceed 88 characters on a single line. The implementation above splits it correctly; verify with `ruff format --check`.

### References

- Inline prompt source: `/Users/sontv2/Workspace/Sown/sata/app/utils/conversational_spec_builder.py` — `_build_prompt()`, lines 66–89
- UI string source: `/Users/sontv2/Workspace/Sown/sata/app.py` — `CONVERSATION_PROMPT` (lines 70–73) and `ZERO_ENDPOINT_FALLBACK_MESSAGE` (lines 74–76)
- Existing test file (must not be modified): `/Users/sontv2/Workspace/Sown/sata/tests/test_conversational_spec_builder.py`
- Stub to replace: `/Users/sontv2/Workspace/Sown/sata/src/core/prompts.py` (created in Story 7.1, Task 5)
- Target architecture spec: `/Users/sontv2/Workspace/Sown/sata/docs/source-architecture.md` — `src/prompts/` section and migration table row for "Inline prompt strings → src/prompts/*.md"
- Story 7.1 artifact (scaffold context): `/Users/sontv2/Workspace/Sown/sata/_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md`
- Epic 7 story list: `/Users/sontv2/Workspace/Sown/sata/_bmad-output/planning-artifacts/epics.md` — Story 7.4, lines 964–995

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

_TBD_

### Completion Notes List

_TBD_

### File List

_TBD_

### Change Log

_TBD_

### Review Findings

- [ ] [Review][Patch] `tests/unit/test_core_prompts.py` missing — `src/core/prompts.py` has zero test coverage (required by AC2 and AC3) [`tests/unit/`]
- [ ] [Review][Patch] `conversation_starter.md` `---` split fragile — use `re.split(r'\n---\n', ...)` or assert `len == 2` [`app.py:78`]
- [x] [Review][Defer] Placeholder prompt files return HTML comment as content when consumed by LLM — deferred, known placeholder state
