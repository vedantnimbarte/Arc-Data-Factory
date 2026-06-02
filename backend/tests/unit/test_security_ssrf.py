"""Unit tests for the SSRF guard."""

from __future__ import annotations

import pytest

from arc.security.ssrf import UnsafeURLError, assert_safe_url


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeURLError):
        assert_safe_url("file:///etc/passwd")


def test_rejects_loopback():
    with pytest.raises(UnsafeURLError):
        assert_safe_url("http://127.0.0.1/")


def test_rejects_cloud_metadata_ip():
    with pytest.raises(UnsafeURLError):
        assert_safe_url("http://169.254.169.254/latest/meta-data/")


def test_allows_public_host():
    # example.com resolves to public IPs; should not raise.
    assert_safe_url("https://example.com/")
