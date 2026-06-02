"""Tokenizer loading + encoding. The tokenizer identity is recorded per
dataset (TokenStat) so token counts are reproducible.

Prefers a configured HuggingFace tokenizer; falls back to a deterministic
hashing tokenizer so the stage runs offline and in tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class TokenizerInfo:
    name: str
    version: str
    vocab_size: int


class _HashingTokenizer:
    """Deterministic fallback: word-level hashing into a fixed vocab."""

    name = "arc-hashing"
    version = "1"
    vocab_size = 50_000
    _word = re.compile(r"\w+|[^\w\s]")

    def encode_ids(self, text: str) -> list[int]:
        return [
            (hash(tok) % (self.vocab_size - 1)) + 1  # reserve 0 for pad
            for tok in self._word.findall(text)
        ]


@lru_cache(maxsize=1)
def get_tokenizer(name: str | None = None):
    """Return a tokenizer exposing encode_ids(text) -> list[int] + identity."""
    if name:
        try:
            from tokenizers import Tokenizer

            tok = Tokenizer.from_pretrained(name)

            class _HF:
                def __init__(self, t, n):
                    self._t = t
                    self.name = n
                    self.version = "hf"
                    self.vocab_size = t.get_vocab_size()

                def encode_ids(self, text: str) -> list[int]:
                    return self._t.encode(text).ids

            return _HF(tok, name)
        except Exception:  # noqa: BLE001  fall back offline
            pass
    return _HashingTokenizer()


def info(tokenizer) -> TokenizerInfo:
    return TokenizerInfo(
        name=tokenizer.name, version=tokenizer.version, vocab_size=tokenizer.vocab_size
    )
