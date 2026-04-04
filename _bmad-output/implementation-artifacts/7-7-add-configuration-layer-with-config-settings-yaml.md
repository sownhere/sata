# Story 7.7: Add Configuration Layer with `config/settings.yaml`

Status: ready-for-dev

## Story

As a developer working on Sata,
I want non-secret configuration (retry counts, timeouts, max iterations, model parameters) managed in `config/settings.yaml` alongside `.env` for secrets,
So that I can tune pipeline behavior without modifying Python code.

## Acceptance Criteria

1. **Given** all config is currently env vars only, **when** the config layer is added, **then** `config/settings.yaml` exists with documented defaults for:
   - `pipeline.max_iterations: 10`
   - `pipeline.node_timeout_seconds: 30`
   - `execution.request_timeout_seconds: 30`
   - `execution.retry_count: 1`
   - `execution.max_spec_size_bytes: 10485760`
   - `llm.temperature: 0.0`
   - `llm.max_tokens: 4096`

2. **Given** `config/settings.yaml` exists, **when** the developer inspects `src/core/config.py`, **then** it loads settings from YAML using PyYAML, merges with env vars (env vars override YAML for secrets), and exposes a typed `Settings` object implemented as a Pydantic `BaseModel` (not `BaseSettings`) containing nested section models.

3. **Given** a developer changes `pipeline.max_iterations` in `config/settings.yaml`, **when** the app restarts, **then** the new value is used by all pipeline nodes without any Python code changes.

4. **Given** the config layer is complete, **when** `pytest tests/ --tb=short -q` runs, **then** all tests pass. When no `config/settings.yaml` is present on disk (e.g., in CI or an isolated test environment), `get_settings()` falls back to the hardcoded defaults without raising an error.

## Tasks / Subtasks

- [ ] Task 1: Create `config/settings.yaml` with documented defaults (AC: 1, 3)
  - [ ] Create the `config/` directory at the project root
  - [ ] Write `config/settings.yaml` with all seven required keys in three sections (`pipeline`, `execution`, `llm`), each with an inline comment explaining the setting
  - [ ] Add `config/settings.yaml` to version control (do NOT gitignore it — it contains no secrets)
  - [ ] Add `config/` directory entry to `.gitignore` exclusion list only for any future auto-generated override files (e.g., `config/settings.local.yaml`) — do NOT ignore `config/settings.yaml` itself

- [ ] Task 2: Define Pydantic `Settings` models in `src/core/config.py` (AC: 2, 3)
  - [ ] Add three nested `BaseModel` classes to `src/core/config.py`:
    ```python
    class PipelineSettings(BaseModel):
        max_iterations: int = 10
        node_timeout_seconds: int = 30

    class ExecutionSettings(BaseModel):
        request_timeout_seconds: int = 30
        retry_count: int = 1
        max_spec_size_bytes: int = 10_485_760

    class LlmSettings(BaseModel):
        temperature: float = 0.0
        max_tokens: int = 4096

    class Settings(BaseModel):
        pipeline: PipelineSettings = PipelineSettings()
        execution: ExecutionSettings = ExecutionSettings()
        llm: LlmSettings = LlmSettings()
    ```
  - [ ] All nested models use Pydantic v2 syntax (`model_config = ConfigDict(...)` if needed; plain `BaseModel` is sufficient here since no aliases are required)
  - [ ] All field defaults in the `BaseModel` classes must exactly match the values specified in `config/settings.yaml` — the YAML is the canonical human-readable source, the dataclass defaults are the code-level fallback

