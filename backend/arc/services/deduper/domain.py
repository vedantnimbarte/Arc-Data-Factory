"""Pure near-dup math: shingling + MinHash signatures.

Exact duplicates are already removed at collect time by the content-hash
upsert. This handles *near* duplicates (forks, mirrors, lightly edited
copies) per the dedup spec. No I/O here.
"""

from __future__ import annotations

import re

from datasketch import MinHash

from arc.core.config import settings

_TOKEN_RE = re.compile(r"\w+")


def shingles(text: str, k: int = 5) -> set[str]:
    """Word k-shingles — the set whose Jaccard similarity we estimate."""
    tokens = _TOKEN_RE.findall(text.lower())
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def minhash(text: str, num_perm: int | None = None) -> MinHash:
    mh = MinHash(num_perm=num_perm or settings.minhash_num_perm)
    for sh in shingles(text):
        mh.update(sh.encode("utf-8"))
    return mh
