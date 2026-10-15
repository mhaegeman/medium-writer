"""Turn web pages (or local files) into clean text that can be archived as research."""

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from .http import get_text

_SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside"}
_BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "h1", "h2", "h3", "h4", "pre"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in _SKIP:
            self._skip_depth += 1
        elif tag in _BLOCK:
            self.parts.append("\n")
            if tag in ("h1", "h2", "h3", "h4"):
                self.parts.append("#" * int(tag[1]) + " ")
            elif tag == "li":
                self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in _SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    """Return (title, text) from an HTML document."""
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return parser.title.strip(), text


@dataclass
class Page:
    source: str
    title: str
    text: str


def fetch_page(url_or_path: str, *, max_chars: int = 20000, refresh: bool = False) -> Page:
    if url_or_path.startswith(("http://", "https://")):
        raw = get_text(url_or_path, ttl=86400, refresh=refresh)
        if "<html" in raw[:2000].lower() or "<!doctype" in raw[:200].lower():
            title, text = html_to_text(raw)
        else:  # markdown, plain text, llms.txt, JSON
            title, text = urlparse(url_or_path).path.rsplit("/", 1)[-1], raw
    else:
        path = Path(url_or_path)
        title, text = path.name, path.read_text(encoding="utf-8")
    return Page(url_or_path, title or url_or_path, text[:max_chars])


def archive_page(page: Page, dest_dir: Path, index: int) -> Path:
    """Save a page under dest_dir with a provenance header (URL + retrieval date)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    host = urlparse(page.source).netloc or "local"
    slug = re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
    path = dest_dir / f"{index:02d}-{slug}.md"
    header = (
        f"---\nsource: {page.source}\ntitle: {page.title!r}\n"
        f"retrieved: {date.today().isoformat()}\n---\n\n"
    )
    path.write_text(header + page.text + "\n", encoding="utf-8")
    return path
