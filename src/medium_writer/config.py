"""Configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    anthropic_api_key: str
    medium_token: str | None
    medium_author_id: str | None
    medium_publish_status: str
    claude_model: str
    articles_dir: Path

    def __init__(self) -> None:
        self.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
        self.medium_token = os.getenv("MEDIUM_INTEGRATION_TOKEN")
        self.medium_author_id = os.getenv("MEDIUM_AUTHOR_ID")
        self.medium_publish_status = os.getenv("MEDIUM_PUBLISH_STATUS", "draft")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.articles_dir = Path(os.getenv("ARTICLES_DIR", "articles"))
        self.articles_dir.mkdir(exist_ok=True)


config = Config()
