"""Unit tests for the tokenizer (offline hashing fallback)."""

from __future__ import annotations

import os
import subprocess
import sys
import types

import pytest

from arc.services.tokenizer import domain


def test_hashing_tokenizer_is_deterministic():
    tok = domain.get_tokenizer(None)
    a = tok.encode_ids("hello world hello")
    b = tok.encode_ids("hello world hello")
    assert a == b
    assert all(i >= 1 for i in a)  # 0 reserved for pad


def test_hashing_ids_stable_across_processes():
    # Workers are separate processes; str hash() is salted per process.
    code = (
        "from arc.services.tokenizer.domain import get_tokenizer;"
        "print(get_tokenizer(None).encode_ids('hello world'))"
    )
    outs = {
        subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()[-1]  # last line: ids (earlier lines are log output)
        for seed in ("1", "2")
    }
    assert len(outs) == 1


def test_named_tokenizer_failure_raises(monkeypatch):
    def _boom(name):
        raise OSError("not found")

    fake = types.ModuleType("tokenizers")
    fake.Tokenizer = types.SimpleNamespace(from_pretrained=_boom)
    monkeypatch.setitem(sys.modules, "tokenizers", fake)
    domain.get_tokenizer.cache_clear()
    with pytest.raises(RuntimeError, match="no-such/tokenizer"):
        domain.get_tokenizer("no-such/tokenizer")
    domain.get_tokenizer.cache_clear()


def test_info_reports_identity():
    tok = domain.get_tokenizer(None)
    i = domain.info(tok)
    assert i.name == "arc-hashing"
    assert i.vocab_size == 50_000