- [ ] Task 3: Implement `get_settings()` loader in `src/core/config.py` (AC: 2, 3, 4)
  - [ ] Implement a `get_settings(yaml_path: Path | None = None) -> Settings` function:
    - Resolves `yaml_path` to `<project_root>/config/settings.yaml` when `None`
    - If the YAML file exists, loads it with `yaml.safe_load()` and constructs `Settings` from the nested dict using `Settings.model_validate(data)`
    - If the YAML file does not exist, returns `Settings()` (all defaults) without raising
    - Does NOT cache the result at module import time — returns a fresh parse on each call, so restarts reflect file changes (see singleton note in Dev Notes)
  - [ ] Apply env var overrides after YAML load for the two overlapping keys:
    - `LLM_TEMPERATURE` env var (if set and non-empty) overrides `settings.llm.temperature` (cast to `float`)
    - `LLM_MAX_TOKENS` env var (if set and non-empty) overrides `settings.llm.max_tokens` (cast to `int`)
    - Secrets (`LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`) remain exclusively in `.env` and are not represented in `Settings`
  - [ ] Keep existing `REQUIRED_ENV_VARS`, `load_env()`, and `validate_env()` functions exactly as migrated from Story 7.1 — do NOT remove or rename them

- [ ] Task 4: Add `get_settings` to `src/core/__init__.py` public re-exports (AC: 2)
  - [ ] Add `from src.core.config import get_settings` to `src/core/__init__.py` so callers can use either `from src.core.config import get_settings` or `from src.core import get_settings`

- [ ] Task 5: Write unit tests in `tests/unit/test_core_config.py` (AC: 4)
  - [ ] If `tests/unit/test_core_config.py` was already created by Story 7.1, extend it; if not, create it
  - [ ] Test: `get_settings()` returns a `Settings` instance with correct defaults when called with a non-existent path:
    ```python
    def test_get_settings_returns_defaults_when_no_yaml(tmp_path):
        missing = tmp_path / "settings.yaml"
        s = get_settings(yaml_path=missing)
        assert s.pipeline.max_iterations == 10
        assert s.pipeline.node_timeout_seconds == 30
        assert s.execution.request_timeout_seconds == 30
        assert s.execution.retry_count == 1
        assert s.execution.max_spec_size_bytes == 10_485_760
        assert s.llm.temperature == 0.0
        assert s.llm.max_tokens == 4096
    ```
  - [ ] Test: `get_settings()` correctly loads overridden values from a YAML file:
    ```python
    def test_get_settings_loads_yaml_overrides(tmp_path):
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text("pipeline:\n  max_iterations: 5\n")
        s = get_settings(yaml_path=yaml_file)
        assert s.pipeline.max_iterations == 5
        assert s.pipeline.node_timeout_seconds == 30  # default preserved
    ```
  - [ ] Test: env var overrides take precedence over YAML values for `llm.temperature` and `llm.max_tokens`:
    ```python
    def test_get_settings_env_var_overrides_yaml(tmp_path, monkeypatch):
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text("llm:\n  temperature: 0.7\n  max_tokens: 2048\n")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.1")
        monkeypatch.setenv("LLM_MAX_TOKENS", "512")
        s = get_settings(yaml_path=yaml_file)
        assert s.llm.temperature == 0.1
        assert s.llm.max_tokens == 512
    ```
  - [ ] Test: `get_settings()` called with no argument resolves against the real `config/settings.yaml` and returns a valid `Settings` instance (smoke test — asserts type only, not specific values, so it passes both in local and CI environments):
    ```python
    def test_get_settings_default_path_returns_settings_instance():
        s = get_settings()
        assert isinstance(s, Settings)
    ```
  - [ ] All tests are offline and deterministic — no LLM calls, no network, no Streamlit

- [ ] Task 6: Verify full test suite passes (AC: 4)
  - [ ] Run `pytest tests/ --tb=short -q` — all tests (existing + new) must be green
  - [ ] Run `ruff check src/core/config.py tests/unit/test_core_config.py` — no lint errors
  - [ ] Run `ruff format --check src/core/config.py tests/unit/test_core_config.py` — no format violations

## Dev Notes

### Epic & Scope Context

Story 7.7 is the final story in Epic 7 (Source Architecture Restructuring). It adds the non-secret configuration layer described in `docs/source-architecture.md` under "Configuration Strategy":

