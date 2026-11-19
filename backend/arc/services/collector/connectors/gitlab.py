"""GitLab connector — lists repository files via the REST API (v4).

Works for gitlab.com and self-hosted instances: the API host is taken from
`source.url` (e.g. https://gitlab.example.com/group/sub/project), so every
request passes the SSRF guard. Credentials come from settings by
`source.credential_ref` (sent as PRIVATE-TOKEN). The cursor pins the commit
sha (a moving branch can't shift pages), carries the project license, and the
tree's keyset page token.
"""

from __future__ import annotations

from urllib.parse import quote, urlsplit

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from arc.core.logging import get_logger
from arc.db.models import Source
from arc.services.collector.connectors.base import Connector, FetchPage, RawDocument
from arc.services.collector.connectors.github import (
    DEFAULT_MAX_FILE_BYTES,
    _is_binary,
    _resolve_token,
    _wanted,
)
from arc.services.collector.connectors.web import _ssrf_guard, _transient

log = get_logger("connector.gitlab")


def _license_of(project: dict) -> str:
    """Lowercased license key; "none" for unlicensed projects so compliance rejects them."""
    key = (project.get("license") or {}).get("key")
    return key.lower() if key else "none"


def _api_base(url: str) -> str:
    """https://host/group/sub/proj(.git) -> https://host/api/v4/projects/group%2Fsub%2Fproj"""
    u = urlsplit(url)
    project = u.path.strip("/").removesuffix(".git")
    return f"{u.scheme}://{u.netloc}/api/v4/projects/{quote(project, safe='')}"


class GitLabConnector(Connector):
    """Walks a project's tree page by page, fetching each blob's raw bytes."""

    @retry(
        retry=retry_if_exception(_transient),
        stop=stop_after_attempt(4),
        wait=wait_exponential(min=1, max=20),
        reraise=True,
    )
    async def _get(self, client: httpx.AsyncClient, url: str, **params) -> httpx.Response:
        resp = await client.get(url, params=params or None)
        resp.raise_for_status()
        return resp

    async def fetch(self, source: Source, cursor: dict, limit: int) -> FetchPage:
        api = _api_base(source.url)
        token = _resolve_token(source.credential_ref)
        headers = {"PRIVATE-TOKEN": token} if token else {}
        max_bytes = int(source.config.get("max_file_bytes", DEFAULT_MAX_FILE_BYTES))
        page_token = cursor.get("page_token")
        docs: list[RawDocument] = []

        async with httpx.AsyncClient(
            headers=headers, timeout=30, event_hooks={"request": [_ssrf_guard]}
        ) as client:
            if "commit" in cursor:
                commit, license_id = cursor["commit"], cursor["license"]
            else:
                project = (await self._get(client, api, license="true")).json()
                ref = source.config.get("ref") or project["default_branch"]
                commit_url = f"{api}/repository/commits/{quote(ref, safe='')}"
                commit = (await self._get(client, commit_url)).json()["id"]
                license_id = _license_of(project)

            # Whole tree pages are processed, so a batch can overshoot `limit` by < 100.
            while True:
                params = {"recursive": "true", "ref": commit, "per_page": 100,
                          "pagination": "keyset"}
                if page_token:
                    params["page_token"] = page_token
                resp = await self._get(client, f"{api}/repository/tree", **params)
                # ponytail: one request per file; switch to the repository archive
                # endpoint if large projects make this the bottleneck.
                for node in resp.json():
                    if not _wanted(node, max_bytes):
                        continue
                    blob_url = f"{api}/repository/blobs/{node['id']}/raw"
                    content = (await self._get(client, blob_url)).content
                    # Tree entries carry no size, so the size cap applies after download.
                    if len(content) > max_bytes or _is_binary(content):
                        continue
                    docs.append(
                        RawDocument(
                            external_id=node["id"],
                            content=content,
                            mime_type="text/plain",
                            metadata={"path": node["path"], "repo": source.url,
                                      "license": license_id},
                        )
                    )
                nxt = resp.links.get("next", {}).get("url")
                page_token = httpx.URL(nxt).params.get("page_token") if nxt else None
                if page_token is None or len(docs) >= limit:
                    break

        if page_token is None:
            return FetchPage(documents=docs, next_cursor=None)
        return FetchPage(
            documents=docs,
            next_cursor={"commit": commit, "license": license_id, "page_token": page_token},
        )
