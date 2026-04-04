"""Environment variable validation and settings loader.

Canonical location: src.core.config
Separates .env file loading from environment inspection so that
``validate_env`` remains a pure ``os.environ`` query and is testable
without side-effects from a locally present ``.env`` file.

Typical startup sequence::

    load_env()          # populate os.environ from .env (once, at startup)
    missing = validate_env()  # pure check — safe to call in tests
    if missing:
        ...
    settings = get_settings()   # load config/settings.yaml defaults
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

REQUIRED_ENV_VARS = ["LLM_API_KEY", "LLM_CHAT_MODEL", "LLM_BASE_URL"]

# Default path for the settings file relative to the project root
_DEFAULT_SETTINGS_PATH = (
    Path(__file__).parent.parent.parent / "config" / "settings.yaml"
)


def load_env() -> None:
    """Load variables from a .env file into os.environ (no-op if already set).

    Uses ``override=False`` so that variables already present in the process
    environment (including those manipulated by ``monkeypatch`` in tests) are
    never overwritten.
    """
    load_dotenv(override=False)


def validate_env() -> list[str]:
    """Return a list of missing required environment variable names.

    This function is a *pure* os.environ inspector — it does **not** load any
    ``.env`` file.  Call ``load_env()`` beforehand at application startup if
    you need ``.env`` support.
    """
    return [var for var in REQUIRED_ENV_VARS if not os.environ.get(var, "").strip()]


# ── Settings models ──────────────────────────────────────────────────────────


class PipelineSettings(BaseModel):
    max_iterations: int = 10
    node_timeout_seconds: int = 30


class ExecutionSettings(BaseModel):
    request_timeout_seconds: int = 30
    retry_count: int = 1
    max_spec_size_bytes: int = 10 * 1024 * 1024  # 10 MB


class LlmSettings(BaseModel):
    temperature: float = 0.0
    max_tokens: int = 4096


class Settings(BaseModel):
    pipeline: PipelineSettings = PipelineSettings()
    execution: ExecutionSettings = ExecutionSettings()
    llm: LlmSettings = LlmSettings()


def get_settings(settings_path: Optional[Path] = None) -> Settings:
    """Load and return a Settings object from config/settings.yaml.

    Falls back to built-in defaults if the file is absent or unreadable.
    Environment variables override yaml values for llm.temperature and
    llm.max_tokens (``LLM_TEMPERATURE``, ``LLM_MAX_TOKENS``).

    Args:
        settings_path: Override path to settings.yaml (useful in tests).
    """
    path = settings_path or _DEFAULT_SETTINGS_PATH
    raw: dict = {}

    if path.exists():
        try:
            with open(path) as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                raw = loaded
        except (yaml.YAMLError, OSError):
            pass  # Malformed YAML or I/O error → fall through to defaults

    settings = Settings.model_validate(raw)

    # Environment variable overrides for LLM tuning params
    if os.environ.get("LLM_TEMPERATURE", "").strip():
        try:
            settings.llm.temperature = float(os.environ["LLM_TEMPERATURE"])
        except ValueError:
            pass

    if os.environ.get("LLM_MAX_TOKENS", "").strip():
        try:
            settings.llm.max_tokens = int(os.environ["LLM_MAX_TOKENS"])
        except ValueError:
            pass

    return settings
