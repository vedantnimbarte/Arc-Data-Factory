"""Collector connectors against a mocked HTTP transport (no network)."""

from __future__ import annotations

import base64
from types import SimpleNamespace

import httpx
import pytest

from arc.core.config import settings
from arc.db.enums import SourceType
from arc.services.collector.connectors import get_connector, github, gitlab, web

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


async def test_gitlab_pins_commit_records_license_paginates_and_skips_binaries(monkeypatch):
    monkeypatch.setattr(settings, "allow_collector_private_ranges", True)  # no DNS in tests
    monkeypatch.setattr(settings, "credentials", {"gl": "tok"})
    calls: list[httpx.Request] = []
    pages = {
        None: [
            {"id": "s1", "type": "blob", "path": "a.py"},
            {"id": "s2", "type": "blob", "path": "logo.png"},
            {"id": "s3", "type": "tree", "path": "src"},
        ],
        "p2": [
            {"id": "s4", "type": "blob", "path": "data.dat"},
            {"id": "s5", "type": "blob", "path": "big.txt"},
            {"id": "s6", "type": "blob", "path": "b.md"},
        ],
    }
    blobs = {"s1": b"print('hi')\n", "s4": b"\x00bin", "s5": b"x" * 100, "s6": b"# Title\n"}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        path = request.url.path
        if path.endswith("/repository/commits/main"):
            return httpx.Response(200, json={"id": "C1"})
        if path.endswith("/repository/tree"):
            assert request.url.params["ref"] == "C1"  # always the pinned commit
            token = request.url.params.get("page_token")
            headers = {}
            if token is None:
                nxt = f"{request.url.copy_merge_params({'page_token': 'p2'})}"
                headers["link"] = f'<{nxt}>; rel="next"'
            return httpx.Response(200, json=pages[token], headers=headers)
        if path.endswith("/raw"):
            return httpx.Response(200, content=blobs[path.split("/")[-2]])
        return httpx.Response(200, json={"default_branch": "main", "license": {"key": "MIT"}})

    _mock_http(monkeypatch, handler)
    source = SimpleNamespace(
        url="https://gitlab.com/group/sub/proj", credential_ref="gl", config={"max_file_bytes": 50}
    )
    conn = gitlab.GitLabConnector()

    first = await conn.fetch(source, {}, 1)
    assert [d.metadata["path"] for d in first.documents] == ["a.py"]
    assert first.documents[0].metadata["license"] == "mit"
    assert first.next_cursor == {"commit": "C1", "license": "mit", "page_token": "p2"}

    second = await conn.fetch(source, first.next_cursor, 1)
    assert [d.metadata["path"] for d in second.documents] == ["b.md"]  # binary + oversized skipped
    assert second.next_cursor is None

    raw_paths = [r.url.raw_path.decode() for r in calls]
    assert sum("license=true" in p for p in raw_paths) == 1  # project looked up once
    assert all("/projects/group%2Fsub%2Fproj" in p for p in raw_paths)  # nested group encoded
    assert not any("/s2/" in p for p in raw_paths)  # png never fetched
    assert all(r.headers["private-token"] == "tok" for r in calls)


async def test_gitlab_guards_self_hosted_hosts_against_ssrf(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request to a private address must not be sent")

    _mock_http(monkeypatch, handler)
    source = SimpleNamespace(url="http://127.0.0.1/group/proj", credential_ref=None, config={})
    with pytest.raises(Exception, match="disallowed address"):
        await gitlab.GitLabConnector().fetch(source, {}, 10)


def test_gitlab_unlicensed_project_marked_none():
    assert gitlab._license_of({"license": None}) == "none"
    assert gitlab._license_of({"license": {"key": "Apache-2.0"}}) == "apache-2.0"


def test_gitlab_source_type_has_connector():
    assert isinstance(get_connector(SourceType.GITLAB), gitlab.GitLabConnector)


@pytest.mark.parametrize(
    "path",
    [
        "package-lock.json", "web/yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock",
        "go.sum", "Gemfile.lock", "uv.lock",  # lockfiles
        "node_modules/x/index.js", "vendor/github.com/a/b.go", "app/dist/bundle.js",  # vendored
        "static/app.min.js", "css/site.min.css", "app.js.map",  # minified / source maps
        "api/v1/service.pb.go", "proto/msg_pb2.py",  # protobuf output
    ],
)
def test_repo_filter_skips_lockfiles_vendored_and_generated_paths(path):
    assert not github._wanted({"type": "blob", "path": path, "size": 10}, 1_000)


@pytest.mark.parametrize(
    "path", ["src/main.py", "package.json", "docs/vendor-guide.md", "lib/distance.go", "Makefile"]
)
def test_repo_filter_keeps_source_files(path):
    assert github._wanted({"type": "blob", "path": path, "size": 10}, 1_000)


def test_generated_content_markers():
    assert github._is_generated(b"// Code generated by protoc-gen-go. DO NOT EDIT.\npackage x")
    assert github._is_generated(b"/**\n * @generated by relay-compiler\n */")
    assert github._is_generated(b"// <auto-generated>\n// This code was generated")
    assert not github._is_generated(b"def main():\n    pass\n")
