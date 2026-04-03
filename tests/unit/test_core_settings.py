"""Unit tests for get_settings() — config/settings.yaml loading (Story 7.7)."""

import pytest
import yaml

from src.core.config import Settings, get_settings


def test_get_settings_returns_defaults_when_no_yaml(tmp_path):
    nonexistent = tmp_path / "no_settings.yaml"
    s = get_settings(settings_path=nonexistent)
    assert isinstance(s, Settings)
    assert s.pipeline.max_iterations == 10
    assert s.pipeline.node_timeout_seconds == 30
    assert s.execution.retry_count == 1
    assert s.execution.max_spec_size_bytes == 10 * 1024 * 1024
    assert s.llm.temperature == 0.0
    assert s.llm.max_tokens == 4096


def test_get_settings_loads_yaml_overrides(tmp_path):
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(yaml.dump({"pipeline": {"max_iterations": 5}}))
    s = get_settings(settings_path=cfg)
    assert s.pipeline.max_iterations == 5
    assert s.pipeline.node_timeout_seconds == 30  # default preserved


def test_get_settings_env_overrides_temperature(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    s = get_settings(settings_path=tmp_path / "absent.yaml")
    assert s.llm.temperature == pytest.approx(0.7)
    assert s.llm.max_tokens == 4096  # default preserved


def test_get_settings_returns_defaults_on_malformed_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(": : invalid yaml :::")
    s = get_settings(settings_path=bad)
    assert s.pipeline.max_iterations == 10  # fallback to defaults


def test_get_settings_env_overrides_max_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
    monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
    s = get_settings(settings_path=tmp_path / "absent.yaml")
    assert s.llm.max_tokens == 2048
    assert s.llm.temperature == 0.0  # default preserved
