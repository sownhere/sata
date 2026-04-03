"""Tests for startup environment variable validation (AC: 3, 4)."""

from src.core.config import REQUIRED_ENV_VARS, validate_env


def test_validate_env_returns_all_missing_when_none_set(monkeypatch):
    for var in REQUIRED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    missing = validate_env()
    assert set(missing) == set(REQUIRED_ENV_VARS)


def test_validate_env_returns_specific_missing_var(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CHAT_MODEL", "test-model")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    missing = validate_env()
    assert missing == ["LLM_BASE_URL"]


def test_validate_env_returns_empty_when_all_set(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CHAT_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://test.example.com/v1/")
    missing = validate_env()
    assert missing == []


def test_required_env_vars_contains_expected_keys():
    assert "LLM_API_KEY" in REQUIRED_ENV_VARS
    assert "LLM_CHAT_MODEL" in REQUIRED_ENV_VARS
    assert "LLM_BASE_URL" in REQUIRED_ENV_VARS
