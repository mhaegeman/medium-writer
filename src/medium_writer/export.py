"""Turn a finished article into a Medium-ready publishing package."""

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import ROOT, USER_AGENT
from .lint import lint, word_count
from .trends import load_interests

EXPORTS_DIR = ROOT / "exports"
EXT = {"python": "py", "py": "py", "pyspark": "py", "sql": "sql", "bash": "sh", "sh": "sh",
       "shell": "sh", "yaml": "yaml", "yml": "yaml", "json": "json", "toml": "toml",
       "javascript": "js", "typescript": "ts", "dockerfile": "Dockerfile", "markdown": "md", "csv": "csv", "text": "txt"}
FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.S | re.M)


@dataclass
class Snippet:
    index: int
    lang: str
    code: str
    filename: str


def split_title(md: str) -> tuple[str, str]:
    """Return (title, body) where body no longer contains the H1 (Medium has a title field)."""
    lines = md.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[:i] + lines[i + 1:]).strip() + "\n"
    return "", md


def extract_snippets(body: str) -> list[Snippet]:
    out = []
    for n, m in enumerate(FENCE.finditer(body), 1):
        lang = m.group(1).strip().lower()
        ext = EXT.get(lang, "txt")
        name = ext if ext == "Dockerfile" else f"snippet-{n:02d}.{ext}"
        out.append(Snippet(n, lang, m.group(2), name))
    return out


def replace_snippets(body: str, urls: dict[int, str]) -> str:
    """Swap each fenced block for its gist URL on its own line (Medium auto-embeds it)."""
    counter = iter(range(1, 10_000))
    return FENCE.sub(lambda m: urls.get(next(counter), m.group(0)), body)


def suggest_tags(md: str, limit: int = 5) -> list[str]:
    """Pick Medium tags from the pillars whose keywords appear most in the article."""
    text = md.lower()
    pillars = load_interests().get("pillars", {})
    scored = []
    for spec in pillars.values():
        hits = sum(len(re.findall(rf"(?<![a-z0-9]){re.escape(k.lower())}(?![a-z0-9])", text))
                   for k in spec.get("keywords", []))
        if hits:
            scored.append((hits * spec.get("weight", 1.0), spec.get("medium_tags", [])))
    tags: list[str] = []
    for _, pillar_tags in sorted(scored, key=lambda x: x[0], reverse=True):
        for tag in pillar_tags:
            if tag not in tags:
                tags.append(tag)
    return tags[:limit]


def create_gists(snippets: list[Snippet], title: str, token: str) -> dict[int, str]:
    """Create one unlisted (secret) gist per snippet. Secret gists are reachable by URL."""
    urls = {}
    for s in snippets:
        resp = httpx.post(
            "https://api.github.com/gists",
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT,
                     "Accept": "application/vnd.github+json"},
            json={"description": f"{title} (snippet {s.index})", "public": False,
                  "files": {s.filename: {"content": s.code or "\n"}}},
            timeout=20,
        )
        resp.raise_for_status()
        urls[s.index] = resp.json()["html_url"]
    return urls


def export_article(path: Path, *, gists: bool = False, force: bool = False) -> Path:
    md = path.read_text(encoding="utf-8")
    issues = lint(md, final=True)
    errors = [i for i in issues if i.severity == "error"]
    if errors and not force:
        raise ValueError(
            "Lint errors block export (use --force to override):\n"
            + "\n".join(f"  L{i.line} {i.rule}: {i.message}" for i in errors)
        )

    title, body = split_title(md)
    snippets = extract_snippets(body)
    dest = EXPORTS_DIR / path.stem
    (dest / "snippets").mkdir(parents=True, exist_ok=True)
    for s in snippets:
        (dest / "snippets" / s.filename).write_text(s.code, encoding="utf-8")

    gist_urls: dict[int, str] = {}
    if gists and snippets:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("--gists needs GITHUB_TOKEN with the 'gist' scope in the environment.")
        gist_urls = create_gists(snippets, title, token)
    (dest / "medium.md").write_text(replace_snippets(body, gist_urls), encoding="utf-8")

    words = word_count(md)
    links = sorted(set(re.findall(r"\]\((https?://[^)\s]+)\)", md)))
    images = len(re.findall(r"!\[[^\]]*\]\(", md)) + len(re.findall(r"<!--\s*image", md, re.I))
    tags = suggest_tags(md)
    meta = {"title": title, "words": words, "reading_minutes": math.ceil(words / 238),
            "tags": tags, "links": links, "snippets": len(snippets), "gists": gist_urls,
            "lint_errors": len(errors), "lint_warnings": len(issues) - len(errors)}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    checklist = [
        f"# Publish checklist: {title}", "",
        f"- Words: {words} (~{meta['reading_minutes']} min read)",
        f"- Lint: {len(errors)} errors, {len(issues) - len(errors)} warnings",
        f"- Suggested tags (max 5): {', '.join(tags) or '(none matched)'}",
        f"- Code snippets: {len(snippets)} ({'gist links inserted' if gist_urls else 'inline'}); "
        "files in `snippets/`",
        f"- Images in draft: {images} (Medium rewards a strong header image)", "",
        "## Steps", "",
        "1. Pick a title and write the subtitle (see `publish.md` if `/export` was run)",
        "2. Paste `medium.md` into a new Medium story and fix formatting",
        "3. Re-embed code: paste each gist URL on its own line, or Medium's code block",
        "4. Add header image and alt text; set the five tags above",
        "5. Check every link below opens, then schedule", "",
        "## Links to check", "", *[f"- {u}" for u in links],
    ]
    (dest / "checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")
    return dest
