"""Fetch candidate items from the sources listed in profile/sources.yaml."""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import yaml
from defusedxml import ElementTree as ET

from .config import SOURCES_FILE
from .http import get_text


@dataclass
class Item:
    title: str
    url: str
    source: str
    kind: str = "blog"  # blog | release | community
    trust: int = 1  # 2 = official channel, 1 = reputable, 0 = community chatter
    published: datetime | None = None
    summary: str = ""
    points: int = 0


@dataclass
class SourceReport:
    name: str
    ok: bool
    count: int = 0
    error: str = ""
    seconds: float = 0.0


@dataclass
class Scan:
    items: list[Item] = field(default_factory=list)
    reports: list[SourceReport] = field(default_factory=list)


def load_sources() -> dict:
    return yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8")) or {}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(el, name: str) -> str:
    for child in el:
        if _local(child.tag) == name and (child.text or "").strip():
            return child.text.strip()
    return ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)  # RSS (RFC 822)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom (ISO 8601)
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def parse_feed(xml_text: str, *, source: str, kind: str = "blog", trust: int = 1) -> list[Item]:
    """Parse RSS 2.0 or Atom into Items."""
    root = ET.fromstring(xml_text)
    items: list[Item] = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        title = _child_text(el, "title")
        link = _child_text(el, "link")
        if not link:  # Atom puts the URL in href
            for child in el:
                if _local(child.tag) == "link" and child.get("href"):
                    if child.get("rel", "alternate") == "alternate":
                        link = child.get("href", "")
                        break
        date = (
            _child_text(el, "pubDate")
            or _child_text(el, "published")
            or _child_text(el, "updated")
            or _child_text(el, "date")
        )
        summary = _child_text(el, "description") or _child_text(el, "summary")
        if title and link:
            items.append(
                Item(
                    title=title,
                    url=link,
                    source=source,
                    kind=kind,
                    trust=trust,
                    published=_parse_date(date),
                    summary=summary[:600],
                )
            )
    return items


def _fetch_feed(spec: dict, refresh: bool) -> list[Item]:
    xml_text = get_text(spec["url"], refresh=refresh)
    items = parse_feed(
        xml_text,
        source=spec["name"],
        kind=spec.get("kind", "blog"),
        trust=spec.get("trust", 1),
    )
    if spec.get("kind") == "release":  # bare version numbers need their project name
        for it in items:
            it.title = f"{spec['name']}: {it.title}"
    return items


def _fetch_github_releases(spec: dict, refresh: bool) -> list[Item]:
    url = f"https://github.com/{spec['repo']}/releases.atom"
    items = parse_feed(get_text(url, refresh=refresh), source=spec["repo"], kind="release", trust=2)
    for it in items:
        it.title = f"{spec['repo']} {it.title}"
    return items[:5]


def _fetch_hn(cfg: dict, refresh: bool) -> list[Item]:
    base = "https://hn.algolia.com/api/v1"
    min_points = cfg.get("min_points", 50)
    since = int(time.time()) - cfg.get("days", 7) * 86400
    urls = [f"{base}/search?tags=front_page&hitsPerPage=60"]
    for q in cfg.get("queries", []):
        urls.append(
            f"{base}/search?tags=story&query={q.replace(' ', '+')}"
            f"&numericFilters=created_at_i>{since},points>{min_points}&hitsPerPage=15"
        )
    seen: dict[str, Item] = {}
    for u in urls:
        data = json.loads(get_text(u, ttl=1800, refresh=refresh))
        for hit in data.get("hits", []):
            title = hit.get("title")
            if not title or (hit.get("points") or 0) < min_points:
                continue
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            seen[link] = Item(
                title=title,
                url=link,
                source="Hacker News",
                kind="community",
                trust=0,
                published=datetime.fromtimestamp(hit.get("created_at_i", 0), UTC),
                points=hit.get("points") or 0,
            )
    return list(seen.values())


def scan(refresh: bool = False, workers: int = 8) -> Scan:
    """Fetch every configured source in parallel. Failures are reported, never fatal."""
    cfg = load_sources()
    jobs: list[tuple[str, Callable]] = []
    for spec in cfg.get("feeds", []):
        jobs.append((spec["name"], lambda s=spec: _fetch_feed(s, refresh)))
    for spec in cfg.get("github_releases", []):
        jobs.append((spec["repo"], lambda s=spec: _fetch_github_releases(s, refresh)))
    if cfg.get("hackernews"):
        jobs.append(("Hacker News", lambda: _fetch_hn(cfg["hackernews"], refresh)))

    def run(job: tuple[str, Callable]) -> tuple[SourceReport, list[Item]]:
        name, fn = job
        start = time.time()
        try:
            got = fn()
            return SourceReport(name, True, len(got), seconds=time.time() - start), got
        except Exception as e:  # network, parse, HTTP status: all non-fatal
            msg = f"{type(e).__name__}: {str(e)[:120]}"
            return SourceReport(name, False, error=msg, seconds=time.time() - start), []

    result = Scan()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for report, got in pool.map(run, jobs):
            result.reports.append(report)
            result.items.extend(got)
    return result
