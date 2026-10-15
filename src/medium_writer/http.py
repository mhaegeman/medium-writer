"""Tiny HTTP helper with an on-disk cache so repeated scans stay polite and fast."""

import hashlib
import time

import httpx

from .config import CACHE_DIR, USER_AGENT


def get_text(url: str, *, ttl: int = 3600, timeout: float = 15.0, refresh: bool = False) -> str:
    """GET a URL and return its body, using a cache entry younger than `ttl` seconds."""
    key = hashlib.sha1(url.encode()).hexdigest()
    cache_file = CACHE_DIR / "http" / key
    if not refresh and ttl > 0 and cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < ttl:
            return cache_file.read_text(encoding="utf-8")

    resp = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    resp.raise_for_status()
    text = resp.text
    if ttl > 0:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(text, encoding="utf-8")
    return text