| What | Where |
|------|-------|
| Secrets (API keys) | `.env` (loaded by `python-dotenv`) |
| Tuning parameters | `config/settings.yaml` (loaded by PyYAML) |
| Prompt content | `src/prompts/*.md` |

This story operates in Wave 2 of Epic 7, meaning it can be developed in parallel with Stories 7.2, 7.4, and 7.5. It has one hard dependency: Story 7.1 must be complete because this story extends `src/core/config.py` which Story 7.1 creates.

### Dependency on Story 7.1

Story 7.1 creates `src/core/config.py` and migrates `REQUIRED_ENV_VARS`, `load_env()`, and `validate_env()` from `app/utils/env.py`. Story 7.7 extends that file by adding the `Settings` models and `get_settings()` function. The existing three symbols must remain intact and un-renamed — downstream code and existing tests depend on them via the `app/utils/env.py` re-export shim.

The starting state of `src/core/config.py` after Story 7.1 is:

```python
REQUIRED_ENV_VARS = ["LLM_API_KEY", "LLM_CHAT_MODEL", "LLM_BASE_URL"]

def load_env() -> None: ...
def validate_env() -> list[str]: ...
```

Story 7.7 adds new symbols below those without touching the existing ones.

### Settings Object Design — Pydantic BaseModel (not BaseSettings)

**Decision: use plain `pydantic.BaseModel` nested classes, not `pydantic_settings.BaseSettings`.**

Rationale:
- `pydantic>=2.0.0` is already in `requirements.txt`. `pydantic-settings` is a separate package (`pydantic-settings>=2.0.0`) that is NOT in `requirements.txt` and would require a dependency addition.
- `BaseSettings` auto-reads from environment variables, which would create an implicit global side-effect and complicate test isolation. Keeping env var merging as an explicit code step inside `get_settings()` is simpler and more predictable.
- The YAML-first design (load YAML, then apply selective env overrides) maps naturally to a plain `BaseModel` populated via `model_validate()`.
- `BaseModel` with typed nested models gives all the validation benefits (type coercion, error messages) without the `BaseSettings` complexity.

Do NOT add `pydantic-settings` to `requirements.txt`. Keep the implementation self-contained within the existing dependency set.

### `get_settings()` — Function vs. Singleton

`get_settings()` is a **plain function** (not a cached singleton or module-level constant). Each call re-reads and re-parses the YAML file.

- This satisfies AC 3: restarting the app re-calls `get_settings()` at startup, picking up YAML changes.
- For performance in the actual pipeline, callers that need the settings for an entire pipeline run should call `get_settings()` once at node entry and pass values as local variables — not call it in a tight loop.
- Do NOT use `@functools.lru_cache` on `get_settings()` in this story. If caching becomes a performance concern in the future, it can be added later as an explicit opt-in.
- Do NOT create a `settings = get_settings()` module-level constant in `config.py` — that would freeze the values at import time and break test isolation.

The recommended call pattern for pipeline nodes (future stories):

```python
from src.core.config import get_settings

def ingest_spec(state: SataState) -> SataState:
    settings = get_settings()
    max_size = settings.execution.max_spec_size_bytes
    ...
```

### YAML + Env Merge Strategy

The merge is explicit and intentional:

1. Load `config/settings.yaml` with `yaml.safe_load()` into a raw dict.
2. Construct `Settings` from the dict via `Settings.model_validate(raw_dict)`. Pydantic fills in defaults for any keys missing from the YAML.
3. Apply env var overrides for the two LLM tuning params that may also be set via env in some deployment environments (`LLM_TEMPERATURE`, `LLM_MAX_TOKENS`). Use `model_copy(update={...})` to produce a new immutable `Settings` instance — do not mutate in place.
4. Return the final `Settings` instance.

