"""Pure cleaning logic — no I/O, unit-tested in isolation.

Strips HTML, normalizes whitespace/unicode, and detects language. Kept free
of DB/storage so it is trivially testable and reusable.
"""

from __future__ import annotations

import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\f\v]+")
_BLANKLINES_RE = re.compile(r"\n{3,}")


def strip_markup(text: str, mime_type: str | None) -> str:
    if mime_type and ("html" in mime_type or "xml" in mime_type):
        text = _TAG_RE.sub(" ", text)
    return text


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = _BLANKLINES_RE.sub("\n\n", text)
    return text.strip()


def clean(raw: bytes, mime_type: str | None) -> str:
    text = raw.decode("utf-8", errors="replace")
    return normalize(strip_markup(text, mime_type))


def detect_language(text: str) -> str | None:
    sample = text[:2000].strip()
    if len(sample) < 20:
        return None
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # deterministic
        return detect(sample)
    except Exception:  # noqa: BLE001
        return None


def is_empty_after_clean(text: str) -> bool:
    return len(text.strip()) == 0
