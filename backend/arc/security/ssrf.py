"""SSRF guard for collectors that fetch arbitrary URLs (web docs, RFCs).

Default-deny private/link-local/loopback ranges so a malicious source URL
cannot reach internal services or the cloud metadata endpoint
(169.254.169.254). Resolve then validate every resolved IP.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from arc.core.config import settings


class UnsafeURLError(ValueError):
    """Raised when a URL resolves to a disallowed address."""


_ALLOWED_SCHEMES = {"http", "https"}


def assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme not allowed: {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeURLError("missing host")

    if settings.allow_collector_private_ranges:
        return

    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed for {parsed.hostname!r}") from exc

    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeURLError(f"{parsed.hostname!r} resolves to disallowed address {ip}")
