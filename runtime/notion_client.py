"""Async Notion API client for context fetching.

Used by webhook handlers to read page content, properties, and search
workspace data before routing to the cognitive pipeline.

Design:
    - httpx async client for non-blocking I/O
    - Retry with exponential backoff on 429/5xx
    - Notion API version pinned to 2022-06-28 (stable)
    - Minimal surface: read page, read block children, search
"""

from __future__ import annotations

import json
import logging
import os
import random
from typing import Any, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger("audhd_agents.notion_client")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class NotionClientError(Exception):
    """Base exception for Notion API errors."""

    def __init__(self, status_code: int, message: str, body: Any = None):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Notion API {status_code}: {message}")


class NotionClient:
    """Async Notion API client.

    Usage:
        async with NotionClient() as client:
            page = await client.get_page("page-id")
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        if httpx is None:
            raise ImportError(
                "httpx is required for NotionClient. "
                "Install with: pip install httpx"
            )

        self._token = token or os.getenv("NOTION_API_TOKEN", "").strip()
        if not self._token:
            logger.warning(
                "NOTION_API_TOKEN not set. NotionClient will fail on API calls."
            )

        self._max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> NotionClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    # -----------------------------------------------------------------------
    # Internal request with retry
    # -----------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Make an API request with retry on transient errors."""
        import asyncio

        last_exc: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json_body,
                    params=params,
                )

                if response.status_code == 200:
                    return response.json()

                # Rate limited: backoff and retry
                if response.status_code == 429:
                    # AUDIT-FIX: P2-2 -- cap Retry-After, handle non-numeric
                    raw_retry = response.headers.get(
                        "Retry-After", str(2 ** attempt)
                    )
                    try:
                        retry_after = min(int(raw_retry), 120)
                    except (ValueError, TypeError):
                        retry_after = min(2 ** attempt, 120)
                    logger.warning(
                        "Notion rate limited. Retry in %ds (attempt %d/%d)",
                        retry_after,
                        attempt + 1,
                        self._max_retries,
                    )
                    # AUDIT-FIX: P2-9 -- add jitter to prevent thundering herd
                    await asyncio.sleep(
                        retry_after + random.uniform(0, 0.5 * retry_after)
                    )
                    continue

                # Server error: retry with backoff
                if response.status_code >= 500:
                    backoff = min(2 ** attempt, 120)
                    await asyncio.sleep(
                        backoff + random.uniform(0, 0.5 * backoff)
                    )
                    continue

                # Client error: don't retry
                body = response.json() if response.headers.get(
                    "content-type", ""
                ).startswith("application/json") else response.text

                raise NotionClientError(
                    response.status_code,
                    str(body),
                    body,
                )

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        raise NotionClientError(
            0,
            f"All {self._max_retries} retries failed: {last_exc}",
        )

    # -----------------------------------------------------------------------
    # Page operations
    # -----------------------------------------------------------------------

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """Retrieve a page by ID. Returns full page object with properties."""
        return await self._request("GET", f"/pages/{page_id}")

    async def get_page_properties(
        self, page_id: str
    ) -> dict[str, Any]:
        """Get just the properties of a page."""
        page = await self.get_page(page_id)
        return page.get("properties", {})

    async def update_page(
        self,
        page_id: str,
        *,
        properties: Optional[dict] = None,
        archived: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Update page properties or archive status."""
        body: dict[str, Any] = {}
        if properties:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived

        return await self._request("PATCH", f"/pages/{page_id}", json_body=body)

    # -----------------------------------------------------------------------
    # Block operations
    # -----------------------------------------------------------------------

    async def get_block_children(
        self,
        block_id: str,
        *,
        page_size: int = 100,
        start_cursor: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get children of a block (page content)."""
        params: dict[str, Any] = {"page_size": page_size}
        if start_cursor:
            params["start_cursor"] = start_cursor

        return await self._request(
            "GET",
            f"/blocks/{block_id}/children",
            params=params,
        )

    async def get_all_block_children(
        self,
        block_id: str,
        *,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Paginate through all block children. Safety cap at max_pages."""
        all_blocks: list[dict[str, Any]] = []
        cursor: Optional[str] = None

        for _ in range(max_pages):
            result = await self.get_block_children(
                block_id, start_cursor=cursor
            )
            all_blocks.extend(result.get("results", []))

            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")

        return all_blocks

    # -----------------------------------------------------------------------
    # Database operations
    # -----------------------------------------------------------------------

    async def query_database(
        self,
        database_id: str,
        *,
        filter_obj: Optional[dict] = None,
        sorts: Optional[list[dict]] = None,
        page_size: int = 100,
        start_cursor: Optional[str] = None,
    ) -> dict[str, Any]:
        """Query a database with optional filter and sorts."""
        body: dict[str, Any] = {"page_size": page_size}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor

        return await self._request(
            "POST",
            f"/databases/{database_id}/query",
            json_body=body,
        )

    # -----------------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        filter_type: Optional[str] = None,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Search the workspace.

        Args:
            query: Search text
            filter_type: 'page' or 'database'
            page_size: Results per page
        """
        body: dict[str, Any] = {
            "query": query,
            "page_size": page_size,
        }
        if filter_type:
            body["filter"] = {"value": filter_type, "property": "object"}

        return await self._request("POST", "/search", json_body=body)

    # -----------------------------------------------------------------------
    # Comments
    # -----------------------------------------------------------------------

    async def get_comments(
        self,
        block_id: str,
        *,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Get comments on a block or page."""
        return await self._request(
            "GET",
            "/comments",
            params={"block_id": block_id, "page_size": page_size},
        )

    async def add_comment(
        self,
        page_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Add a comment to a page."""
        return await self._request(
            "POST",
            "/comments",
            json_body={
                "parent": {"page_id": page_id},
                "rich_text": [{
                    "type": "text",
                    "text": {"content": text},
                }],
            },
        )
