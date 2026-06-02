"""Sources: register and list ingestion sources."""

from __future__ import annotations

from fastapi import APIRouter, status

from arc.api.deps import PrincipalDep, SessionDep
from arc.api.schemas import SourceCreate, SourceOut
from arc.db.models import Source
from arc.db.repositories import SourceRepository

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED,
             summary="Register a new ingestion source")
async def create_source(body: SourceCreate, session: SessionDep, _: PrincipalDep) -> Source:
    repo = SourceRepository(session)
    source = await repo.add(
        Source(
            name=body.name,
            type=body.type,
            url=str(body.url),
            credential_ref=body.credential_ref,
            rate_limit_per_min=body.rate_limit_per_min,
            config=body.config,
        )
    )
    await session.commit()
    return source


@router.get("", response_model=list[SourceOut], summary="List ingestion sources")
async def list_sources(session: SessionDep, _: PrincipalDep) -> list[Source]:
    return list(await SourceRepository(session).list())
