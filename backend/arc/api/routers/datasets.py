"""Datasets: create (with optional lineage parent) and list versioned datasets."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from arc.api.deps import PrincipalDep, SessionDep
from arc.api.schemas import DatasetCreate, DatasetOut, ShardOut
from arc.db.models import Dataset
from arc.db.repositories import DatasetRepository, ShardRepository

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED,
             summary="Create a versioned dataset")
async def create_dataset(body: DatasetCreate, session: SessionDep, principal: PrincipalDep) -> Dataset:
    repo = DatasetRepository(session)
    dataset = await repo.add(
        Dataset(
            name=body.name,
            version=body.version,
            parent_id=body.parent_id,
            description=body.description,
            created_by=principal,
        )
    )
    await session.commit()
    return dataset


@router.get("", response_model=list[DatasetOut], summary="List datasets")
async def list_datasets(session: SessionDep, _: PrincipalDep) -> list[Dataset]:
    return list(await DatasetRepository(session).list())


@router.get("/{dataset_id}/shards", response_model=list[ShardOut],
            summary="List a dataset's Parquet shards")
async def list_shards(dataset_id: uuid.UUID, session: SessionDep, _: PrincipalDep):
    if await DatasetRepository(session).get(dataset_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    return list(await ShardRepository(session).list(dataset_id))
