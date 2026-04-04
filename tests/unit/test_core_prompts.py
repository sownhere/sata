"""Unit tests for src.core.prompts — load_prompt() loader and cache."""

import pytest

from src.core.prompts import _PROMPT_CACHE, load_prompt


def setup_function():
    """Clear the prompt cache before each test for isolation."""
    _PROMPT_CACHE.clear()


def test_load_conversational_extraction_returns_nonempty_string():
    result = load_prompt("conversational_extraction")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Return valid JSON only" in result


def test_load_conversation_starter_returns_nonempty_string():
    result = load_prompt("conversation_starter")
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_placeholder_prompts_exist():
    for name in ("test_generation", "result_analysis", "gap_filling"):
        result = load_prompt(name)
        assert isinstance(result, str)
        assert len(result) > 0


def test_load_nonexistent_prompt_raises_file_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        load_prompt("nonexistent_prompt")
    assert "src/prompts/nonexistent_prompt.md" in str(exc_info.value)


def test_load_prompt_cache_hit_returns_same_object():
    result1 = load_prompt("conversational_extraction")
    result2 = load_prompt("conversational_extraction")
    assert result1 is result2
