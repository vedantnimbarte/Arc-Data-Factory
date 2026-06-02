"""Pure quality scoring — heuristic, deterministic, in [0, 1].

Combines signals that correlate with training value: sufficient length,
healthy alphanumeric ratio, low duplication of lines, and reasonable average
line length. An ML quality model can replace this behind the same signature.
"""

from __future__ import annotations


def quality_score(text: str) -> float:
    if not text.strip():
        return 0.0

    length = len(text)
    # Length signal: saturates around a few KB.
    length_score = min(length / 2000.0, 1.0)

    alnum = sum(c.isalnum() or c.isspace() for c in text)
    alnum_ratio = alnum / length  # penalize binary/garbage

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines:
        uniq_ratio = len(set(lines)) / len(lines)  # penalize repetitive boilerplate
        avg_len = sum(len(ln) for ln in lines) / len(lines)
        len_balance = 1.0 if 20 <= avg_len <= 200 else 0.6
    else:
        uniq_ratio, len_balance = 0.5, 0.6

    score = (
        0.30 * length_score
        + 0.30 * alnum_ratio
        + 0.25 * uniq_ratio
        + 0.15 * len_balance
    )
    return round(max(0.0, min(score, 1.0)), 4)
