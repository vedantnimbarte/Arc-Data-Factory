"""Unit tests for cleaner domain logic (pure, no I/O)."""

from __future__ import annotations

from arc.services.cleaner import domain


def test_strip_markup_removes_html_tags():
    out = domain.strip_markup("<p>hello <b>world</b></p>", "text/html")
    assert "<p>" not in out and "hello" in out and "world" in out


def test_strip_markup_keeps_plain_text():
    assert domain.strip_markup("a < b and c > d", "text/plain") == "a < b and c > d"


def test_normalize_collapses_whitespace_and_blanklines():
    assert domain.normalize("a   b\n\n\n\nc") == "a b\n\nc"


def test_clean_decodes_and_normalizes():
    assert domain.clean(b"<h1>Hi</h1>\r\n\r\n\r\nthere", "text/html").startswith("Hi")


def test_is_empty_after_clean():
    assert domain.is_empty_after_clean("   \n  ")
    assert not domain.is_empty_after_clean("x")


def test_detect_language_short_text_returns_none():
    assert domain.detect_language("hi") is None
