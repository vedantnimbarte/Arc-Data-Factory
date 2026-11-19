"""Tokenizer loading + encoding. The tokenizer identity is recorded per
dataset (TokenStat) so token counts are reproducible.

Uses the HuggingFace tokenizer named in the run params. With no name it
falls back to a deterministic hashing tokenizer — fine for tests and dry
runs, not for training a real model.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from functools import lru_cache

from arc.core.logging import get_logger

log = get_logger("tokenizer")


@dataclass(frozen=True, slots=True)
class TokenizerInfo:
    name: str
    version: str
    vocab_size: int


class _HashingTokenizer:
    """Deterministic fallback: word-level hashing into a fixed vocab."""

    name = "arc-hashing"
    version = "2"  # v1 used salted hash(): ids differed per process
    vocab_size = 50_000
    _word = re.compile(r"\w+|[^\w\s]")

    def encode_ids(self, text: str) -> list[int]:
        # crc32, not hash(): str hashes are salted per process, and every Ray
        # worker is its own process.
        return [
            (zlib.crc32(tok.encode("utf-8")) % (self.vocab_size - 1)) + 1  # reserve 0 for pad
            for tok in self._word.findall(text)
        ]


class _HF:
    def __init__(self, tok, name: str) -> None:
        self._t = tok
        self.name = name
        self.version = "hf"
        self.vocab_size = tok.get_vocab_size()

    def encode_ids(self, text: str) -> list[int]:
        return self._t.encode(text).ids


@lru_cache(maxsize=1)
def get_tokenizer(name: str | None = None):
    """Return a tokenizer exposing encode_ids(text) -> list[int] + identity."""
    if not name:
        log.warning("hashing_tokenizer_fallback", hint="set params.tokenizer for training data")
        return _HashingTokenizer()
    from tokenizers import Tokenizer

    try:
        return _HF(Tokenizer.from_pretrained(name), name)
    except Exception as exc:
        # Never silently swap tokenizers: a dataset would mix incompatible ids.
        raise RuntimeError(f"cannot load tokenizer {name!r}: {exc}") from exc


def info(tokenizer) -> TokenizerInfo:
    return TokenizerInfo(
        name=tokenizer.name, version=tokenizer.version, vocab_size=tokenizer.vocab_size
    )
