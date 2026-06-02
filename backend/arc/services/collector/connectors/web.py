"""HTTP fetch connectors (web docs, SourceHut, RFCs, Wikipedia).

Every outbound URL passes the SSRF guard before fetch. URLs come from
`source.config["urls"]`; the cursor walks that list so collection is
resumable and incremental.
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arc.core.logging import get_logger
from arc.db.models import Source
from arc.security.ssrf import assert_safe_url
from arc.services.collector.connectors.base import Connector, FetchPage, RawDocument

log = get_logger("connector.web")


class WebDocsConnector(Connector):
    """Fetches a configured list of documentation/RFC URLs."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp

    async def fetch(self, source: Source, cursor: dict, limit: int) -> FetchPage:
        urls: list[str] = list(source.config.get("urls", []))
        offset = int(cursor.get("offset", 0))
        window = urls[offset : offset + limit]
        docs: list[RawDocument] = []
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "arc-collector/0.1"}) as c:
            for url in window:
                assert_safe_url(url)  # SSRF guard
                resp = await self._get(c, url)
                docs.append(
                    RawDocument(
                        external_id=url,
                        content=resp.content,
                        mime_type=resp.headers.get("content-type", "text/html").split(";")[0],
                        metadata={"url": url, "source_type": source.type.value},
                    )
                )
        next_cursor = {"offset": offset + len(window)} if offset + len(window) < len(urls) else None
        return FetchPage(documents=docs, next_cursor=next_cursor)


class WikipediaConnector(WebDocsConnector):
    """Wikipedia article fetch via the REST summary/HTML endpoints (config urls)."""
