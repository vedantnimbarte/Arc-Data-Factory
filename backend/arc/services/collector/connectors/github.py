"""GitHub connector — lists repository files via the REST API.

Credentials come from settings by `source.credential_ref`, never inline.
Paginates via the cursor, which pins the git tree sha (so a branch moving
mid-collection can't shift offsets) and carries the repo license.
"""

from __future__ import annotations

import base64
from pathlib import PurePosixPath

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arc.core.config import settings
from arc.core.logging import get_logger
from arc.db.models import Source
from arc.services.collector.connectors.base import Connector, FetchPage, RawDocument

log = get_logger("connector.github")

DEFAULT_MAX_FILE_BYTES = 1_000_000
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".pdf", ".zip", ".gz",
    ".tgz", ".bz2", ".xz", ".7z", ".tar", ".jar", ".war", ".exe", ".dll", ".so", ".dylib",
    ".o", ".a", ".pyc", ".class", ".bin", ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".wav", ".mov", ".avi", ".psd", ".sqlite", ".db",
}


def _wanted(node: dict, max_bytes: int) -> bool:
    """Skip directories, oversized files and known-binary extensions before fetching."""
    return (
        node["type"] == "blob"
        and node.get("size", 0) <= max_bytes
        and PurePosixPath(node["path"]).suffix.lower() not in _BINARY_EXT
    )


def _is_binary(content: bytes) -> bool:
    return b"\0" in content[:8192]  # git's own heuristic


def _license_of(repo: dict) -> str:
    """Lowercased SPDX id; "none" for unlicensed repos so compliance rejects them."""
    spdx = (repo.get("license") or {}).get("spdx_id")
    return "none" if spdx in (None, "NOASSERTION") else spdx.lower()


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
        max_bytes = int(source.config.get("max_file_bytes", DEFAULT_MAX_FILE_BYTES))
        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            license_id = cursor.get("license") or _license_of((await self._get(client, api)).json())
            tree_ref = cursor.get("tree") or source.config.get("ref", "HEAD")
            tree = (await self._get(client, f"{api}/git/trees/{tree_ref}?recursive=1")).json()
            if tree.get("truncated"):
                log.warning("github_tree_truncated", repo=owner_repo)
            blobs = [n for n in tree.get("tree", []) if _wanted(n, max_bytes)]
            window = blobs[offset : offset + limit]
            docs: list[RawDocument] = []
            # ponytail: one API call per file (5000/hr with a token); switch to the
            # repo tarball if large repos make this the bottleneck.
            for node in window:
                blob = (await self._get(client, f"{api}/git/blobs/{node['sha']}")).json()
                content = base64.b64decode(blob["content"]) if blob.get("encoding") == "base64" \
                    else blob.get("content", "").encode()
                if _is_binary(content):
                    continue
                docs.append(
                    RawDocument(
                        external_id=node["sha"],
                        content=content,
                        mime_type="text/plain",
                        metadata={"path": node["path"], "repo": owner_repo, "license": license_id},
                    )
                )
        end = offset + len(window)
        if end >= len(blobs):
            return FetchPage(documents=docs, next_cursor=None)
        return FetchPage(
            documents=docs, next_cursor={"offset": end, "tree": tree["sha"], "license": license_id}
        )


def _resolve_token(credential_ref: str | None) -> str | None:
    if not credential_ref:
        return None
    try:
        return settings.credentials[credential_ref]
    except KeyError:
        # Fail loudly: silently going unauthenticated drops to 60 requests/hour.
        raise LookupError(
            f"credential {credential_ref!r} not configured (set ARC_CREDENTIALS)"
        ) from None
