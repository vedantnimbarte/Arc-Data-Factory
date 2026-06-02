"""Stats, quality, languages, shards — backing the dashboard read pages."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from arc.api.deps import PrincipalDep, SessionDep
from arc.api.schemas import DatasetStats, LanguageOut
from arc.db.repositories import (
    DatasetRepository,
    DocumentRepository,
    LanguageRepository,
    TokenStatRepository,
)

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/{dataset_id}", response_model=DatasetStats, summary="Dataset statistics")
async def dataset_stats(dataset_id: uuid.UUID, session: SessionDep, _: PrincipalDep):
    if await DatasetRepository(session).get(dataset_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    docs = DocumentRepository(session)
    counts = await docs.count_by_status(dataset_id)
    token_stats = await TokenStatRepository(session).for_dataset(dataset_id)
    return DatasetStats(
        dataset_id=dataset_id,
        status_counts=counts,
        token_count=sum(t.token_count for t in token_stats),
        document_count=sum(counts.values()),
    )


@router.get("/quality/{dataset_id}", summary="Quality + language breakdown")
async def quality(dataset_id: uuid.UUID, session: SessionDep, _: PrincipalDep) -> dict:
    if await DatasetRepository(session).get(dataset_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    docs = DocumentRepository(session)
    return {
        "dataset_id": str(dataset_id),
        "languages": await docs.language_breakdown(dataset_id),
    }


@router.get("/languages", response_model=list[LanguageOut], summary="Supported languages")
async def languages(session: SessionDep, _: PrincipalDep):
    return list(await LanguageRepository(session).list())
