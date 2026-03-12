"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    anthropic_api_key: str
    claude_model: str
    articles_dir: Path

    def __init__(self) -> None:
        self.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.articles_dir = Path(os.getenv("ARTICLES_DIR", "articles"))
        self.articles_dir.mkdir(exist_ok=True)


config = Config()
