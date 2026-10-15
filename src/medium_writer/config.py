"""Paths and settings for the harness."""

import os
from pathlib import Path


def _find_root() -> Path:
    override = os.getenv("MEDIUM_WRITER_HOME")
    if override:
        return Path(override).resolve()
    # Editable install: this file lives in <root>/src/medium_writer/
    return Path(__file__).resolve().parents[2]


ROOT = _find_root()
PROFILE_DIR = ROOT / "profile"
ARTICLES_DIR = ROOT / "articles"
RESEARCH_DIR = ROOT / "research"
CACHE_DIR = ROOT / ".cache"
MEDIUM_POSTS_DIR = PROFILE_DIR / "medium"

SOURCES_FILE = PROFILE_DIR / "sources.yaml"
INTERESTS_FILE = PROFILE_DIR / "interests.yaml"

MEDIUM_HANDLE = os.getenv("MEDIUM_HANDLE", "maximehaegeman")
USER_AGENT = "medium-writer/0.2 (+https://github.com/mhaegeman/medium-writer)"
