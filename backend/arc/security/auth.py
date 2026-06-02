"""API authentication. v1 uses static API keys (OIDC/RBAC drops in later).

A FastAPI dependency that rejects unauthenticated requests. Keys live in
settings (sourced from secrets management in prod), never in code.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from arc.core.config import settings


def _valid(presented: str) -> bool:
    # Constant-time compare against each configured key.
    return any(hmac.compare_digest(presented, k) for k in settings.api_keys)


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if settings.environment == "dev" and not settings.api_keys:
        return "dev"  # no keys configured in dev => open, but never in prod
    if not x_api_key or not _valid(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key
