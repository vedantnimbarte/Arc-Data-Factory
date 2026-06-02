"""Unit tests for the tokenizer (offline hashing fallback)."""

from __future__ import annotations

from arc.services.tokenizer import domain


def test_hashing_tokenizer_is_deterministic():
    tok = domain.get_tokenizer(None)
    a = tok.encode_ids("hello world hello")
    b = tok.encode_ids("hello world hello")
    assert a == b
    assert all(i >= 1 for i in a)  # 0 reserved for pad


def test_info_reports_identity():
    tok = domain.get_tokenizer(None)
    i = domain.info(tok)
    assert i.name == "arc-hashing"
    assert i.vocab_size == 50_000
