"""Prompt loader utility — reads versioned LLM prompts from src/prompts/*.md.

Canonical location: src.core.prompts

Usage:
    from src.core.prompts import load_prompt
    system_prompt = load_prompt("conversational_extraction")

The cache is a plain module-level dict so tests can call
``_PROMPT_CACHE.clear()`` for isolation without coupling to functools.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_PROMPT_CACHE: dict[str, str] = {}


def load_prompt(name: str) -> str:
    """Return the content of src/prompts/{name}.md, cached after first load.

    Args:
        name: Prompt file stem, e.g. "conversational_extraction".

    Raises:
        FileNotFoundError: if the prompt file does not exist.
    """
    if name in _PROMPT_CACHE:
        return _PROMPT_CACHE[name]

    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: src/prompts/{name}.md")

    content = path.read_text(encoding="utf-8").strip()
    _PROMPT_CACHE[name] = content
    return content
