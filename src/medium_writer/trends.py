"""Rank scanned items against the author's interests."""

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import yaml

from .config import ARTICLES_DIR, INTERESTS_FILE
from .sources import Item

HALF_LIFE_DAYS = 7.0


@dataclass
class Ranked:
    item: Item
    score: float
    pillars: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)
    covered_by: str = ""  # existing article that already covers this


def load_interests() -> dict:
    return yaml.safe_load(INTERESTS_FILE.read_text(encoding="utf-8")) or {}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _has_keyword(text: str, kw: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(kw.lower())}(?![a-z0-9])", text) is not None


def existing_titles() -> list[tuple[str, str]]:
    """(filename, title) for every article already written."""
    out = []
    for path in sorted(ARTICLES_DIR.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                out.append((path.name, line[2:].strip()))
                break
    return out


def rank(items: list[Item], *, days: int = 14, pillar: str | None = None) -> list[Ranked]:
    interests = load_interests()
    pillars: dict = interests.get("pillars", {})
    avoid = [a.lower() for a in interests.get("avoid", [])]
    now = datetime.now(UTC)
    covered = [(f, _tokens(t)) for f, t in existing_titles()]

    ranked: list[Ranked] = []
    seen_urls: set[str] = set()
    for it in items:
        if it.url in seen_urls:
            continue
        seen_urls.add(it.url)

        age_days = (now - it.published).total_seconds() / 86400 if it.published else days / 2
        if age_days > days:
            continue
        title_l, summary_l = it.title.lower(), it.summary.lower()
        if any(_has_keyword(title_l, a) for a in avoid):
            continue

        score, hit_pillars, hits = 0.0, [], []
        for name, spec in pillars.items():
            if pillar and pillar != name:
                continue
            weight = spec.get("weight", 1.0)
            pillar_score = 0.0
            for kw in spec.get("keywords", []):
                if _has_keyword(title_l, kw):
                    pillar_score += 2.0 * weight
                    hits.append(kw)
                elif _has_keyword(summary_l, kw):
                    pillar_score += 0.7 * weight
                    hits.append(kw)
            if pillar_score:
                score += pillar_score
                hit_pillars.append(name)
        if not hit_pillars:
            continue

        recency = 0.5 ** (max(age_days, 0) / HALF_LIFE_DAYS)
        score = score * (0.4 + 0.6 * recency)
        score += math.log1p(it.points) * 0.4
        score += it.trust * 0.8

        toks = _tokens(it.title)
        covered_by = ""
        for fname, ctoks in covered:
            if toks and ctoks and len(toks & ctoks) / len(toks | ctoks) > 0.5:
                covered_by = fname
                break
        ranked.append(Ranked(it, round(score, 2), hit_pillars, sorted(set(hits)), covered_by))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