The three secret env vars (`LLM_API_KEY`, `LLM_CHAT_MODEL`, `LLM_BASE_URL`) are NOT represented in `Settings`. They remain under `validate_env()` / `load_env()` as before.

The architecture doc states: "Environment variables always override yaml values for overlapping keys." Apply this rule for `LLM_TEMPERATURE` and `LLM_MAX_TOKENS` only. All other YAML keys have no env var counterpart in this story.

Implementation sketch for the merge:

```python
import os
from pathlib import Path
import yaml
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # src/core/config.py → project root

def get_settings(yaml_path: Path | None = None) -> Settings:
    path = yaml_path if yaml_path is not None else _PROJECT_ROOT / "config" / "settings.yaml"
    raw: dict = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    settings = Settings.model_validate(raw)

    # Selective env var overrides
    overrides: dict = {}
    if (temp := os.environ.get("LLM_TEMPERATURE", "").strip()):
        overrides.setdefault("llm", {})["temperature"] = float(temp)
    if (tokens := os.environ.get("LLM_MAX_TOKENS", "").strip()):
        overrides.setdefault("llm", {})["max_tokens"] = int(tokens)
    if overrides:
        merged_raw = {**raw, **overrides}
        settings = Settings.model_validate(merged_raw)

    return settings
```

Note: the sketch above is a guide, not a copy-paste requirement. Adapt as needed to keep the code clean and within the 88-character line limit enforced by Ruff.

### Backward Compatibility — Existing Code Must Not Break

The following symbols in `src/core/config.py` are imported by existing code and tests via the `app/utils/env.py` re-export shim. They must not be removed, renamed, or have their signatures changed:

- `REQUIRED_ENV_VARS: list[str]`
- `load_env() -> None`
- `validate_env() -> list[str]`

All existing tests that import from `app.utils.env` must continue to pass without modification.

### PyYAML Dependency

PyYAML is **already present** in `requirements.txt` as `PyYAML>=6.0.0`. No change to `requirements.txt` is needed for this story.

Always use `yaml.safe_load()` — never `yaml.load()` without a Loader argument, as that is a security risk and will trigger a warning.

### `config/settings.yaml` Structure and Comments

The YAML file must be well-commented so it serves as self-documenting developer-facing configuration. Required structure:

```yaml
# Sata non-secret configuration
# Secrets (LLM_API_KEY, LLM_CHAT_MODEL, LLM_BASE_URL) live in .env — not here.
# Environment variables LLM_TEMPERATURE and LLM_MAX_TOKENS override llm section values.

pipeline:
  # Maximum number of LangGraph state machine iterations before forced termination.
  max_iterations: 10
  # Per-node wall-clock timeout in seconds. Nodes exceeding this are interrupted.
  node_timeout_seconds: 30

execution:
  # HTTP request timeout in seconds for test execution calls to the target API.
  request_timeout_seconds: 30
  # Number of retry attempts for failed HTTP requests during test execution.
  retry_count: 1
  # Maximum allowed spec file size in bytes (default: 10 MB).
  max_spec_size_bytes: 10485760

llm:
  # Sampling temperature for LLM calls. 0.0 = deterministic output.
  # Override with LLM_TEMPERATURE env var.
  temperature: 0.0
  # Maximum number of tokens in LLM responses.
  # Override with LLM_MAX_TOKENS env var.
  max_tokens: 4096
```

### File Structure Requirements

Files to create:
- `config/settings.yaml` — non-secret tuning configuration (project root)
- `tests/unit/test_core_config.py` — new tests for `get_settings()` (or extend if Story 7.1 created this file)

Files to modify:
- `src/core/config.py` — add `PipelineSettings`, `ExecutionSettings`, `LlmSettings`, `Settings` models and `get_settings()` function below the existing content
- `src/core/__init__.py` — add `get_settings` to public re-exports

Files to NOT touch:
- `app/utils/env.py` (already a re-export shim from Story 7.1 — do not modify)
- Any existing `tests/*.py` files in the flat `tests/` directory
- `requirements.txt` (PyYAML already present)
- `app.py`, `app/pipeline.py`, or any other `app/` file

