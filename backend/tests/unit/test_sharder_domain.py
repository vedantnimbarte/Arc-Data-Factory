"""Unit tests for Parquet shard serialization."""

from __future__ import annotations

import io

import pytest

pytest.importorskip("pyarrow")

import pyarrow.parquet as pq  # noqa: E402

from arc.services.sharder import domain  # noqa: E402


def test_build_parquet_roundtrip():
    rows = [
        {
            "doc_id": "d1", "label": "code", "language": "en",
            "quality": 0.9, "token_count": 3, "tokens": [1, 2, 3], "text": "a b c",
        }
    ]
    blob = domain.build_parquet(rows)
    table = pq.read_table(io.BytesIO(blob))
    assert table.num_rows == 1
    assert table.column("tokens")[0].as_py() == [1, 2, 3]
    assert table.column("text")[0].as_py() == "a b c"  # text kept so data can be re-tokenized
    assert table.schema.field("quality").type == "float"
