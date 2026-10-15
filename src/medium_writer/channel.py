"""Sync the author's Medium posts so the voice profile can be learned from real articles."""

import re
from datetime import date

from defusedxml import ElementTree as ET

from .config import MEDIUM_HANDLE, MEDIUM_POSTS_DIR
from .fetch import html_to_text
from .http import get_text
from .sources import _child_text, _local, _parse_date


def feed_url(handle: str = MEDIUM_HANDLE) -> str:
    return f"https://medium.com/feed/@{handle.lstrip('@')}"


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70]


def parse_posts(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    posts = []
    for item in root.iter("item"):
        html = ""
        tags = []
        for child in item:
            name = _local(child.tag)
            if name == "encoded":
                html = child.text or ""
            elif name == "category" and child.text:
                tags.append(child.text.strip())
        published = _parse_date(_child_text(item, "pubDate"))
        _, body = html_to_text(html)
        posts.append(
            {
                "title": _child_text(item, "title"),
                "url": _child_text(item, "link").split("?")[0],
                "date": published.date().isoformat() if published else date.today().isoformat(),
                "tags": tags,
                "body": body,
            }
        )
    return posts


def sync(handle: str = MEDIUM_HANDLE, from_file: str | None = None) -> list[dict]:
    """Download (or read) the Medium RSS feed and store each post as Markdown."""
    if from_file:
        with open(from_file, encoding="utf-8") as fh:
            xml_text = fh.read()
    else:
        xml_text = get_text(feed_url(handle), ttl=0)
    posts = parse_posts(xml_text)
    MEDIUM_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in posts:
        path = MEDIUM_POSTS_DIR / f"{p['date']}-{_slug(p['title'])}.md"
        front = (
            f"---\ntitle: {p['title']!r}\nurl: {p['url']}\ndate: {p['date']}\n"
            f"tags: [{', '.join(p['tags'])}]\n---\n\n"
        )
        path.write_text(front + p["body"] + "\n", encoding="utf-8")
    index = ["# Medium posts (auto-synced)", ""]
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        tags = ", ".join(p["tags"])
        index.append(f"- {p['date']} [{p['title']}]({p['url']}) — {tags}")
    (MEDIUM_POSTS_DIR / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return posts