### Testing Requirements

- `pytest tests/ --tb=short -q` must be fully green after this story
- All four new unit tests (defaults, YAML override, env override, type check) must pass
- Tests use `tmp_path` fixture for isolated YAML files — no test depends on the real `config/settings.yaml` being present or having specific values
- No Streamlit imports, no LLM calls, no live network access in any test
- `monkeypatch.setenv` / `monkeypatch.delenv` used for env var isolation — no test pollutes `os.environ`

### Architecture Compliance

- `src/core/config.py` imports only from: `os`, `pathlib`, `yaml` (PyYAML), `pydantic` — no imports from `src/nodes/`, `src/tools/`, `src/ui/`, `src/utils/`, or `app/`
- `config/settings.yaml` is committed to version control (it contains no secrets)
- The `Settings` object is a passive data container — no I/O, no side effects after `get_settings()` returns
- `get_settings()` is a pure function for test purposes: same YAML path + same env → same output

### Risks and Guardrails

- **Missing YAML risk:** `get_settings()` must not raise `FileNotFoundError` when `config/settings.yaml` does not exist. The `if path.exists()` guard is mandatory. CI environments may not have the file if `config/` is gitignored by mistake — verify `.gitignore` does not exclude `config/settings.yaml`.
- **YAML parse error risk:** If `config/settings.yaml` is malformed, `yaml.safe_load()` raises `yaml.YAMLError`. Do NOT silently swallow this exception — let it propagate so the developer sees a clear error at startup rather than a confusing downstream failure with wrong defaults.
- **Pydantic validation error risk:** If a developer puts an invalid type in `config/settings.yaml` (e.g., `max_iterations: "ten"`), Pydantic will raise `ValidationError` at `Settings.model_validate()`. This is the desired behavior — fail fast with a clear message.
- **Env var cast error risk:** If `LLM_TEMPERATURE` or `LLM_MAX_TOKENS` is set to a non-numeric value, `float(temp)` / `int(tokens)` will raise `ValueError`. Let it propagate — do not silently use the default.
- **Module-level singleton anti-pattern:** Do not add `settings = get_settings()` at module level. This freezes values at import time and causes subtle test contamination when one test writes a YAML file and the module was already imported.
- **Scope creep risk:** This story only adds the config reading layer. Do NOT wire `get_settings()` into existing pipeline nodes, `app.py`, or any existing `app/` code. That integration belongs to future stories after the full Epic 7 migration is complete.

### References

- Target architecture and config strategy: [`docs/source-architecture.md`] — "Configuration Strategy" table and `config/settings.yaml` entry in the migration table
- Story 7.1 artifact (defines starting state of `src/core/config.py`): [`_bmad-output/implementation-artifacts/7-1-scaffold-src-package-and-migrate-core-module.md`]
- Current `app/utils/env.py` (source of `REQUIRED_ENV_VARS`, `load_env`, `validate_env`): [`app/utils/env.py`]
- Existing env tests (all must keep passing): [`tests/test_env.py`]
- Pydantic v2 `BaseModel` and `model_validate` docs: [`https://docs.pydantic.dev/latest/concepts/models/`]
- PyYAML `safe_load` docs: [`https://pyyaml.org/wiki/PyYAMLDocumentation`]
- Epic 7 story list and objectives: [`_bmad-output/planning-artifacts/epics.md`]

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

- [ ] [Review][Patch] `src/core/__init__.py` missing `get_settings` re-export — `from src.core import get_settings` raises `ImportError` [`src/core/__init__.py`]
- [ ] [Review][Patch] `LLM_MAX_TOKENS` env override codepath has no test coverage [`tests/unit/test_core_settings.py`]
- [x] [Review][Defer] `execution.request_timeout_seconds` not asserted in any test — deferred, low impact
