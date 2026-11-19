"""Schema invariants the pipeline depends on."""

from __future__ import annotations

from arc.db.models import Document


def test_document_content_hash_index_is_unique():
    # Collector's ON CONFLICT (dataset_id, content_hash) needs a unique index to exist.
    idx = next(i for i in Document.__table__.indexes if i.name == "ix_doc_dataset_hash")
    assert idx.unique
