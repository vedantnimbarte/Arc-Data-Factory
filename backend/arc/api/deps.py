"""FastAPI dependencies: DB session and authenticated principal."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from arc.core.db import get_session
from arc.security.auth import require_api_key


async def db_session() -> AsyncIterator[AsyncSession]:
    async for s in get_session():
        yield s


SessionDep = Annotated[AsyncSession, Depends(db_session)]
PrincipalDep = Annotated[str, Depends(require_api_key)]
