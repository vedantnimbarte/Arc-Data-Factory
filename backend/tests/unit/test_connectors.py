"""Collector connectors against a mocked HTTP transport (no network)."""

from __future__ import annotations

import base64
from types import SimpleNamespace

import httpx
import pytest

from arc.core.config import settings
from arc.db.enums import SourceType
from arc.services.collector.connectors import github, web

_REAL_CLIENT = httpx.AsyncClient


def _mock_http(monkeypatch, handler):
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )


async def test_web_blocks_redirect_to_private_and_skips_bad_urls(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/meta"})
        if request.url.path == "/missing":
            return httpx.Response(404)
        return httpx.Response(200, text="hello", headers={"content-type": "text/html"})

    _mock_http(monkeypatch, handler)
    base = "http://93.184.216.34"
    urls = [f"{base}/redirect", f"{base}/missing", f"{base}/ok"]
    source = SimpleNamespace(type=SourceType.WEB_DOCS, config={"urls": urls})
    page = await web.WebDocsConnector().fetch(source, {}, 10)
    assert [d.external_id for d in page.documents] == [f"{base}/ok"]
    assert not any("169.254" in u for u in seen)  # redirect target was never requested


async def test_github_pins_tree_records_license_and_skips_binaries(monkeypatch):
    calls: list[str] = []
    tree = {
        "sha": "T1",
        "truncated": False,
        "tree": [
            {"type": "blob", "path": "a.py", "sha": "s1", "size": 10},
            {"type": "blob", "path": "logo.png", "sha": "s2", "size": 10},
            {"type": "blob", "path": "data.dat", "sha": "s3", "size": 10},
            {"type": "blob", "path": "huge.py", "sha": "s4", "size": 50_000_000},
            {"type": "tree", "path": "src", "sha": "s5"},
        ],
    }
    blobs = {"s1": b"print('hi')\n", "s3": b"\x00\x01binary"}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path == "/repos/o/r":
            return httpx.Response(200, json={"license": {"spdx_id": "MIT"}})
        if path.startswith("/repos/o/r/git/trees/"):
            return httpx.Response(200, json=tree)
        sha = path.rsplit("/", 1)[-1]
        content = base64.b64encode(blobs[sha]).decode()
        return httpx.Response(200, json={"encoding": "base64", "content": content})

    _mock_http(monkeypatch, handler)
    source = SimpleNamespace(url="https://github.com/o/r", credential_ref=None, config={})
    conn = github.GitHubConnector()

    first = await conn.fetch(source, {}, 1)
    assert [d.metadata["path"] for d in first.documents] == ["a.py"]
    assert first.documents[0].metadata["license"] == "mit"
    assert first.next_cursor == {"offset": 1, "tree": "T1", "license": "mit"}

    second = await conn.fetch(source, first.next_cursor, 1)
    assert second.documents == []  # data.dat is binary
    assert second.next_cursor is None
    assert "/repos/o/r/git/trees/T1" in calls  # later pages read the pinned tree
    assert calls.count("/repos/o/r") == 1  # license looked up once, then carried in cursor
    assert not any(c.endswith(("/s2", "/s4")) for c in calls)  # png/huge never fetched


def test_github_unlicensed_repo_marked_none():
    assert github._license_of({"license": None}) == "none"
    assert github._license_of({"license": {"spdx_id": "NOASSERTION"}}) == "none"


def test_resolve_token(monkeypatch):
    monkeypatch.setattr(settings, "credentials", {"gh": "tok"})
    assert github._resolve_token(None) is None
    assert github._resolve_token("gh") == "tok"
    with pytest.raises(LookupError):
        github._resolve_token("missing")
