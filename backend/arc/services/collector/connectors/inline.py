"""Inline connector — documents supplied directly in source.config["documents"].

Used for web-dataset imports and for deterministic tests (no network).
"""

from __future__ import annotations

from arc.db.models import Source
from arc.services.collector.connectors.base import Connector, FetchPage, RawDocument


class InlineConnector(Connector):
    async def fetch(self, source: Source, cursor: dict, limit: int) -> FetchPage:
        items: list[dict] = list(source.config.get("documents", []))
        offset = int(cursor.get("offset", 0))
        window = items[offset : offset + limit]
        docs = [
            RawDocument(
                external_id=item.get("id", f"{offset + i}"),
                content=item["text"].encode("utf-8") if "text" in item
                else bytes.fromhex(item["hex"]),
                mime_type=item.get("mime_type", "text/plain"),
                metadata=item.get("metadata", {}),
            )
            for i, item in enumerate(window)
        ]
        next_cursor = {"offset": offset + len(window)} if offset + len(window) < len(items) else None
        return FetchPage(documents=docs, next_cursor=next_cursor)
