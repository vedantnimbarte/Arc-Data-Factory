"""Pure Parquet serialization for a shard. No DB/storage here.

Schema is explicit and versioned so downstream training readers are stable.
"""

from __future__ import annotations

import io

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_VERSION = 2  # v2: + text, so shards can be re-tokenized without re-running the pipeline

SHARD_SCHEMA = pa.schema(
    [
        pa.field("doc_id", pa.string()),
        pa.field("label", pa.string()),
        pa.field("language", pa.string()),
        pa.field("quality", pa.float32()),
        pa.field("token_count", pa.int32()),
        pa.field("tokens", pa.list_(pa.int32())),
        pa.field("text", pa.large_string()),
    ]
)


def build_parquet(rows: list[dict], compression: str = "zstd") -> bytes:
    table = pa.Table.from_pylist(rows, schema=SHARD_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression=compression)
    return buf.getvalue()
