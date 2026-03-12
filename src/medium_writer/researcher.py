"""Topic research and ideation using Claude."""

import json
import time
from pathlib import Path

import anthropic

from .config import config

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Use Haiku for cheap research/ideation tasks; reserve Sonnet for writing
_RESEARCH_MODEL = "claude-haiku-4-5-20251001"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text()


def _call_with_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    """Call client.messages.create with exponential backoff on rate limit errors."""
    max_retries = 4
    base_delay = 1.0
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt)
            time.sleep(delay)
        except anthropic.APIStatusError as e:
            # Retry on 529 (overloaded) too
            if e.status_code == 529 and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Unreachable")


def suggest_topics(category: str | None = None) -> list[dict]:
    """Ask Claude to suggest relevant article topics.

    Returns a list of dicts with keys: title, angle, why_now, category.
    Uses prompt caching on the system prompt to reduce costs on repeated calls.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system_text = _load_prompt("researcher_system.md")

    user_msg = "Suggest 5 article topics"
    if category:
        user_msg += f" focused on: {category}"
    else:
        user_msg += (
            " across these categories: AI Engineering, Data Engineering, "
            "and learning to use Claude Code"
        )
    user_msg += (
        '\n\nReturn a JSON array of objects with keys: "title", "angle", "why_now", "category". '
        "No markdown fences, just raw JSON."
    )

    message = _call_with_retry(
        client,
        model=_RESEARCH_MODEL,
        max_tokens=2048,
        # Prompt caching: mark the system prompt as cacheable
        system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)


def research_topic(topic: str) -> str:
    """Generate a research brief for a given topic.

    Uses Haiku (cheap) with prompt caching on the system prompt.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system_text = _load_prompt("researcher_system.md")

    user_msg = (
        f'Write a concise research brief for a Medium article titled: "{topic}"\n\n'
        "Include:\n"
        "- Key concepts to cover\n"
        "- Relevant recent developments (as of your knowledge cutoff)\n"
        "- Code example ideas\n"
        "- Potential gotchas or counterintuitive points\n"
        "- Target audience assumptions (beginner-intermediate data engineers/scientists)\n\n"
        "Keep it under 500 words. This is for the writer, not the reader."
    )

    message = _call_with_retry(
        client,
        model=_RESEARCH_MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_msg}],
    )

    return message.content[0].text
