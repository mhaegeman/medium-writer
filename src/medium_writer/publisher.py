"""Medium API integration for publishing articles."""

import httpx

from .config import config

MEDIUM_API_BASE = "https://api.medium.com/v1"


class MediumPublisher:
    def __init__(self) -> None:
        if not config.medium_token:
            raise ValueError(
                "MEDIUM_INTEGRATION_TOKEN is not set. "
                "Get one at https://medium.com/me/settings"
            )
        self._headers = {
            "Authorization": f"Bearer {config.medium_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_author_id(self) -> str:
        """Fetch the authenticated user's Medium author ID."""
        if config.medium_author_id:
            return config.medium_author_id

        resp = httpx.get(f"{MEDIUM_API_BASE}/me", headers=self._headers)
        resp.raise_for_status()
        author_id = resp.json()["data"]["id"]
        return author_id

    def publish(
        self,
        title: str,
        content_markdown: str,
        tags: list[str] | None = None,
        status: str | None = None,
    ) -> dict:
        """Publish an article to Medium.

        Args:
            title: Article title.
            content_markdown: Full article in Markdown.
            tags: Up to 5 tags.
            status: "draft", "public", or "unlisted". Defaults to config value.

        Returns:
            Medium API response dict with article URL.
        """
        author_id = self.get_author_id()
        publish_status = status or config.medium_publish_status

        payload = {
            "title": title,
            "contentFormat": "markdown",
            "content": content_markdown,
            "publishStatus": publish_status,
        }
        if tags:
            payload["tags"] = tags[:5]

        resp = httpx.post(
            f"{MEDIUM_API_BASE}/users/{author_id}/posts",
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"]
