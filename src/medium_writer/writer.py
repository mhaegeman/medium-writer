"""Article generation using Claude."""

import re
import time
from datetime import datetime
from pathlib import Path

import anthropic
import httpx

from .config import config
from .researcher import research_topic

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
_REPO_ROOT = Path(__file__).parent.parent.parent


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text()


def _load_tone_profile() -> str | None:
    tone_file = _REPO_ROOT / "tone_profile.md"
    if not tone_file.exists():
        return None
    content = tone_file.read_text(encoding="utf-8").strip()
    # Skip if still mostly the blank template
    filled_lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("<!--")]
    if len(filled_lines) < 3:
        return None
    return content


def _fetch_resource(url_or_path: str) -> str:
    """Fetch content from a URL or local file path."""
    if url_or_path.startswith(("http://", "https://")):
        try:
            resp = httpx.get(url_or_path, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s{3,}", "\n\n", text)
            return text[:6000]  # cap to avoid token blowout
        except Exception as e:
            return f"[Could not fetch {url_or_path}: {e}]"
    else:
        path = Path(url_or_path)
        if path.exists():
            return path.read_text(encoding="utf-8")[:6000]
        return f"[File not found: {url_or_path}]"


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def generate_article(
    topic: str,
    research_brief: str | None = None,
    resources: list[str] | None = None,
    stream: bool = True,
) -> tuple[str, Path]:
    """Generate a Medium article for the given topic.

    Applies prompt caching on the system prompt and any large resource blocks
    to minimise repeated token costs.

    Args:
        topic: Article title or topic.
        research_brief: Pre-generated research brief (fetched if not provided).
        resources: List of URLs or file paths to incorporate.
        stream: Stream output to stdout while generating.

    Returns:
        (article_markdown, output_path)
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    if research_brief is None:
        research_brief = research_topic(topic)

    system_text = _load_prompt("writer_system.md")
    tone_profile = _load_tone_profile()
    if tone_profile:
        system_text += f"\n\n## Author Tone Profile\n{tone_profile}"

    # Build user message as a content block list so we can cache large resource blocks
    user_content: list[dict] = []

    intro_text = f'Write a Medium article titled: "{topic}"\n\nResearch brief:\n{research_brief}'
    user_content.append({"type": "text", "text": intro_text})

    if resources:
        for url_or_path in resources:
            resource_text = f"\n\n## Resource: {url_or_path}\n{_fetch_resource(url_or_path)}"
            # Mark large resource blocks as cacheable — they're expensive to re-tokenise
            user_content.append({
                "type": "text",
                "text": resource_text,
                "cache_control": {"type": "ephemeral"},
            })

    max_retries = 4
    base_delay = 1.0

    def _stream_with_retry() -> str:
        for attempt in range(max_retries):
            try:
                parts: list[str] = []
                with client.messages.stream(
                    model=config.claude_model,
                    max_tokens=4096,
                    system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user_content}],
                ) as s:
                    for text in s.text_stream:
                        print(text, end="", flush=True)
                        parts.append(text)
                print()
                return "".join(parts)
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                if attempt == max_retries - 1:
                    raise
                is_overloaded = isinstance(e, anthropic.APIStatusError) and e.status_code == 529
                if isinstance(e, anthropic.RateLimitError) or is_overloaded:
                    time.sleep(base_delay * (2**attempt))
                else:
                    raise
        raise RuntimeError("Unreachable")

    def _create_with_retry() -> str:
        for attempt in range(max_retries):
            try:
                message = client.messages.create(
                    model=config.claude_model,
                    max_tokens=4096,
                    system=[{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user_content}],
                )
                return message.content[0].text
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                if attempt == max_retries - 1:
                    raise
                is_overloaded = isinstance(e, anthropic.APIStatusError) and e.status_code == 529
                if isinstance(e, anthropic.RateLimitError) or is_overloaded:
                    time.sleep(base_delay * (2**attempt))
                else:
                    raise
        raise RuntimeError("Unreachable")

    article_md = _stream_with_retry() if stream else _create_with_retry()

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(topic)
    filename = f"{date_str}-{slug}.md"
    output_path = config.articles_dir / filename
    output_path.write_text(article_md, encoding="utf-8")

    return article_md, output_path
