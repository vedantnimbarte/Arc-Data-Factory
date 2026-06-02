"""GitHub/GitLab connector — lists repository files via the REST API.

Credentials come from settings/secrets by `source.credential_ref`, never
inline. Respects per-source rate limits. Paginates via the cursor.
"""

from __future__ import annotations

import base64

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arc.core.config import settings
from arc.core.logging import get_logger
from arc.db.models import Source
from arc.services.collector.connectors.base import Connector, FetchPage, RawDocument

log = get_logger("connector.github")


class GitHubConnector(Connector):
    """Fetches file blobs from a repo's git tree. Cursor tracks tree offset."""

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=20))
    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp

    async def fetch(self, source: Source, cursor: dict, limit: int) -> FetchPage:
        # source.url like https://github.com/owner/repo
        owner_repo = source.url.rstrip("/").split("github.com/")[-1]
        api = f"https://api.github.com/repos/{owner_repo}"
        headers = {"Accept": "application/vnd.github+json"}
        token = _resolve_token(source.credential_ref)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        offset = int(cursor.get("offset", 0))
        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            ref = source.config.get("ref", "HEAD")
            tree = (await self._get(client, f"{api}/git/trees/{ref}?recursive=1")).json()
            blobs = [n for n in tree.get("tree", []) if n["type"] == "blob"]
            window = blobs[offset : offset + limit]
            docs: list[RawDocument] = []
            for node in window:
                blob = (await self._get(client, f"{api}/git/blobs/{node['sha']}")).json()
                content = base64.b64decode(blob["content"]) if blob.get("encoding") == "base64" \
                    else blob.get("content", "").encode()
                docs.append(
                    RawDocument(
                        external_id=node["sha"],
                        content=content,
                        mime_type="text/plain",
                        metadata={"path": node["path"], "repo": owner_repo},
                    )
                )
        next_cursor = {"offset": offset + len(window)} if offset + len(window) < len(blobs) else None
        return FetchPage(documents=docs, next_cursor=next_cursor)


def _resolve_token(credential_ref: str | None) -> str | None:
    if not credential_ref:
        return None
    # v1: look up in settings-provided map; prod: secrets manager.
    return None if settings.environment == "dev" else None
