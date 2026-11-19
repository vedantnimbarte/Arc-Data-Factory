"""Pure cleaning logic — no I/O, unit-tested in isolation.

Extracts text from HTML (dropping scripts, styles and navigation), normalizes
unicode/newlines, and detects language. Plain text and code keep their
indentation; only markup-derived text has its layout whitespace collapsed.
"""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

_WS_RE = re.compile(r"[ \t\f\v]+")
_BLANKLINES_RE = re.compile(r"\n{3,}")

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer"}
_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "pre", "section", "article", "table", "ul", "ol",
    "blockquote", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)  # &amp; -> &
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _is_markup(mime_type: str | None) -> bool:
    return bool(mime_type) and ("html" in mime_type or "xml" in mime_type)


def strip_markup(text: str, mime_type: str | None) -> str:
    if not _is_markup(mime_type):
        return text
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def normalize(text: str, *, markup: bool = False) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if markup:
        # Layout whitespace in HTML means nothing; in code it's indentation.
        lines = (_WS_RE.sub(" ", ln).strip() for ln in text.split("\n"))
    else:
        lines = (ln.rstrip() for ln in text.split("\n"))
    return _BLANKLINES_RE.sub("\n\n", "\n".join(lines)).strip("\n")


def clean(raw: bytes, mime_type: str | None) -> str:
    text = raw.decode("utf-8", errors="replace")
    return normalize(strip_markup(text, mime_type), markup=_is_markup(mime_type))


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
