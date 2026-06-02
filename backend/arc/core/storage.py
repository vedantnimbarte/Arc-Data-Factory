"""S3-compatible object storage abstraction.

Single client; MinIO backs dev, R2/S3 swap in by config only (no local-NVMe
special-casing). Raw documents are PACKED into bundles by the collector to
avoid the small-file metadata storm at 10B-doc scale — this layer just moves
bytes and objects by key.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aioboto3
from botocore.config import Config

from arc.core.config import settings
from arc.core.metrics import BYTES_STORED


@dataclass(frozen=True, slots=True)
class ObjectRef:
    """Stable pointer to a stored object — what crosses service boundaries."""

    bucket: str
    key: str

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"

    @classmethod
    def from_uri(cls, uri: str) -> "ObjectRef":
        bucket, _, key = uri.removeprefix("s3://").partition("/")
        return cls(bucket=bucket, key=key)


class ObjectStore:
    """Thin async wrapper over S3. Stateless apart from session config."""

    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._cfg = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # MinIO requires path-style
            retries={"max_attempts": 5, "mode": "adaptive"},
        )

    @asynccontextmanager
    async def _client(self) -> AsyncIterator:
        async with self._session.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            use_ssl=settings.s3_use_tls,
            config=self._cfg,
        ) as client:
            yield client

    async def ensure_buckets(self) -> None:
        async with self._client() as client:
            for bucket in (settings.s3_bucket_raw, settings.s3_bucket_datasets):
                try:
                    await client.head_bucket(Bucket=bucket)
                except client.exceptions.ClientError:
                    await client.create_bucket(Bucket=bucket)

    async def put_bytes(self, ref: ObjectRef, data: bytes, content_type: str) -> None:
        async with self._client() as client:
            await client.put_object(
                Bucket=ref.bucket, Key=ref.key, Body=data, ContentType=content_type
            )
        BYTES_STORED.labels(bucket=ref.bucket).inc(len(data))

    async def get_bytes(self, ref: ObjectRef) -> bytes:
        async with self._client() as client:
            resp = await client.get_object(Bucket=ref.bucket, Key=ref.key)
            return await resp["Body"].read()

    async def exists(self, ref: ObjectRef) -> bool:
        async with self._client() as client:
            try:
                await client.head_object(Bucket=ref.bucket, Key=ref.key)
                return True
            except client.exceptions.ClientError:
                return False


_store: ObjectStore | None = None


def object_store() -> ObjectStore:
    global _store
    if _store is None:
        _store = ObjectStore()
    return _store
